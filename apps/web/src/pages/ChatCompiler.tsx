import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { analyzeMessage, getSources } from '../api/client';
import type { AnalyzeResponse, SourceItem } from '../api/types';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
  analysis?: AnalyzeResponse;
}

const EXAMPLES = [
  'compactness에서 finite subcover가 왜 중요한지 모르겠어.',
  'Rudin의 open cover 정의가 직관적으로 안 잡혀.',
  'connectedness와 path connectedness가 헷갈려.',
];

const REP_LABELS: Record<string, string> = {
  intuitive: '직관',
  formal: '정의',
  example: '예시/반례',
  proof_schema: '증명 구조',
  misconception: '오개념',
};

const SEED_CONCEPTS = [
  { id: 'compactness', ko: '옹골성', en: 'compactness' },
  { id: 'connectedness', ko: '연결성', en: 'connectedness' },
  { id: 'uniform_continuity', ko: '균등 연속', en: 'uniform continuity' },
];

export default function ChatCompiler() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getSources().then(setSources).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setLoading(true);
    try {
      const res = await analyzeMessage({
        message: msg,
        source_id: selectedSourceId || undefined,
      });
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.concept_id
            ? `${res.canonical_name_ko} ${res.canonical_name_en}`
            : '해당 개념을 찾을 수 없습니다.',
          analysis: res,
        },
      ]);
    } catch (e: unknown) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `오류가 발생했습니다. 다시 시도해주세요. (${String(e)})` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function toggleSection(key: string) {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  }

  const showEmptyState = messages.length === 0;

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {showEmptyState && (
          <div className="chat-empty-state">
            <h1 className="chat-greeting">어떤 개념이 막혔나요?</h1>
            <div className="chat-examples">
              {EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  className="chat-example-pill"
                  onClick={() => handleSend(ex)}
                >
                  &quot;{ex}&quot;
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble chat-bubble-${msg.role}`}>
            <div className="chat-bubble-text">{msg.content}</div>
            {msg.analysis && msg.analysis.concept_id && (
              <AnalysisCard
                analysis={msg.analysis}
                expanded={expanded}
                onToggle={toggleSection}
                msgIndex={i}
                onConceptClick={handleSend}
              />
            )}
            {msg.analysis && !msg.analysis.concept_id && (
              <NoMatchCard onConceptClick={handleSend} />
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble chat-bubble-assistant">
            <div className="chat-bubble-text chat-loading">분석 중...</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {sources.length > 0 && (
          <div className="chat-source-row">
            <label className="chat-source-label">자료 선택 (선택사항)</label>
            <select
              className="chat-source-select"
              value={selectedSourceId}
              onChange={e => setSelectedSourceId(e.target.value)}
            >
              <option value="">자료 없이 시작</option>
              {sources.map(s => (
                <option key={s.source_id} value={s.source_id}>
                  {s.filename}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="chat-input-bar">
          <textarea
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="막힌 개념이나 질문을 한국어로 적어보세요..."
            rows={1}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            보내기
          </button>
        </div>
      </div>
    </div>
  );
}

function AnalysisCard({
  analysis,
  expanded,
  onToggle,
  msgIndex,
  onConceptClick,
}: {
  analysis: AnalyzeResponse;
  expanded: Record<string, boolean>;
  onToggle: (key: string) => void;
  msgIndex: number;
  onConceptClick: (text: string) => void;
}) {
  const repKey = `rep-${msgIndex}`;
  const prereqKey = `prereq-${msgIndex}`;

  return (
    <div className="analysis-card">
      <div className="analysis-concept-header">
        {analysis.canonical_name_ko} {analysis.canonical_name_en}
      </div>

      <div className="analysis-gap">{analysis.suspected_gap}</div>

      {analysis.correction && (
        <div className="analysis-correction">{analysis.correction}</div>
      )}

      {/* 5가지 표현 보기 */}
      {analysis.representations && (
        <div className="analysis-section">
          <button
            className="analysis-section-toggle"
            onClick={() => onToggle(repKey)}
          >
            {expanded[repKey] ? '▾' : '▸'} 5가지 표현 보기
          </button>
          {expanded[repKey] && (
            <div className="analysis-section-content">
              {Object.entries(analysis.representations).map(([key, text]) => (
                <div key={key} className="analysis-rep-block">
                  <div className="analysis-rep-label">
                    {REP_LABELS[key] ?? key}
                  </div>
                  <div className="analysis-rep-text">{text}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 공부 시작 */}
      {analysis.concept_id && (
        <Link
          className="analysis-action-link"
          to={`/study/${analysis.concept_id}`}
          style={{ background: '#15803d' }}
        >
          공부 시작
          <span className="analysis-action-desc">
            {analysis.canonical_name_ko}의 학습 세션을 시작합니다.
          </span>
        </Link>
      )}

      {/* 인출 연습 시작 */}
      {analysis.recommended_actions
        .filter(a => a.route !== null)
        .map(a => (
          <Link
            key={a.action_id}
            className="analysis-action-link"
            to={a.route!}
          >
            {a.label_ko}
            <span className="analysis-action-desc">{a.description_ko}</span>
          </Link>
        ))}

      {/* 선행개념 확인 */}
      {analysis.prerequisite_checks.length > 0 && (
        <div className="analysis-section">
          <button
            className="analysis-section-toggle"
            onClick={() => onToggle(prereqKey)}
          >
            {expanded[prereqKey] ? '▾' : '▸'} 선행개념 확인
            <span className="analysis-prereq-count">
              ({analysis.prerequisite_checks.length}개)
            </span>
          </button>
          {expanded[prereqKey] && (
            <div className="analysis-section-content">
              <div className="analysis-prereqs">
                {analysis.prerequisite_checks.map(p => {
                  const isSeed = SEED_CONCEPTS.some(s => s.id === p.concept_id);
                  return (
                    <div key={p.concept_id} className="analysis-prereq-item">
                      <span className="analysis-prereq-dot">&#9675;</span>
                      {isSeed ? (
                        <button
                          className="analysis-prereq-link"
                          onClick={() => onConceptClick(p.name_ko)}
                        >
                          {p.name_ko} ({p.name_en})
                        </button>
                      ) : (
                        <span>
                          {p.name_ko} ({p.name_en})
                        </span>
                      )}
                      <span className="badge badge-unchecked">{p.status}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NoMatchCard({
  onConceptClick,
}: {
  onConceptClick: (text: string) => void;
}) {
  return (
    <div className="analysis-card analysis-no-match">
      <div className="analysis-no-match-text">
        현재 지원하는 개념:
      </div>
      <div className="analysis-concept-pills">
        {SEED_CONCEPTS.map(c => (
          <button
            key={c.id}
            className="chat-example-pill"
            onClick={() => onConceptClick(c.ko)}
          >
            {c.ko} {c.en}
          </button>
        ))}
      </div>
    </div>
  );
}

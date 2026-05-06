import { useEffect, useState } from 'react';
import { getBank } from '../../api/client';
import type { QuestionItem } from '../../api/types';

interface WhiteRecallStepProps {
  conceptId: string;
  onNext: () => void;
  advancing?: boolean;
  readOnly?: boolean;
}

const QUESTION_TYPE_LABELS: Record<string, string> = {
  define: '정의',
  explain: '설명',
  prove: '증명',
  example: '예시',
  counterexample: '반례',
  visualize: '시각화',
};

export default function WhiteRecallStep({
  conceptId,
  onNext,
  advancing = false,
  readOnly = false,
}: WhiteRecallStepProps) {
  const [recall, setRecall] = useState('');
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(true);

  useEffect(() => {
    // Fetch bank questions (read-only display).
    // If fetch fails, silently degrade to textarea-only.
    getBank(conceptId)
      .then(setQuestions)
      .catch(() => {})
      .finally(() => setLoadingQuestions(false));
  }, [conceptId]);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>인출 연습</h2>

      <div style={{
        background: '#eff6ff', border: '1px solid #bfdbfe',
        borderRadius: 6, padding: '12px 16px', marginBottom: 20,
        fontSize: 14, color: '#1e40af',
      }}>
        교재를 덮고, 아래 질문들에 대해 처음부터 설명해 보세요.
      </div>

      {/* Read-only bank questions */}
      {!loadingQuestions && questions.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#374151' }}>
            인출 질문 ({questions.length}개)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {questions.map((q, i) => (
              <div key={q.id} style={{
                padding: '10px 14px', borderRadius: 6,
                background: '#f8fafc', border: '1px solid #e2e8f0',
              }}>
                <span style={{ fontSize: 12, color: '#64748b', marginRight: 8 }}>
                  [{QUESTION_TYPE_LABELS[q.question_type] ?? q.question_type}]
                </span>
                <span style={{ fontSize: 14, color: '#1e293b' }}>
                  {i + 1}. {q.question}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <textarea
        className="recall-textarea"
        value={recall}
        onChange={(e) => setRecall(e.target.value)}
        placeholder="이 개념을 처음부터 설명해 보세요. 정의, 핵심 아이디어, 예시, 증명 구조 등을 자유롭게 작성하세요..."
        style={{ minHeight: 200 }}
        disabled={readOnly}
      />

      {!readOnly && (
        <button
          className="submit-btn"
          onClick={onNext}
          disabled={!recall.trim() || advancing}
          style={{ marginTop: 16 }}
        >
          {advancing ? '처리 중...' : '제출'}
        </button>
      )}

      {!readOnly && !recall.trim() && (
        <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 8 }}>
          내용을 작성하면 제출할 수 있습니다.
        </p>
      )}
    </div>
  );
}

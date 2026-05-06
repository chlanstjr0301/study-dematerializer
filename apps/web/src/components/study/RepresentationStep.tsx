import { useState } from 'react';
import type { SelfExplainResponse } from '../../api/types';

interface RepresentationStepProps {
  representations: Record<string, string>;
  onNext: () => void;
  onSubmitSelfExplanation: (representationType: string, learnerExplanation: string) => Promise<SelfExplainResponse>;
  selfExplanationResults: Record<string, SelfExplainResponse>;
  selfExplainSubmitting: boolean;
  advancing?: boolean;
  readOnly?: boolean;
}

const REP_LABELS: Record<string, string> = {
  formal: '정의 (Formal)',
  intuitive: '직관 (Intuitive)',
  visual: '시각적 (Visual)',
  counterexample: '반례 (Counterexample)',
  proof_schema: '증명 구조 (Proof Schema)',
};

const PREFERRED_ORDER = ['formal', 'intuitive', 'visual', 'counterexample', 'proof_schema'];
const REQUIRED_REPS = new Set(['formal', 'proof_schema']);

export default function RepresentationStep({
  representations,
  onNext,
  onSubmitSelfExplanation,
  selfExplanationResults,
  selfExplainSubmitting,
  advancing = false,
  readOnly = false,
}: RepresentationStepProps) {
  // Build ordered list of representations
  const repEntries = PREFERRED_ORDER
    .filter(key => key in representations)
    .map(key => ({ key, label: REP_LABELS[key] ?? key, content: representations[key] }));
  // Append any keys not in PREFERRED_ORDER
  for (const key of Object.keys(representations)) {
    if (!PREFERRED_ORDER.includes(key)) {
      repEntries.push({ key, label: REP_LABELS[key] ?? key, content: representations[key] });
    }
  }

  const [currentRep, setCurrentRep] = useState(0);
  const [viewedReps, setViewedReps] = useState<Set<number>>(new Set([0]));
  const [explanationText, setExplanationText] = useState<Record<string, string>>({});

  function goToRep(index: number) {
    setCurrentRep(index);
    setViewedReps(prev => new Set(prev).add(index));
  }

  async function handleSubmitExplanation(repKey: string) {
    const text = explanationText[repKey] ?? '';
    if (!text.trim()) return;
    await onSubmitSelfExplanation(repKey, text);
  }

  const allViewed = viewedReps.size >= repEntries.length;
  const rep = repEntries[currentRep];
  const submittedCount = Object.keys(selfExplanationResults).length;

  if (repEntries.length === 0) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>표현 학습</h2>
        <p style={{ color: '#94a3b8' }}>표현 데이터가 없습니다.</p>
      </div>
    );
  }

  const currentResult = selfExplanationResults[rep.key];
  const isRequired = REQUIRED_REPS.has(rep.key);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>표현 학습</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        {repEntries.length}가지 표현을 순서대로 학습합니다. 각 표현을 읽고 자신의 말로 설명해 보세요.
      </p>

      {/* Progress indicator */}
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
        자기 설명 제출: {submittedCount}/{repEntries.length}
        {submittedCount < repEntries.length && (
          <span style={{ color: '#f59e0b', marginLeft: 8 }}>
            (formal, proof_schema는 필수)
          </span>
        )}
      </div>

      {/* Representation card */}
      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0',
        borderRadius: 8, padding: '20px 24px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            [{currentRep + 1}/{repEntries.length}] {rep.label}
            {isRequired && <span style={{ color: '#dc2626', marginLeft: 4 }}>*필수</span>}
          </span>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            {viewedReps.size}/{repEntries.length} 확인
          </span>
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.7, color: '#1e293b', whiteSpace: 'pre-wrap' }}>
          {rep.content}
        </div>
      </div>

      {/* Self-explanation textarea */}
      {!readOnly && !currentResult && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
            이 표현을 자신의 말로 설명해 보세요
            {isRequired && <span style={{ color: '#dc2626' }}> (필수)</span>}
          </label>
          <textarea
            className="recall-textarea"
            value={explanationText[rep.key] ?? ''}
            onChange={(e) => setExplanationText(prev => ({ ...prev, [rep.key]: e.target.value }))}
            placeholder="이 표현의 핵심 내용을 자유롭게 작성하세요..."
            style={{ minHeight: 100 }}
            disabled={selfExplainSubmitting}
          />
          <button
            className="submit-btn"
            style={{ marginTop: 8, fontSize: 13 }}
            onClick={() => handleSubmitExplanation(rep.key)}
            disabled={!(explanationText[rep.key] ?? '').trim() || selfExplainSubmitting}
          >
            {selfExplainSubmitting ? '평가 중...' : '자기 설명 제출'}
          </button>
        </div>
      )}

      {/* Evaluation result */}
      {currentResult && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 6, padding: '12px 16px', marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#15803d' }}>
              평가 결과
            </span>
            <span style={{
              fontSize: 12, padding: '2px 8px', borderRadius: 4,
              background: currentResult.accuracy_score >= 0.85 ? '#bbf7d0' :
                currentResult.accuracy_score >= 0.5 ? '#fef3c7' : '#fecaca',
              color: currentResult.accuracy_score >= 0.85 ? '#15803d' :
                currentResult.accuracy_score >= 0.5 ? '#92400e' : '#b91c1c',
            }}>
              정확도: {Math.round(currentResult.accuracy_score * 100)}%
            </span>
          </div>
          {currentResult.feedback && (
            <p style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>
              {currentResult.feedback}
            </p>
          )}
          {currentResult.missing_elements.length > 0 && (
            <div style={{ fontSize: 12, color: '#92400e', marginTop: 4 }}>
              <span style={{ fontWeight: 500 }}>부족한 부분:</span>
              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                {currentResult.missing_elements.map((el, i) => (
                  <li key={i}>{el}</li>
                ))}
              </ul>
            </div>
          )}
          {currentResult.errors.length > 0 && (
            <div style={{ fontSize: 12, color: '#b91c1c', marginTop: 4 }}>
              <span style={{ fontWeight: 500 }}>오류:</span>
              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                {currentResult.errors.map((el, i) => (
                  <li key={i}>{el}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Read-only: show submitted result without textarea */}
      {readOnly && currentResult && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 6, padding: '12px 16px', marginBottom: 16,
        }}>
          <span style={{ fontSize: 12, color: '#15803d', fontWeight: 500 }}>
            제출 완료 — 정확도: {Math.round(currentResult.accuracy_score * 100)}%
          </span>
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button
          className="submit-btn"
          style={{ background: '#64748b' }}
          onClick={() => goToRep(currentRep - 1)}
          disabled={currentRep === 0}
        >
          &larr; 이전 표현
        </button>
        <button
          className="submit-btn"
          onClick={() => goToRep(currentRep + 1)}
          disabled={currentRep === repEntries.length - 1}
        >
          다음 표현 &rarr;
        </button>
      </div>

      {/* Advance button */}
      {!readOnly && allViewed && (
        <>
          {submittedCount < repEntries.length && (
            <p style={{ fontSize: 12, color: '#f59e0b', marginBottom: 8 }}>
              모든 표현에 대해 자기 설명을 제출하는 것이 좋습니다. ({submittedCount}/{repEntries.length} 제출됨)
            </p>
          )}
          <button className="submit-btn" style={{ background: '#15803d' }} onClick={onNext} disabled={advancing}>
            {advancing ? '처리 중...' : '다음 단계 →'}
          </button>
        </>
      )}
      {!allViewed && (
        <p style={{ fontSize: 13, color: '#94a3b8' }}>
          모든 표현을 확인하면 다음 단계로 진행할 수 있습니다.
        </p>
      )}
    </div>
  );
}

import { useState } from 'react';
import type { MisconceptionInfo } from '../../api/types';

interface MisconceptionStepProps {
  misconceptions: MisconceptionInfo[];
  onNext: () => void;
  advancing?: boolean;
  readOnly?: boolean;
}

export default function MisconceptionStep({
  misconceptions,
  onNext,
  advancing = false,
  readOnly = false,
}: MisconceptionStepProps) {
  const [answers, setAnswers] = useState<Record<number, boolean | null>>({});
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});

  function handleAnswer(index: number, answer: boolean) {
    if (readOnly) return;
    setAnswers(prev => ({ ...prev, [index]: answer }));
    setRevealed(prev => ({ ...prev, [index]: true }));
  }

  const allAnswered = misconceptions.length > 0 && misconceptions.every((_, i) => revealed[i]);

  if (misconceptions.length === 0) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>주의할 오개념</h2>
        <p style={{ color: '#94a3b8' }}>오개념 데이터가 없습니다.</p>
        {!readOnly && (
          <button className="submit-btn" onClick={onNext} disabled={advancing}>
            {advancing ? '처리 중...' : '다음 단계 →'}
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>주의할 오개념</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        아래 문장이 참인지 거짓인지 판단해 보세요.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
        {misconceptions.map((item, i) => (
          <div
            key={item.id}
            style={{
              border: `1px solid ${revealed[i] ? (answers[i] === item.is_correct ? '#bbf7d0' : '#fecaca') : '#e5e7eb'}`,
              borderRadius: 8, padding: '14px 18px',
              background: revealed[i] ? (answers[i] === item.is_correct ? '#f0fdf4' : '#fef2f2') : '#fff',
            }}
          >
            <p style={{ fontWeight: 500, marginBottom: 10, fontSize: 14 }}>
              &ldquo;{item.claim}&rdquo;
            </p>

            {!revealed[i] && !readOnly ? (
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="submit-btn"
                  style={{ padding: '6px 16px', fontSize: 13 }}
                  onClick={() => handleAnswer(i, true)}
                >
                  참
                </button>
                <button
                  className="submit-btn"
                  style={{ padding: '6px 16px', fontSize: 13, background: '#64748b' }}
                  onClick={() => handleAnswer(i, false)}
                >
                  거짓
                </button>
              </div>
            ) : revealed[i] ? (
              <div style={{ fontSize: 13, color: '#374151', marginTop: 8 }}>
                <span style={{
                  fontWeight: 600,
                  color: answers[i] === item.is_correct ? '#15803d' : '#b91c1c',
                }}>
                  {answers[i] === item.is_correct ? '정답!' : '오답'}
                </span>
                <span style={{ color: '#888', marginLeft: 8 }}>
                  (정답: {item.is_correct ? '참' : '거짓'})
                </span>
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {!readOnly && allAnswered && (
        <button className="submit-btn" onClick={onNext} disabled={advancing}>
          {advancing ? '처리 중...' : '다음 단계 →'}
        </button>
      )}
      {!allAnswered && !readOnly && (
        <p style={{ fontSize: 13, color: '#94a3b8' }}>
          모든 문항에 답하면 다음 단계로 진행할 수 있습니다.
        </p>
      )}
    </div>
  );
}

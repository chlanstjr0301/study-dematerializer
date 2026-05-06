import { useState } from 'react';

interface MisconceptionStepProps {
  conceptId: string;
  onNext: () => void;
}

interface MisconceptionItem {
  statement: string;
  isTrue: boolean;
  explanation: string;
}

const SAMPLE_MISCONCEPTIONS: Record<string, MisconceptionItem[]> = {
  compactness: [
    {
      statement: '콤팩트 집합은 항상 유계이다.',
      isTrue: true,
      explanation: '맞습니다. 콤팩트 집합은 유계이고 폐집합입니다 (유클리드 공간에서).',
    },
    {
      statement: '유계이고 폐인 집합은 항상 콤팩트하다.',
      isTrue: false,
      explanation: '유클리드 공간에서는 맞지만 (하이네-보렐), 일반 거리 공간에서는 틀립니다.',
    },
    {
      statement: '콤팩트 집합의 부분집합은 항상 콤팩트하다.',
      isTrue: false,
      explanation: '폐부분집합만 콤팩트합니다. 열린 부분집합은 콤팩트하지 않을 수 있습니다.',
    },
  ],
  connectedness: [
    {
      statement: '연결 집합은 항상 경로 연결이다.',
      isTrue: false,
      explanation: '연결이 경로 연결보다 약한 조건입니다. 반례: 위상수학자의 사인 곡선.',
    },
    {
      statement: '연속 함수의 상은 연결 집합을 보존한다.',
      isTrue: true,
      explanation: '맞습니다. 연속 함수는 연결성을 보존합니다.',
    },
  ],
  uniform_continuity: [
    {
      statement: '균등 연속이면 연속이다.',
      isTrue: true,
      explanation: '맞습니다. 균등 연속은 연속보다 강한 조건입니다.',
    },
    {
      statement: '연속 함수는 항상 균등 연속이다.',
      isTrue: false,
      explanation: '반례: f(x) = x²은 R에서 연속이지만 균등 연속이 아닙니다.',
    },
  ],
};

export default function MisconceptionStep({ conceptId, onNext }: MisconceptionStepProps) {
  const misconceptions = SAMPLE_MISCONCEPTIONS[conceptId] ?? SAMPLE_MISCONCEPTIONS['compactness']!;
  const [answers, setAnswers] = useState<Record<number, boolean | null>>({});
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});

  function handleAnswer(index: number, answer: boolean) {
    setAnswers(prev => ({ ...prev, [index]: answer }));
    setRevealed(prev => ({ ...prev, [index]: true }));
  }

  const allAnswered = misconceptions.every((_, i) => revealed[i]);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>주의할 오개념</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        아래 문장이 참인지 거짓인지 판단해 보세요.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
        {misconceptions.map((item, i) => (
          <div
            key={i}
            style={{
              border: `1px solid ${revealed[i] ? (answers[i] === item.isTrue ? '#bbf7d0' : '#fecaca') : '#e5e7eb'}`,
              borderRadius: 8, padding: '14px 18px',
              background: revealed[i] ? (answers[i] === item.isTrue ? '#f0fdf4' : '#fef2f2') : '#fff',
            }}
          >
            <p style={{ fontWeight: 500, marginBottom: 10, fontSize: 14 }}>
              "{item.statement}"
            </p>

            {!revealed[i] ? (
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
            ) : (
              <div style={{ fontSize: 13, color: '#374151', marginTop: 8 }}>
                <span style={{
                  fontWeight: 600,
                  color: answers[i] === item.isTrue ? '#15803d' : '#b91c1c',
                }}>
                  {answers[i] === item.isTrue ? '정답!' : '오답'}
                </span>
                <span style={{ color: '#888', marginLeft: 8 }}>
                  (정답: {item.isTrue ? '참' : '거짓'})
                </span>
                <p style={{ marginTop: 6, color: '#555' }}>{item.explanation}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {allAnswered && (
        <button className="submit-btn" onClick={onNext}>
          다음 단계 →
        </button>
      )}
      {!allAnswered && (
        <p style={{ fontSize: 13, color: '#94a3b8' }}>
          모든 문항에 답하면 다음 단계로 진행할 수 있습니다.
        </p>
      )}
    </div>
  );
}

import { useState } from 'react';

interface RepresentationStepProps {
  representations: Record<string, string>;
  onNext: () => void;
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

export default function RepresentationStep({
  representations,
  onNext,
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

  function goToRep(index: number) {
    setCurrentRep(index);
    setViewedReps(prev => new Set(prev).add(index));
  }

  const allViewed = viewedReps.size >= repEntries.length;
  const rep = repEntries[currentRep];

  if (repEntries.length === 0) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>표현 학습</h2>
        <p style={{ color: '#94a3b8' }}>표현 데이터가 없습니다.</p>
      </div>
    );
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>표현 학습</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        {repEntries.length}가지 표현을 순서대로 학습합니다. 각 표현을 읽고 이해한 뒤 다음으로 넘어가세요.
      </p>

      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0',
        borderRadius: 8, padding: '20px 24px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            [{currentRep + 1}/{repEntries.length}] {rep.label}
          </span>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            {viewedReps.size}/{repEntries.length} 완료
          </span>
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.7, color: '#1e293b', whiteSpace: 'pre-wrap' }}>
          {rep.content}
        </div>
      </div>

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

      {!readOnly && allViewed && (
        <button className="submit-btn" style={{ background: '#15803d' }} onClick={onNext} disabled={advancing}>
          {advancing ? '처리 중...' : '다음 단계 →'}
        </button>
      )}
      {!allViewed && (
        <p style={{ fontSize: 13, color: '#94a3b8' }}>
          모든 표현을 확인하면 다음 단계로 진행할 수 있습니다.
        </p>
      )}
    </div>
  );
}

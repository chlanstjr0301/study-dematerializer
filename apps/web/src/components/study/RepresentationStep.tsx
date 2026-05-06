import { useState } from 'react';

interface RepresentationStepProps {
  onNext: () => void;
}

const REP_TYPES = [
  { key: 'formal', label: '정의' },
  { key: 'intuitive', label: '직관' },
  { key: 'visual', label: '시각적 설명' },
  { key: 'counterexample', label: '반례' },
  { key: 'proof_schema', label: '증명 구조' },
];

const PLACEHOLDER_CONTENT: Record<string, string> = {
  formal: '집합 K가 콤팩트하다 ⟺ K의 모든 열린 덮개가 유한 부분 덮개를 가진다.',
  intuitive: '"아무리 많은 열린 집합으로 덮어도, 유한 개만 골라도 충분하다" — 집합이 충분히 작고 잘 정돈되어 있다는 뜻.',
  visual: '[시각적 표현] 열린 덮개에서 유한 개를 선택하여 K를 완전히 덮는 과정을 상상해 보세요.',
  counterexample: '(0, 1)은 콤팩트하지 않다: {(1/n, 1-1/n) : n≥2}는 유한 부분 덮개를 갖지 않는 열린 덮개.',
  proof_schema: '콤팩트 ⟹ 유계+폐: 귀류법. 유계가 아니면 → 수열 구성 → 수렴 부분수열 없음 → 모순.',
};

export default function RepresentationStep({ onNext }: RepresentationStepProps) {
  const [currentRep, setCurrentRep] = useState(0);
  const [viewedReps, setViewedReps] = useState<Set<number>>(new Set([0]));

  function goToRep(index: number) {
    setCurrentRep(index);
    setViewedReps(prev => new Set(prev).add(index));
  }

  const allViewed = viewedReps.size === REP_TYPES.length;
  const rep = REP_TYPES[currentRep];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>표현 학습</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        5가지 표현을 순서대로 학습합니다. 각 표현을 읽고 이해한 뒤 다음으로 넘어가세요.
      </p>

      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0',
        borderRadius: 8, padding: '20px 24px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            [{currentRep + 1}/{REP_TYPES.length}] {rep.label} ({rep.key})
          </span>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            {viewedReps.size}/{REP_TYPES.length} 완료
          </span>
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.7, color: '#1e293b' }}>
          {PLACEHOLDER_CONTENT[rep.key]}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button
          className="submit-btn"
          style={{ background: '#64748b' }}
          onClick={() => goToRep(currentRep - 1)}
          disabled={currentRep === 0}
        >
          ← 이전 표현
        </button>
        <button
          className="submit-btn"
          onClick={() => goToRep(currentRep + 1)}
          disabled={currentRep === REP_TYPES.length - 1}
        >
          다음 표현 →
        </button>
      </div>

      {allViewed && (
        <button className="submit-btn" style={{ background: '#15803d' }} onClick={onNext}>
          다음 단계 →
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

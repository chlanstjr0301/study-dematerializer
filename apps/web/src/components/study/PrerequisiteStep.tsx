import { useState } from 'react';

interface PrerequisiteStepProps {
  conceptId: string;
  onNext: () => void;
}

const SAMPLE_PREREQUISITES: Record<string, { id: string; ko: string; en: string }[]> = {
  compactness: [
    { id: 'metric_space', ko: '거리 공간', en: 'metric space' },
    { id: 'open_set', ko: '열린 집합', en: 'open set' },
    { id: 'open_cover', ko: '열린 덮개', en: 'open cover' },
    { id: 'heine_borel', ko: '하이네-보렐 정리', en: 'Heine-Borel theorem' },
  ],
  connectedness: [
    { id: 'metric_space', ko: '거리 공간', en: 'metric space' },
    { id: 'open_set', ko: '열린 집합', en: 'open set' },
    { id: 'continuity', ko: '연속성', en: 'continuity' },
  ],
  uniform_continuity: [
    { id: 'metric_space', ko: '거리 공간', en: 'metric space' },
    { id: 'continuity', ko: '연속성', en: 'continuity' },
    { id: 'compactness', ko: '옹골성', en: 'compactness' },
  ],
};

export default function PrerequisiteStep({ conceptId, onNext }: PrerequisiteStepProps) {
  const prereqs = SAMPLE_PREREQUISITES[conceptId] ?? SAMPLE_PREREQUISITES['compactness']!;
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const uncheckedCount = prereqs.filter(p => !checked[p.id]).length;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>선행 확인</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        아래 선행 개념을 편하게 설명할 수 있는지 체크해 주세요.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
        {prereqs.map((p) => (
          <label
            key={p.id}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 14px', borderRadius: 6,
              background: checked[p.id] ? '#f0fdf4' : '#fafafa',
              border: `1px solid ${checked[p.id] ? '#bbf7d0' : '#e5e7eb'}`,
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={!!checked[p.id]}
              onChange={(e) => setChecked(prev => ({ ...prev, [p.id]: e.target.checked }))}
            />
            <span style={{ fontWeight: 500 }}>{p.ko}</span>
            <span style={{ color: '#888', fontSize: 13 }}>({p.en})</span>
            <span style={{ marginLeft: 'auto', fontSize: 12, color: '#888' }}>
              편하게 설명할 수 있나요?
            </span>
          </label>
        ))}
      </div>

      {uncheckedCount > 0 && (
        <div style={{
          background: '#fff7ed', border: '1px solid #fed7aa',
          borderRadius: 6, padding: '10px 14px', marginBottom: 16,
          fontSize: 13, color: '#9a3412',
        }}>
          체크하지 않은 선행 개념이 {uncheckedCount}개 있습니다. 학습 중 해당 부분을 더 주의깊게 살펴보세요.
        </div>
      )}

      <button className="submit-btn" onClick={onNext}>
        다음 단계 →
      </button>
    </div>
  );
}

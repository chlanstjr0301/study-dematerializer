import { useState } from 'react';
import type { StudyPrerequisiteInfo } from '../../api/types';

interface PrerequisiteStepProps {
  prerequisites: StudyPrerequisiteInfo[];
  onNext: () => void;
  advancing?: boolean;
  readOnly?: boolean;
}

const MASTERY_BADGE: Record<string, { label: string; className: string }> = {
  unknown: { label: '미확인', className: 'badge-overdue' },
  partial: { label: '부분', className: 'badge-partial' },
  solid: { label: '숙련', className: 'badge-solid' },
};

export default function PrerequisiteStep({
  prerequisites,
  onNext,
  advancing = false,
  readOnly = false,
}: PrerequisiteStepProps) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const uncheckedCount = prerequisites.filter(p => !checked[p.concept_id]).length;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>선행 확인</h2>
      <p style={{ fontSize: 14, color: '#555', marginBottom: 16 }}>
        아래 선행 개념을 편하게 설명할 수 있는지 체크해 주세요.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
        {prerequisites.map((p) => {
          const badge = MASTERY_BADGE[p.mastery] ?? MASTERY_BADGE['unknown'];
          return (
            <label
              key={p.concept_id}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 14px', borderRadius: 6,
                background: checked[p.concept_id] ? '#f0fdf4' : '#fafafa',
                border: `1px solid ${checked[p.concept_id] ? '#bbf7d0' : '#e5e7eb'}`,
                cursor: readOnly ? 'default' : 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={!!checked[p.concept_id]}
                onChange={(e) => setChecked(prev => ({ ...prev, [p.concept_id]: e.target.checked }))}
                disabled={readOnly}
              />
              <span style={{ fontWeight: 500 }}>{p.name_ko}</span>
              <span className={`badge ${badge.className}`} style={{ fontSize: 11 }}>
                {badge.label}
              </span>
              <span style={{ marginLeft: 'auto', fontSize: 12, color: '#888' }}>
                편하게 설명할 수 있나요?
              </span>
            </label>
          );
        })}
      </div>

      {uncheckedCount > 0 && !readOnly && (
        <div style={{
          background: '#fff7ed', border: '1px solid #fed7aa',
          borderRadius: 6, padding: '10px 14px', marginBottom: 16,
          fontSize: 13, color: '#9a3412',
        }}>
          체크하지 않은 선행 개념이 {uncheckedCount}개 있습니다. 학습 중 해당 부분을 더 주의깊게 살펴보세요.
        </div>
      )}

      {!readOnly && (
        <button className="submit-btn" onClick={onNext} disabled={advancing}>
          {advancing ? '처리 중...' : '다음 단계 →'}
        </button>
      )}
    </div>
  );
}

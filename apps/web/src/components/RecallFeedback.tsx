import type { RecallFeedbackData } from '../api/types';

function accuracyBadge(score: number) {
  if (score >= 0.85) return { label: `${(score * 100).toFixed(0)}%`, color: '#15803d', bg: '#dcfce7' };
  if (score >= 0.50) return { label: `${(score * 100).toFixed(0)}%`, color: '#92400e', bg: '#fef9c3' };
  return { label: `${(score * 100).toFixed(0)}%`, color: '#b91c1c', bg: '#fee2e2' };
}

export default function RecallFeedback({ data }: { data: RecallFeedbackData }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <p className="empty-state">No recall feedback recorded.</p>;
  }

  const sorted = [...data].sort((a, b) => {
    if (a.needs_human_review !== b.needs_human_review)
      return a.needs_human_review ? -1 : 1;
    return a.accuracy_score - b.accuracy_score;
  });

  return (
    <div>
      {sorted.map((item, i) => {
        const badge = accuracyBadge(item.accuracy_score);
        return (
          <div key={i} className="feedback-card" style={{ marginBottom: 12 }}>
            {item.needs_human_review && (
              <div style={{
                background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: 4,
                padding: '4px 10px', marginBottom: 8, fontSize: 13, color: '#92400e',
              }}>
                ⚠ Needs human review
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#555' }}>
                {item.question_id}
              </span>
              <span style={{
                background: badge.bg, color: badge.color, padding: '1px 8px',
                borderRadius: 10, fontSize: 12, fontWeight: 600,
              }}>
                {badge.label}
              </span>
            </div>
            <p style={{ fontSize: 13, marginBottom: 6, color: '#444' }}>
              <strong>Type:</strong> {item.representation_type}
            </p>
            {item.feedback && (
              <p style={{ fontSize: 13, marginBottom: 6 }}>{item.feedback}</p>
            )}
            {item.missing_elements.length > 0 && (
              <div style={{ marginTop: 6 }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>
                  Missing elements:
                </p>
                <ul style={{ paddingLeft: 18, fontSize: 13 }}>
                  {item.missing_elements.map((el, j) => <li key={j}>{el}</li>)}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

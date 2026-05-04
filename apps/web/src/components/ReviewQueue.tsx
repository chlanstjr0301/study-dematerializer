import type { ReviewQueueData } from '../api/types';

export default function ReviewQueue({ data }: { data: ReviewQueueData }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <p className="empty-state">Review queue is empty.</p>;
  }

  return (
    <div>
      {data.map((item, i) => (
        <div key={i} className="feedback-card">
          <dl>
            {Object.entries(item).map(([k, v]) => (
              <span key={k} style={{ display: 'contents' }}>
                <dt>{k}</dt>
                <dd>{typeof v === 'object' ? JSON.stringify(v) : String(v ?? '—')}</dd>
              </span>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}

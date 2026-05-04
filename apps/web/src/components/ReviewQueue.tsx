import type { ReviewQueueData } from '../api/types';

function dueStatusStyle(status: string) {
  if (status === 'overdue')   return { color: '#b91c1c', bg: '#fee2e2' };
  if (status === 'due_today') return { color: '#92400e', bg: '#fef9c3' };
  return { color: '#15803d', bg: '#dcfce7' };
}

export default function ReviewQueue({ data }: { data: ReviewQueueData }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <p className="empty-state">Review queue is empty.</p>;
  }

  return (
    <table className="table-simple">
      <thead>
        <tr>
          <th>Concept</th>
          <th>Next Review</th>
          <th>Weakest Rep</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item, i) => {
          const style = dueStatusStyle(item.due_status);
          return (
            <tr key={i}>
              <td>{item.concept_id}</td>
              <td>{item.next_review_date}</td>
              <td>{item.weakest_representation}</td>
              <td>
                <span style={{
                  background: style.bg, color: style.color,
                  padding: '1px 8px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                }}>
                  {item.due_status}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

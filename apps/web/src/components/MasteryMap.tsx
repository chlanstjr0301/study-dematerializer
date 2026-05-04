import type { MasteryMapData } from '../api/types';

function masteryColor(level: string) {
  if (level === 'solid')   return '#15803d';
  if (level === 'partial') return '#92400e';
  return '#b91c1c';
}

export default function MasteryMap({ data }: { data: MasteryMapData }) {
  const reps = Array.isArray(data.representations) ? data.representations : [];

  return (
    <div>
      <table className="table-simple" style={{ marginBottom: 12 }}>
        <tbody>
          <tr>
            <th>Concept</th>
            <td>{data.concept_id ?? '—'}</td>
          </tr>
          <tr>
            <th>Overall mastery</th>
            <td>
              <span className={`badge badge-${data.overall_mastery ?? 'unknown'}`}>
                {data.overall_mastery ?? 'unknown'}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      {reps.length > 0 && (
        <>
          <h4>Representations</h4>
          <table className="table-simple">
            <thead>
              <tr>
                <th>Type</th>
                <th>Before</th>
                <th>After</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {reps.map((r, i) => (
                <tr key={i}>
                  <td>{r.type}</td>
                  <td style={{ color: masteryColor(r.before) }}>{r.before}</td>
                  <td style={{ color: masteryColor(r.after), fontWeight: 600 }}>{r.after}</td>
                  <td>{(r.accuracy_score * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {Array.isArray(data.weakest_links) && data.weakest_links.length > 0 && (
        <>
          <h4 style={{ marginTop: 12 }}>Weakest links</h4>
          <ul style={{ paddingLeft: 20, fontSize: 14 }}>
            {data.weakest_links.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

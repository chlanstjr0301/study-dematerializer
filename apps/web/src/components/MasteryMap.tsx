import type { MasteryMapData } from '../api/types';

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
                <th>Mastery</th>
              </tr>
            </thead>
            <tbody>
              {reps.map((r, i) => {
                const row = r as Record<string, unknown>;
                return (
                  <tr key={i}>
                    <td>{String(row['type'] ?? row['representation_type'] ?? '—')}</td>
                    <td>
                      <span className={`badge badge-${String(row['mastery'] ?? 'unknown')}`}>
                        {String(row['mastery'] ?? '—')}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {Array.isArray(data.weakest_links) && data.weakest_links.length > 0 && (
        <>
          <h4 style={{ marginTop: 12 }}>Weakest links</h4>
          <ul style={{ paddingLeft: 20, fontSize: 14 }}>
            {data.weakest_links.map((w, i) => (
              <li key={i}>{String(w)}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getSessions } from '../api/client';
import type { SessionSummaryItem } from '../api/types';

export default function SessionHistory() {
  const [sessions, setSessions] = useState<SessionSummaryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch((e: unknown) => setError(String(e)));
  }, []);

  return (
    <div>
      <h1>Session History</h1>

      <div className="card">
        {error ? (
          <p className="error-text">{error}</p>
        ) : sessions === null ? (
          <p className="loading">Loading sessions…</p>
        ) : sessions.length === 0 ? (
          <p className="empty-state">No sessions found.</p>
        ) : (
          <table className="table-simple">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Concept</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>
                    <Link className="session-link" to={`/sessions/${s.session_id}`}>
                      {s.session_id}
                    </Link>
                  </td>
                  <td>{s.concept_id}</td>
                  <td>{s.started_at}</td>
                  <td>{s.ended_at ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

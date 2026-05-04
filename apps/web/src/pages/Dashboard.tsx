import { useEffect, useState } from 'react';
import { getHealth, getDue, getStudyMd } from '../api/client';
import type { HealthResponse, DueConceptItem, StudyMdResponse } from '../api/types';
import StudyMdViewer from '../components/StudyMdViewer';

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [due, setDue] = useState<DueConceptItem[] | null>(null);
  const [dueError, setDueError] = useState<string | null>(null);

  const [studyMd, setStudyMd] = useState<StudyMdResponse | null>(null);
  const [studyMdError, setStudyMdError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: unknown) => setHealthError(String(e)));

    getDue()
      .then(setDue)
      .catch((e: unknown) => setDueError(String(e)));

    getStudyMd()
      .then(setStudyMd)
      .catch((e: unknown) => setStudyMdError(String(e)));
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>

      {/* API health */}
      <div className="section">
        <h2>API Status</h2>
        <div className="card">
          {healthError ? (
            <span className="error-text">Cannot reach API: {healthError}</span>
          ) : health ? (
            <span className="badge badge-ok">API: {health.status}</span>
          ) : (
            <span className="loading">Checking…</span>
          )}
        </div>
      </div>

      {/* Due today */}
      <div className="section">
        <h2>Review Due</h2>
        <div className="card">
          {dueError ? (
            <p className="error-text">{dueError}</p>
          ) : due === null ? (
            <p className="loading">Loading…</p>
          ) : due.length === 0 ? (
            <p className="empty-state">Nothing due for review.</p>
          ) : (
            <table className="table-simple">
              <thead>
                <tr>
                  <th>Concept</th>
                  <th>Next review</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {due.map((item) => (
                  <tr key={item.concept_id}>
                    <td>{item.concept_id}</td>
                    <td>{item.next_review ?? '—'}</td>
                    <td>
                      <span className={item.overdue ? 'badge badge-overdue' : 'badge'}>
                        {item.overdue ? 'overdue' : 'due'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* STUDY.md */}
      <div className="section">
        <h2>STUDY.md</h2>
        <div className="card">
          {studyMdError ? (
            <p className="error-text">{studyMdError}</p>
          ) : studyMd === null ? (
            <p className="loading">Loading…</p>
          ) : (
            <StudyMdViewer content={studyMd.content} />
          )}
        </div>
      </div>
    </div>
  );
}

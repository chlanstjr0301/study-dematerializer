import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getHealth, getDue, getStudyMd, getWeak } from '../api/client';
import type { HealthResponse, DueConceptItem, StudyMdResponse, WeakRepItem } from '../api/types';
import StudyMdViewer from '../components/StudyMdViewer';

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [due, setDue] = useState<DueConceptItem[] | null>(null);
  const [dueError, setDueError] = useState<string | null>(null);

  const [weak, setWeak] = useState<WeakRepItem[] | null>(null);

  const [studyMd, setStudyMd] = useState<StudyMdResponse | null>(null);
  const [studyMdError, setStudyMdError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: unknown) => setHealthError(String(e)));

    getDue()
      .then(setDue)
      .catch((e: unknown) => setDueError(String(e)));

    getWeak()
      .then(setWeak)
      .catch(() => setWeak([]));   // silent — dashboard functional without this

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
                  <th>Mastery</th>
                  <th>Weak Reps</th>
                  <th>Next Review</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {due.map((item) => {
                  const href = item.suggested_mode === 'weak_only' && item.target_representations.length > 0
                    ? `/recall?concept=${item.concept_id}&target_reps=${item.target_representations.join(',')}`
                    : `/recall?concept=${item.concept_id}`;
                  const label = item.suggested_mode === 'weak_only' ? 'Review Weak →' : 'Full Review →';
                  const masteryClass =
                    item.overall_mastery === 'solid' ? 'badge badge-ok' :
                    item.overall_mastery === 'partial' ? 'badge badge-partial' :
                    'badge badge-overdue';
                  return (
                    <tr key={item.concept_id}>
                      <td>{item.concept_id}</td>
                      <td><span className={masteryClass}>{item.overall_mastery}</span></td>
                      <td>{item.weak_rep_count > 0 ? item.weak_rep_count : '—'}</td>
                      <td>{item.next_review ?? '—'}</td>
                      <td>
                        <span className={item.overdue ? 'badge badge-overdue' : 'badge'}>
                          {item.overdue ? 'overdue' : 'due'}
                        </span>
                      </td>
                      <td>
                        <Link to={href} className="session-link">{label}</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Weak Representations */}
      {weak !== null && weak.length > 0 && (
        <div className="section">
          <h2>Weak Representations</h2>
          <div className="card">
            <table className="table-simple">
              <thead>
                <tr>
                  <th>Concept</th>
                  <th>Type</th>
                  <th>Mastery</th>
                  <th>Last reviewed</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {weak.map((item) => (
                  <tr key={`${item.concept_id}-${item.rep_type}`}>
                    <td>{item.concept_id}</td>
                    <td><code>{item.rep_type}</code></td>
                    <td>
                      <span className={item.mastery === 'unknown' ? 'badge badge-overdue' : 'badge badge-partial'}>
                        {item.mastery}
                      </span>
                    </td>
                    <td>{item.last_reviewed ?? '—'}</td>
                    <td>
                      <Link
                        to={`/recall?concept=${item.concept_id}&rep_type=${item.rep_type}`}
                        className="session-link"
                      >
                        Strengthen →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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

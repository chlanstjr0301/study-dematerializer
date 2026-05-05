import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getHealth, getDue, getStudyMd, getWeak, getValidation, getSessions } from '../api/client';
import type {
  HealthResponse,
  DueConceptItem,
  StudyMdResponse,
  WeakRepItem,
  StudyValidationReport,
  SessionSummaryItem,
} from '../api/types';
import StudyMdViewer from '../components/StudyMdViewer';

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [due, setDue] = useState<DueConceptItem[] | null>(null);
  const [dueError, setDueError] = useState<string | null>(null);

  const [weak, setWeak] = useState<WeakRepItem[] | null>(null);

  const [studyMd, setStudyMd] = useState<StudyMdResponse | null>(null);
  const [studyMdError, setStudyMdError] = useState<string | null>(null);

  const [validation, setValidation] = useState<StudyValidationReport | null>(null);

  const [recentSessions, setRecentSessions] = useState<SessionSummaryItem[] | null>(null);

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

    getValidation()
      .then(setValidation)
      .catch(() => setValidation(null));  // silent — validation badge optional

    getSessions()
      .then((sessions) => setRecentSessions(sessions.slice(0, 3)))
      .catch(() => setRecentSessions([]));  // silent
  }, []);

  // Compute primary CTA
  const ctaContent = (() => {
    if (validation && !validation.valid) {
      return {
        type: 'fix' as const,
        label: `Fix: STUDY.md has ${validation.error_count} error(s)`,
        note: 'Due and weak rep data may be unreliable when canonical state is invalid.',
      };
    }
    if (due && due.length > 0) {
      const first = due[0];
      const href = first.suggested_mode === 'weak_only' && first.target_representations.length > 0
        ? `/recall?concept=${first.concept_id}&target_reps=${first.target_representations.join(',')}`
        : `/recall?concept=${first.concept_id}`;
      return { type: 'due' as const, label: `Resume: ${due.length} concept(s) due for review`, href };
    }
    if (weak && weak.length > 0) {
      const first = weak[0];
      const href = `/recall?concept=${first.concept_id}&rep_type=${first.rep_type}`;
      return { type: 'weak' as const, label: `Strengthen: ${weak.length} weak representation(s)`, href };
    }
    if (due !== null && weak !== null) {
      return { type: 'done' as const, label: 'All representations current. Compile next concept →', href: '/concepts' };
    }
    return null;  // still loading
  })();

  return (
    <div>
      <h1>Dashboard</h1>

      {/* Primary CTA */}
      {ctaContent && (
        <div className="section">
          <div style={{
            background: ctaContent.type === 'fix' ? '#fff7ed' : ctaContent.type === 'done' ? '#f0fdf4' : '#eff6ff',
            border: `1px solid ${ctaContent.type === 'fix' ? '#fed7aa' : ctaContent.type === 'done' ? '#bbf7d0' : '#bfdbfe'}`,
            borderRadius: 8, padding: '14px 18px',
          }}>
            {ctaContent.type === 'fix' ? (
              <>
                <strong style={{ color: '#9a3412', fontSize: 15 }}>{ctaContent.label}</strong>
                <p style={{ marginTop: 4, fontSize: 13, color: '#7c2d12' }}>{ctaContent.note}</p>
              </>
            ) : (
              <Link to={ctaContent.href} style={{
                color: ctaContent.type === 'done' ? '#15803d' : '#1d4ed8',
                fontWeight: 600, fontSize: 15, textDecoration: 'none',
              }}>
                {ctaContent.label}
              </Link>
            )}
          </div>
        </div>
      )}

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

      {/* STUDY.md validation status */}
      <div className="section">
        <h2>STUDY.md State</h2>
        <div className="card">
          {validation === null ? (
            <span className="loading">Checking…</span>
          ) : validation.valid ? (
            <span className="badge badge-ok">✓ Valid</span>
          ) : (
            <span className="badge badge-overdue">
              ✗ {validation.error_count} error(s){validation.warning_count > 0 ? `, ${validation.warning_count} warning(s)` : ''}
            </span>
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

      {/* Recent Sessions */}
      <div className="section">
        <h2>Recent Sessions</h2>
        <div className="card">
          {recentSessions === null ? (
            <p className="loading">Loading…</p>
          ) : recentSessions.length === 0 ? (
            <p className="empty-state">No sessions yet.</p>
          ) : (
            <table className="table-simple">
              <thead>
                <tr>
                  <th>Concept</th>
                  <th>Started</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentSessions.map((s) => (
                  <tr key={s.session_id}>
                    <td>{s.concept_id}</td>
                    <td style={{ fontSize: 13, color: '#555' }}>{s.started_at.slice(0, 10)}</td>
                    <td>
                      <Link to={`/sessions/${s.session_id}`} className="session-link">View →</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* STUDY.md (collapsed) */}
      <div className="section">
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: 16, marginBottom: 4 }}>
            STUDY.md (raw)
          </summary>
          <div className="card" style={{ marginTop: 8 }}>
            {studyMdError ? (
              <p className="error-text">{studyMdError}</p>
            ) : studyMd === null ? (
              <p className="loading">Loading…</p>
            ) : (
              <StudyMdViewer content={studyMd.content} />
            )}
          </div>
        </details>
      </div>
    </div>
  );
}

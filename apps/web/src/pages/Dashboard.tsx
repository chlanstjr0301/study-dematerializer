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

const MASTERY_LABEL: Record<string, string> = {
  solid: '완전',
  partial: '부분',
  unknown: '미확인',
};

const DUE_LABEL: Record<string, string> = {
  overdue: '초과',
  due: '예정',
};

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
        label: `수정 필요: STUDY.md에 ${validation.error_count}개 오류`,
        note: '표준 상태가 유효하지 않으면 복습/취약 데이터가 부정확할 수 있습니다.',
      };
    }
    if (due && due.length > 0) {
      const first = due[0];
      const href = first.suggested_mode === 'weak_only' && first.target_representations.length > 0
        ? `/recall?concept=${first.concept_id}&target_reps=${first.target_representations.join(',')}`
        : `/recall?concept=${first.concept_id}`;
      return { type: 'due' as const, label: `복습: ${due.length}개 개념 복습 예정`, href };
    }
    if (weak && weak.length > 0) {
      const first = weak[0];
      const href = `/recall?concept=${first.concept_id}&rep_type=${first.rep_type}`;
      return { type: 'weak' as const, label: `강화: ${weak.length}개 취약 표현`, href };
    }
    if (due !== null && weak !== null) {
      return { type: 'done' as const, label: '모든 표현 최신. 다음 개념 컴파일 →', href: '/concepts' };
    }
    return null;  // still loading
  })();

  return (
    <div>
      <h1>대시보드</h1>

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
        <h2>API 상태</h2>
        <div className="card">
          {healthError ? (
            <span className="error-text">API 연결 불가: {healthError}</span>
          ) : health ? (
            <span className="badge badge-ok">API: {health.status}</span>
          ) : (
            <span className="loading">확인 중…</span>
          )}
        </div>
      </div>

      {/* STUDY.md validation status */}
      <div className="section">
        <h2>STUDY.md 상태</h2>
        <div className="card">
          {validation === null ? (
            <span className="loading">확인 중…</span>
          ) : validation.valid ? (
            <span className="badge badge-ok">✓ 정상</span>
          ) : (
            <span className="badge badge-overdue">
              ✗ {validation.error_count}개 오류{validation.warning_count > 0 ? `, ${validation.warning_count}개 경고` : ''}
            </span>
          )}
        </div>
      </div>

      {/* Due today */}
      <div className="section">
        <h2>복습 예정</h2>
        <div className="card">
          {dueError ? (
            <p className="error-text">{dueError}</p>
          ) : due === null ? (
            <p className="loading">불러오는 중…</p>
          ) : due.length === 0 ? (
            <p className="empty-state">복습 예정인 개념이 없습니다.</p>
          ) : (
            <table className="table-simple">
              <thead>
                <tr>
                  <th>개념</th>
                  <th>숙련도</th>
                  <th>취약</th>
                  <th>다음 복습</th>
                  <th>상태</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {due.map((item) => {
                  const href = item.suggested_mode === 'weak_only' && item.target_representations.length > 0
                    ? `/recall?concept=${item.concept_id}&target_reps=${item.target_representations.join(',')}`
                    : `/recall?concept=${item.concept_id}`;
                  const label = item.suggested_mode === 'weak_only' ? '취약 복습 →' : '전체 복습 →';
                  const masteryClass =
                    item.overall_mastery === 'solid' ? 'badge badge-ok' :
                    item.overall_mastery === 'partial' ? 'badge badge-partial' :
                    'badge badge-overdue';
                  return (
                    <tr key={item.concept_id}>
                      <td>{item.concept_id}</td>
                      <td><span className={masteryClass}>{MASTERY_LABEL[item.overall_mastery] ?? item.overall_mastery}</span></td>
                      <td>{item.weak_rep_count > 0 ? item.weak_rep_count : '—'}</td>
                      <td>{item.next_review ?? '—'}</td>
                      <td>
                        <span className={item.overdue ? 'badge badge-overdue' : 'badge'}>
                          {item.overdue ? DUE_LABEL['overdue'] : DUE_LABEL['due']}
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
          <h2>취약 표현</h2>
          <div className="card">
            <table className="table-simple">
              <thead>
                <tr>
                  <th>개념</th>
                  <th>유형</th>
                  <th>숙련도</th>
                  <th>최근 복습</th>
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
                        {MASTERY_LABEL[item.mastery] ?? item.mastery}
                      </span>
                    </td>
                    <td>{item.last_reviewed ?? '—'}</td>
                    <td>
                      <Link
                        to={`/recall?concept=${item.concept_id}&rep_type=${item.rep_type}`}
                        className="session-link"
                      >
                        강화 →
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
        <h2>최근 세션</h2>
        <div className="card">
          {recentSessions === null ? (
            <p className="loading">불러오는 중…</p>
          ) : recentSessions.length === 0 ? (
            <p className="empty-state">아직 세션이 없습니다.</p>
          ) : (
            <table className="table-simple">
              <thead>
                <tr>
                  <th>개념</th>
                  <th>시작일</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentSessions.map((s) => (
                  <tr key={s.session_id}>
                    <td>{s.concept_id}</td>
                    <td style={{ fontSize: 13, color: '#555' }}>{s.started_at.slice(0, 10)}</td>
                    <td>
                      <Link to={`/sessions/${s.session_id}`} className="session-link">보기 →</Link>
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
            STUDY.md (원본)
          </summary>
          <div className="card" style={{ marginTop: 8 }}>
            {studyMdError ? (
              <p className="error-text">{studyMdError}</p>
            ) : studyMd === null ? (
              <p className="loading">불러오는 중…</p>
            ) : (
              <StudyMdViewer content={studyMd.content} />
            )}
          </div>
        </details>
      </div>
    </div>
  );
}

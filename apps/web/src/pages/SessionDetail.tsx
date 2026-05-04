import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getSession,
  getSessionSummary,
  getVisualization,
} from '../api/client';
import type {
  SessionResponse,
  SummaryResponse,
  MasteryMapData,
  RecallFeedbackData,
  ReviewQueueData,
} from '../api/types';
import StudyMdViewer from '../components/StudyMdViewer';
import MasteryMap from '../components/MasteryMap';
import RecallFeedback from '../components/RecallFeedback';
import ReviewQueue from '../components/ReviewQueue';
import MermaidPreview from '../components/MermaidPreview';

type ArtifactState<T> = { data: T | null; error: string | null };

function initArtifact<T>(): ArtifactState<T> {
  return { data: null, error: null };
}

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  const [masteryMap, setMasteryMap] = useState<ArtifactState<MasteryMapData>>(initArtifact());
  const [recallFeedback, setRecallFeedback] = useState<ArtifactState<RecallFeedbackData>>(initArtifact());
  const [reviewQueue, setReviewQueue] = useState<ArtifactState<ReviewQueueData>>(initArtifact());
  const [masteryMapMmd, setMasteryMapMmd] = useState<ArtifactState<string>>(initArtifact());
  const [sessionFlowMmd, setSessionFlowMmd] = useState<ArtifactState<string>>(initArtifact());

  useEffect(() => {
    if (!sessionId) return;

    getSession(sessionId)
      .then(setSession)
      .catch((e: unknown) => setSessionError(String(e)));

    getSessionSummary(sessionId)
      .then(setSummary)
      .catch(() => { /* summary is optional */ });

    getVisualization(sessionId, 'mastery_map')
      .then((d) => setMasteryMap({ data: d as MasteryMapData, error: null }))
      .catch((e: unknown) => setMasteryMap({ data: null, error: String(e) }));

    getVisualization(sessionId, 'recall_feedback')
      .then((d) => setRecallFeedback({ data: d as RecallFeedbackData, error: null }))
      .catch((e: unknown) => setRecallFeedback({ data: null, error: String(e) }));

    getVisualization(sessionId, 'review_queue')
      .then((d) => setReviewQueue({ data: d as ReviewQueueData, error: null }))
      .catch((e: unknown) => setReviewQueue({ data: null, error: String(e) }));

    getVisualization(sessionId, 'mastery_map_mmd')
      .then((d) => setMasteryMapMmd({ data: d as string, error: null }))
      .catch((e: unknown) => setMasteryMapMmd({ data: null, error: String(e) }));

    getVisualization(sessionId, 'session_flow_mmd')
      .then((d) => setSessionFlowMmd({ data: d as string, error: null }))
      .catch((e: unknown) => setSessionFlowMmd({ data: null, error: String(e) }));
  }, [sessionId]);

  if (sessionError) {
    return (
      <div>
        <p className="error-text">{sessionError}</p>
        <Link to="/sessions">← Back to sessions</Link>
      </div>
    );
  }

  if (!session) {
    return <p className="loading">Loading session…</p>;
  }

  const s = session.session;

  return (
    <div>
      <p style={{ marginBottom: 12 }}>
        <Link to="/sessions">← Sessions</Link>
      </p>
      <h1>Session Detail</h1>

      {/* Metadata */}
      <div className="section">
        <h2>Metadata</h2>
        <div className="card">
          <table className="table-simple">
            <tbody>
              <tr><th>Session ID</th><td style={{ fontFamily: 'monospace', fontSize: 13 }}>{sessionId}</td></tr>
              <tr><th>Concept</th><td>{String(s['concept_id'] ?? s['concept_ids'] ?? '—')}</td></tr>
              <tr><th>Started</th><td>{String(s['started_at'] ?? '—')}</td></tr>
              <tr><th>Ended</th><td>{String(s['ended_at'] ?? '—')}</td></tr>
              <tr><th>Grader</th><td>{String(s['grader_type'] ?? '—')}</td></tr>
              <tr><th>Attempts</th><td>{session.attempts.length}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="section">
          <h2>Session Summary</h2>
          <div className="card">
            <StudyMdViewer content={summary.content} />
          </div>
        </div>
      )}

      {/* Mastery map */}
      <div className="section">
        <h2>Mastery Map</h2>
        <div className="card">
          {masteryMap.data ? (
            <MasteryMap data={masteryMap.data} />
          ) : (
            <p className="artifact-missing">
              {masteryMap.error ? 'Not available.' : 'Loading…'}
            </p>
          )}
        </div>
      </div>

      {/* Recall feedback */}
      <div className="section">
        <h2>Recall Feedback</h2>
        <div className="card">
          {recallFeedback.data ? (
            <RecallFeedback data={recallFeedback.data} />
          ) : (
            <p className="artifact-missing">
              {recallFeedback.error ? 'Not available.' : 'Loading…'}
            </p>
          )}
        </div>
      </div>

      {/* Review queue */}
      <div className="section">
        <h2>Review Queue</h2>
        <div className="card">
          {reviewQueue.data ? (
            <ReviewQueue data={reviewQueue.data} />
          ) : (
            <p className="artifact-missing">
              {reviewQueue.error ? 'Not available.' : 'Loading…'}
            </p>
          )}
        </div>
      </div>

      {/* Mermaid previews */}
      <div className="section">
        <h2>Diagrams (text preview)</h2>
        <div className="card">
          {masteryMapMmd.data ? (
            <MermaidPreview text={masteryMapMmd.data} label="Mastery Map (.mmd)" />
          ) : (
            <p className="artifact-missing">mastery_map.mmd — not available.</p>
          )}

          <div style={{ marginTop: 20 }}>
            {sessionFlowMmd.data ? (
              <MermaidPreview text={sessionFlowMmd.data} label="Session Flow (.mmd)" />
            ) : (
              <p className="artifact-missing">session_flow.mmd — not available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

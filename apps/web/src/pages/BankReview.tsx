import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getGeneratedBank, reviewBank, exportAccepted } from '../api/client';
import type {
  GeneratedQuestionItem,
  ReviewAction,
  ReviewBankResponse,
  ExportAcceptedResponse,
} from '../api/types';

type ActionType = 'accept' | 'reject' | 'edit' | 'skip';

export default function BankReview() {
  const { conceptId = '' } = useParams<{ conceptId: string }>();

  const [questions, setQuestions]       = useState<GeneratedQuestionItem[] | null>(null);
  const [questionsError, setQuestionsError] = useState<string | null>(null);

  const [actions, setActions] = useState<Record<string, ActionType>>({});
  const [edits,   setEdits]   = useState<Record<string, { q: string; a: string }>>({});

  const [submitting, setSubmitting]     = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewBankResponse | null>(null);
  const [reviewError, setReviewError]   = useState<string | null>(null);

  const [exporting, setExporting]       = useState(false);
  const [exportResult, setExportResult] = useState<ExportAcceptedResponse | null>(null);
  const [exportError, setExportError]   = useState<string | null>(null);

  useEffect(() => {
    if (!conceptId) return;
    getGeneratedBank(conceptId)
      .then(setQuestions)
      .catch((e: unknown) => setQuestionsError(String(e)));
  }, [conceptId]);

  function setAction(qid: string, action: ActionType) {
    setActions(prev => ({ ...prev, [qid]: action }));
    if (action === 'edit' && questions) {
      const q = questions.find(x => x.question_id === qid);
      if (q && !edits[qid]) {
        setEdits(prev => ({ ...prev, [qid]: { q: q.question, a: q.expected_answer } }));
      }
    }
  }

  function setEditField(qid: string, field: 'q' | 'a', value: string) {
    setEdits(prev => ({ ...prev, [qid]: { ...prev[qid], [field]: value } }));
  }

  async function handleSubmit() {
    if (!questions) return;
    setSubmitting(true);
    setReviewError(null);
    try {
      const actionList: ReviewAction[] = Object.entries(actions).map(([qid, action]) => {
        const item: ReviewAction = { question_id: qid, action };
        if (action === 'edit' && edits[qid]) {
          item.updated_question        = edits[qid].q;
          item.updated_expected_answer = edits[qid].a;
        }
        return item;
      });
      const result = await reviewBank(conceptId, { actions: actionList });
      setReviewResult(result);
    } catch (e: unknown) {
      setReviewError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    setExportError(null);
    try {
      const result = await exportAccepted(conceptId);
      setExportResult(result);
    } catch (e: unknown) {
      setExportError(String(e));
    } finally {
      setExporting(false);
    }
  }

  if (questionsError) {
    return (
      <div>
        <h1>Review Bank — {conceptId}</h1>
        <div className="error-box">{questionsError}</div>
      </div>
    );
  }

  if (!questions) {
    return (
      <div>
        <h1>Review Bank — {conceptId}</h1>
        <p>Loading…</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div>
        <h1>Review Bank — {conceptId}</h1>
        <p className="empty-state">No generated questions found. Build a bank first.</p>
      </div>
    );
  }

  const actionCount = Object.keys(actions).length;

  return (
    <div>
      <h1>Review Bank — {conceptId}</h1>
      <p style={{ marginBottom: 16, color: '#555', fontSize: 14 }}>
        {questions.length} questions &nbsp;|&nbsp; {actionCount} reviewed
      </p>

      {questions.map(q => {
        const currentAction = actions[q.question_id];
        const edit = edits[q.question_id];
        return (
          <div
            key={q.question_id}
            className={`review-card${currentAction ? ` action-${currentAction}` : ''}`}
          >
            <p style={{ fontWeight: 600 }}>{q.question}</p>
            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {q.question_type} &middot; {q.difficulty}
            </p>
            <p style={{ fontSize: 13, color: '#555', marginTop: 6 }}>
              <em>Expected:</em> {q.expected_answer.slice(0, 120)}{q.expected_answer.length > 120 ? '…' : ''}
            </p>

            <div className="review-actions">
              {(['accept', 'reject', 'edit', 'skip'] as ActionType[]).map(a => (
                <button
                  key={a}
                  className={`action-btn action-btn-${a}${currentAction === a ? ' selected' : ''}`}
                  onClick={() => setAction(q.question_id, a)}
                >
                  {a.charAt(0).toUpperCase() + a.slice(1)}
                </button>
              ))}
            </div>

            {currentAction === 'edit' && (
              <div className="edit-fields">
                <textarea
                  value={edit?.q ?? q.question}
                  onChange={e => setEditField(q.question_id, 'q', e.target.value)}
                  placeholder="Updated question text"
                />
                <textarea
                  value={edit?.a ?? q.expected_answer}
                  onChange={e => setEditField(q.question_id, 'a', e.target.value)}
                  placeholder="Updated expected answer"
                />
              </div>
            )}
          </div>
        );
      })}

      <div style={{ marginTop: 8 }}>
        <button
          onClick={handleSubmit}
          disabled={submitting || actionCount === 0}
          className="btn-primary"
        >
          {submitting ? 'Submitting…' : 'Submit Review'}
        </button>
      </div>

      {reviewError && <div className="error-box">{reviewError}</div>}

      {reviewResult && (
        <div className="review-summary">
          <h3>Review Complete</h3>
          <dl>
            <dt>Total</dt>    <dd>{reviewResult.total}</dd>
            <dt>Accepted</dt> <dd>{reviewResult.accepted}</dd>
            <dt>Rejected</dt> <dd>{reviewResult.rejected}</dd>
            <dt>Edited</dt>   <dd>{reviewResult.edited}</dd>
            <dt>Skipped</dt>  <dd>{reviewResult.skipped}</dd>
          </dl>

          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-primary"
          >
            {exporting ? 'Exporting…' : 'Export Accepted'}
          </button>

          {exportError && <div className="error-box">{exportError}</div>}

          {exportResult && (
            <div style={{ marginTop: 12 }}>
              <p style={{ marginBottom: 8, fontSize: 14 }}>
                Exported <strong>{exportResult.accepted_count}</strong> accepted question{exportResult.accepted_count !== 1 ? 's' : ''}.
              </p>
              <Link to="/recall" className="btn-primary">
                Go to Recall &rarr;
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

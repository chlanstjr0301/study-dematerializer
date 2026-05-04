import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getBanks, getBank, runSession, getVisualization } from '../api/client';
import type {
  BankSummaryItem,
  QuestionItem,
  RunSessionRequest,
  RunSessionResponse,
  MasteryMapData,
  RecallFeedbackData,
} from '../api/types';

export default function RecallSession() {
  const [searchParams] = useSearchParams();

  const [banks, setBanks] = useState<BankSummaryItem[] | null>(null);
  const [banksError, setBanksError] = useState<string | null>(null);

  const [selected, setSelected] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[] | null>(null);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [questionsError, setQuestionsError] = useState<string | null>(null);

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<RunSessionResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [masteryResult, setMasteryResult] = useState<MasteryMapData | null>(null);
  const [feedbackResult, setFeedbackResult] = useState<RecallFeedbackData | null>(null);

  useEffect(() => {
    getBanks()
      .then(setBanks)
      .catch((e: unknown) => setBanksError(String(e)));
  }, []);

  // Auto-select from ?concept= param after banks load
  useEffect(() => {
    const param = searchParams.get('concept');
    if (param && !selected && banks && banks.some(b => b.concept_id === param)) {
      selectConcept(param);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [banks]);

  function selectConcept(conceptId: string) {
    setSelected(conceptId);
    setQuestions(null);
    setQuestionsError(null);
    setQuestionsLoading(true);
    setResult(null);
    setSubmitError(null);
    setAnswers({});
    setMasteryResult(null);
    setFeedbackResult(null);
    getBank(conceptId)
      .then((qs) => {
        setQuestions(qs);
        const init: Record<string, string> = {};
        for (const q of qs) init[q.id] = '';
        setAnswers(init);
        setQuestionsLoading(false);
      })
      .catch((e: unknown) => {
        setQuestionsError(String(e));
        setQuestionsLoading(false);
      });
  }

  function handleAnswerChange(questionId: string, value: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }

  function handleSubmit() {
    if (!selected || !questions?.length) return;
    setSubmitting(true);
    setSubmitError(null);
    setResult(null);
    setMasteryResult(null);
    setFeedbackResult(null);

    const payload: RunSessionRequest = {
      concept_id: selected,
      questions_path: `${selected}/questions.accepted.json`,
      grader: 'mock',
      answers: questions.map((q) => ({
        question_id: q.id,
        learner_response: answers[q.id] ?? '',
      })),
    };

    runSession(payload)
      .then((res) => {
        setResult(res);
        setSubmitting(false);
        Promise.all([
          getVisualization(res.session_id, 'mastery_map'),
          getVisualization(res.session_id, 'recall_feedback'),
        ]).then(([map, fb]) => {
          setMasteryResult(map as MasteryMapData);
          setFeedbackResult(fb as RecallFeedbackData);
        }).catch(() => { /* silent — summary_md still shown */ });
      })
      .catch((e: unknown) => {
        setSubmitError(String(e));
        setSubmitting(false);
      });
  }

  const submitDisabled = !selected || !questions?.length || submitting;

  return (
    <div>
      <h1>Recall Session</h1>

      {/* Bank selector */}
      <div className="section">
        <h2>Select a Question Bank</h2>
        {banksError ? (
          <p className="error-text">{banksError}</p>
        ) : banks === null ? (
          <p className="loading">Loading banks…</p>
        ) : banks.length === 0 ? (
          <p className="empty-state">No accepted question banks found.</p>
        ) : (
          <div className="concept-list">
            {banks.map((b) => (
              <button
                key={b.concept_id}
                className={`concept-btn${selected === b.concept_id ? ' active' : ''}`}
                onClick={() => selectConcept(b.concept_id)}
                disabled={submitting}
              >
                {b.concept_id} ({b.question_count})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Questions */}
      {selected && (
        <div className="section">
          <h2>{selected}</h2>
          {questionsLoading ? (
            <p className="loading">Loading questions…</p>
          ) : questionsError ? (
            <p className="error-text">{questionsError}</p>
          ) : questions === null || questions.length === 0 ? (
            <p className="empty-state">No accepted questions found.</p>
          ) : (
            <>
              {questions.map((q) => (
                <div key={q.id} className="question-card">
                  <h3>{q.question}</h3>
                  <p className="question-meta">
                    {q.question_type}
                    {q.difficulty ? ` · ${q.difficulty}` : ''}
                  </p>
                  {q.evidence && typeof q.evidence['source_text'] === 'string' && (
                    <div className="evidence-preview">
                      {(q.evidence['source_text'] as string).slice(0, 200)}
                    </div>
                  )}
                  <textarea
                    className="recall-textarea"
                    placeholder="Write your answer here…"
                    value={answers[q.id] ?? ''}
                    onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                    disabled={submitting}
                  />
                </div>
              ))}

              <button
                className="submit-btn"
                onClick={handleSubmit}
                disabled={submitDisabled}
              >
                {submitting ? 'Submitting…' : 'Submit (mock grader)'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Error */}
      {submitError && (
        <div className="error-box">
          <strong>Submission failed:</strong>
          {'\n'}{submitError}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="success-box">
          <h2>Session Created</h2>
          <table className="table-simple" style={{ marginBottom: 16 }}>
            <tbody>
              <tr>
                <th>Session ID</th>
                <td style={{ fontFamily: 'monospace', fontSize: 13 }}>{result.session_id}</td>
              </tr>
              <tr>
                <th>Attempts graded</th>
                <td>{result.attempt_count}</td>
              </tr>
            </tbody>
          </table>

          {result.summary_md && (
            <details style={{ marginBottom: 16 }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: 8 }}>
                Session summary
              </summary>
              <pre className="pre-block" style={{ marginTop: 8 }}>{result.summary_md}</pre>
            </details>
          )}

          {/* Mastery changes */}
          {masteryResult && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 8 }}>Mastery Changes</h3>
              <table className="table-simple">
                <thead>
                  <tr>
                    <th>Representation</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {masteryResult.representations.map((r, i) => (
                    <tr key={i}>
                      <td>{r.type}</td>
                      <td style={{ color: r.before === 'solid' ? '#15803d' : r.before === 'partial' ? '#92400e' : '#b91c1c' }}>
                        {r.before}
                      </td>
                      <td style={{
                        color: r.after === 'solid' ? '#15803d' : r.after === 'partial' ? '#92400e' : '#b91c1c',
                        fontWeight: 600,
                      }}>
                        {r.after}
                      </td>
                      <td>{(r.accuracy_score * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Weak questions */}
          {feedbackResult && (() => {
            const weak = feedbackResult.filter(
              f => f.accuracy_score < 0.5 || f.needs_human_review
            );
            return (
              <div style={{ marginBottom: 16 }}>
                <h3 style={{ marginBottom: 8 }}>Weak Questions</h3>
                {weak.length === 0 ? (
                  <p style={{ fontSize: 14, color: '#15803d' }}>No weak questions — great work!</p>
                ) : (
                  weak.map((f, i) => (
                    <div key={i} style={{
                      background: '#fafafa', border: '1px solid #e5e7eb',
                      borderRadius: 6, padding: '10px 14px', marginBottom: 8, fontSize: 13,
                    }}>
                      {f.needs_human_review && (
                        <span style={{
                          background: '#fef3c7', color: '#92400e', fontSize: 11,
                          padding: '1px 6px', borderRadius: 4, marginRight: 6, fontWeight: 600,
                        }}>
                          ⚠ Review
                        </span>
                      )}
                      <span style={{ fontFamily: 'monospace', color: '#555', fontSize: 11 }}>
                        {f.question_id}
                      </span>
                      {f.feedback && (
                        <p style={{ marginTop: 6 }}>{f.feedback}</p>
                      )}
                      {f.missing_elements.length > 0 && (
                        <ul style={{ paddingLeft: 16, marginTop: 4 }}>
                          {f.missing_elements.map((el, j) => <li key={j}>{el}</li>)}
                        </ul>
                      )}
                    </div>
                  ))
                )}
              </div>
            );
          })()}

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Link className="session-link" to={`/sessions/${result.session_id}`}>
              View Session Detail →
            </Link>
            <Link className="session-link" to="/">
              Back to Dashboard →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

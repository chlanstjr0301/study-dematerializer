import { useEffect, useState } from 'react';
import { getBanks, getBank } from '../api/client';
import type { BankSummaryItem, QuestionItem } from '../api/types';

export default function BankBrowser() {
  const [banks, setBanks] = useState<BankSummaryItem[] | null>(null);
  const [banksError, setBanksError] = useState<string | null>(null);

  const [selected, setSelected] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[] | null>(null);
  const [questionsError, setQuestionsError] = useState<string | null>(null);
  const [questionsLoading, setQuestionsLoading] = useState(false);

  useEffect(() => {
    getBanks()
      .then(setBanks)
      .catch((e: unknown) => setBanksError(String(e)));
  }, []);

  function selectConcept(conceptId: string) {
    setSelected(conceptId);
    setQuestions(null);
    setQuestionsError(null);
    setQuestionsLoading(true);
    getBank(conceptId)
      .then((qs) => { setQuestions(qs); setQuestionsLoading(false); })
      .catch((e: unknown) => { setQuestionsError(String(e)); setQuestionsLoading(false); });
  }

  return (
    <div>
      <h1>Recall Prompt Library</h1>

      {/* Concept selector */}
      <div className="section">
        {banksError ? (
          <p className="error-text">{banksError}</p>
        ) : banks === null ? (
          <p className="loading">Loading banks…</p>
        ) : banks.length === 0 ? (
          <p className="empty-state">No recall prompt banks found.</p>
        ) : (
          <div className="concept-list">
            {banks.map((b) => (
              <button
                key={b.concept_id}
                className={`concept-btn${selected === b.concept_id ? ' active' : ''}`}
                onClick={() => selectConcept(b.concept_id)}
              >
                {b.concept_id} ({b.question_count})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Question list */}
      {selected && (
        <div className="section">
          <h2>{selected}</h2>
          <div className="card">
            {questionsLoading ? (
              <p className="loading">Loading prompts…</p>
            ) : questionsError ? (
              <p className="error-text">{questionsError}</p>
            ) : questions === null || questions.length === 0 ? (
              <p className="empty-state">No recall prompts found.</p>
            ) : (
              <table className="table-simple">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Recall Prompt</th>
                    <th>Type</th>
                    <th>Difficulty</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((q) => (
                    <tr key={q.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{q.id}</td>
                      <td>
                        <div style={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {q.question}
                        </div>
                        {q.evidence && typeof q.evidence['source_text'] === 'string' && (
                          <div style={{ fontSize: 12, color: '#888', marginTop: 4, maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {q.evidence['source_text'].slice(0, 120)}
                          </div>
                        )}
                      </td>
                      <td>{q.question_type}</td>
                      <td>{q.difficulty ?? '—'}</td>
                      <td>
                        <span className={`badge badge-${q.status}`}>{q.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

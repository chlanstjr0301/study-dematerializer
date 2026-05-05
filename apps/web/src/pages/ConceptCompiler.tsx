import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getConcepts, getSources, compileConcept } from '../api/client';
import type { ConceptItem, SourceItem, CompileConceptResponse } from '../api/types';

export default function ConceptCompiler() {
  const [concepts, setConcepts] = useState<ConceptItem[] | null>(null);
  const [sources, setSources]   = useState<SourceItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedConcept, setSelectedConcept] = useState('');
  const [selectedSource, setSelectedSource]   = useState('');

  const [compiling, setCompiling] = useState(false);
  const [result, setResult]       = useState<CompileConceptResponse | null>(null);
  const [compileError, setCompileError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getConcepts(), getSources()])
      .then(([c, s]) => {
        // Only show the three seed concepts (not prerequisite stubs)
        const seeds = ['compactness', 'connectedness', 'uniform_continuity'];
        setConcepts(c.filter(x => seeds.includes(x.concept_id)));
        setSources(s);
      })
      .catch((e: unknown) => setLoadError(String(e)));
  }, []);

  async function handleCompile() {
    if (!selectedConcept || !selectedSource) return;
    setCompiling(true);
    setResult(null);
    setCompileError(null);
    try {
      const source = sources?.find(s => s.relative_path === selectedSource);
      const documentId = source?.source_id ?? selectedSource.replace(/[^A-Za-z0-9_-]/g, '_');
      const res = await compileConcept(selectedConcept, {
        source_relative_path: selectedSource,
        document_id: documentId,
      });
      setResult(res);
    } catch (e: unknown) {
      setCompileError(String(e));
    } finally {
      setCompiling(false);
    }
  }

  if (loadError) {
    return (
      <main>
        <h1>Concept Compiler</h1>
        <p className="error-msg">Failed to load: {loadError}</p>
      </main>
    );
  }

  if (!concepts || !sources) {
    return (
      <main>
        <h1>Concept Compiler</h1>
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main>
      <h1>Concept Compiler</h1>
      <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 16, lineHeight: 1.5 }}>
        The Concept Compiler runs the full 8-stage Gonghaebun pipeline:{' '}
        prerequisite graph → 5 representations → misconception check →
        self-explanation → recall prompts → STUDY.md update.
      </p>

      {/* Concept selection */}
      <section className="compiler-section">
        <h2>1. Select Concept</h2>
        <div className="concept-pills">
          {concepts.map(c => (
            <button
              key={c.concept_id}
              className={`pill${selectedConcept === c.concept_id ? ' pill--active' : ''}`}
              onClick={() => setSelectedConcept(c.concept_id)}
            >
              {c.canonical_name}
            </button>
          ))}
        </div>
        {selectedConcept && (
          <p className="prereqs-note">
            Prerequisites:{' '}
            {concepts.find(c => c.concept_id === selectedConcept)?.prerequisites.join(', ') || '—'}
          </p>
        )}
      </section>

      {/* Source selection */}
      <section className="compiler-section">
        <h2>2. Select Source</h2>
        {sources.length === 0 ? (
          <p className="empty-state">No sources uploaded. Upload a .md file via the Sources page first.</p>
        ) : (
          <select
            value={selectedSource}
            onChange={e => setSelectedSource(e.target.value)}
            className="source-select"
          >
            <option value="">— choose a source —</option>
            {sources.map(s => (
              <option key={s.source_id} value={s.relative_path}>
                {s.filename}
              </option>
            ))}
          </select>
        )}
      </section>

      {/* Compile button */}
      <section className="compiler-section">
        <button
          className="compile-btn"
          onClick={handleCompile}
          disabled={!selectedConcept || !selectedSource || compiling}
        >
          {compiling ? 'Compiling…' : 'Compile'}
        </button>
      </section>

      {/* Error */}
      {compileError && (
        <p className="error-msg">Error: {compileError}</p>
      )}

      {/* Result */}
      {result && (
        <section className="compile-result">
          <h2>Compilation Complete</h2>
          <table>
            <tbody>
              <tr><th>Concept</th><td>{result.concept_id}</td></tr>
              <tr><th>Representations</th><td>{result.representation_count}</td></tr>
              <tr><th>Prerequisites</th><td>{result.prerequisite_count}</td></tr>
              <tr><th>Misconceptions</th><td>{result.misconception_count}</td></tr>
              <tr><th>Recall prompts generated</th><td>{result.question_count}</td></tr>
              <tr><th>Session ID</th><td><code>{result.session_id}</code></td></tr>
            </tbody>
          </table>
          <div className="result-links">
            <Link to={`/review/${result.concept_id}`} style={{
              display: 'inline-block', padding: '8px 16px',
              background: '#1d4ed8', color: '#fff', borderRadius: 6,
              fontWeight: 600, fontSize: 14, textDecoration: 'none',
            }}>
              Review Recall Prompts →
            </Link>
            <Link to={`/sessions/${result.session_id}`} className="session-link">
              View Session Artifacts →
            </Link>
          </div>
        </section>
      )}
    </main>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getProjectStatus,
  bootstrapProject,
  uploadSource,
  buildBank,
} from '../api/client';
import type {
  ProjectStatus,
  BootstrapResponse,
  UploadSourceResponse,
  BuildBankResponse,
} from '../api/types';

export default function SourceUpload() {
  const [status, setStatus]               = useState<ProjectStatus | null>(null);
  const [statusError, setStatusError]     = useState<string | null>(null);
  const [bootstrapResult, setBootstrapResult] = useState<BootstrapResponse | null>(null);
  const [bootstrapping, setBootstrapping] = useState(false);

  const [conceptId, setConceptId]   = useState('');
  const [documentId, setDocumentId] = useState('');
  const [file, setFile]             = useState<File | null>(null);
  const [uploading, setUploading]   = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadSourceResponse | null>(null);
  const [uploadError, setUploadError]   = useState<string | null>(null);

  const [building, setBuilding]         = useState(false);
  const [buildResult, setBuildResult]   = useState<BuildBankResponse | null>(null);
  const [buildError, setBuildError]     = useState<string | null>(null);

  useEffect(() => {
    getProjectStatus()
      .then(setStatus)
      .catch((e: unknown) => setStatusError(String(e)));
  }, []);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f && !documentId) {
      const stem = f.name.replace(/\.[^.]+$/, '');
      setDocumentId(stem);
    }
  }

  async function handleBootstrap() {
    setBootstrapping(true);
    try {
      const r = await bootstrapProject();
      setBootstrapResult(r);
      const s = await getProjectStatus();
      setStatus(s);
    } catch (e: unknown) {
      setStatusError(String(e));
    } finally {
      setBootstrapping(false);
    }
  }

  async function handleUpload() {
    if (!file || !conceptId) return;
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    setBuildResult(null);
    setBuildError(null);
    try {
      const r = await uploadSource(file, conceptId, documentId || undefined);
      setUploadResult(r);
      if (!documentId) setDocumentId(r.document_id);
    } catch (e: unknown) {
      setUploadError(String(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleBuild() {
    if (!uploadResult) return;
    setBuilding(true);
    setBuildError(null);
    try {
      const r = await buildBank({
        concept_id: conceptId,
        source_relative_path: uploadResult.source_path,
        document_id: documentId || uploadResult.document_id,
      });
      setBuildResult(r);
    } catch (e: unknown) {
      setBuildError(String(e));
    } finally {
      setBuilding(false);
    }
  }

  function badge(exists: boolean) {
    return <span className={`status-badge ${exists ? 'ok' : 'miss'}`}>{exists ? 'OK' : 'Missing'}</span>;
  }

  return (
    <div>
      <h1>Sources</h1>

      {/* Section 1: Project Status */}
      <section className="card" style={{ marginBottom: 24 }}>
        <h2>Project Status</h2>
        {statusError && <p className="error-box">{statusError}</p>}
        {status && (
          <dl style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '4px 16px', fontSize: 14, margin: '12px 0' }}>
            <dt>STUDY.md</dt>   <dd>{badge(status.study_md_exists)}</dd>
            <dt>banks/</dt>     <dd>{badge(status.banks_dir_exists)}</dd>
            <dt>runs/</dt>      <dd>{badge(status.runs_dir_exists)}</dd>
            <dt>sources/</dt>   <dd>{badge(status.sources_dir_exists)}</dd>
          </dl>
        )}
        <button onClick={handleBootstrap} disabled={bootstrapping} className="btn-primary">
          {bootstrapping ? 'Bootstrapping…' : 'Bootstrap Project'}
        </button>
        {bootstrapResult && (
          <p style={{ marginTop: 8, fontSize: 13, color: '#555' }}>
            Created: {bootstrapResult.created.join(', ') || 'nothing'} &nbsp;|&nbsp;
            Skipped: {bootstrapResult.skipped.join(', ') || 'nothing'}
          </p>
        )}
      </section>

      {/* Section 2: Upload Source */}
      <section className="card" style={{ marginBottom: 24 }}>
        <h2>Upload Source</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
          <label>
            Concept ID <span style={{ color: '#e55' }}>*</span>
            <input
              type="text"
              value={conceptId}
              onChange={e => setConceptId(e.target.value)}
              placeholder="e.g. compactness"
              style={{ display: 'block', marginTop: 4, width: '100%', maxWidth: 320, padding: '6px 10px', border: '1px solid #ccc', borderRadius: 6 }}
            />
          </label>
          <label>
            Document ID <span style={{ fontSize: 12, color: '#888' }}>(optional — auto-fills from filename)</span>
            <input
              type="text"
              value={documentId}
              onChange={e => setDocumentId(e.target.value)}
              placeholder="e.g. rudin_ch2"
              style={{ display: 'block', marginTop: 4, width: '100%', maxWidth: 320, padding: '6px 10px', border: '1px solid #ccc', borderRadius: 6 }}
            />
          </label>
          <label>
            File <span style={{ fontSize: 12, color: '#888' }}>(.md or .txt, max 2 MB)</span>
            <input
              type="file"
              accept=".md,.txt"
              onChange={handleFileChange}
              style={{ display: 'block', marginTop: 4 }}
            />
          </label>
          <div>
            <button
              onClick={handleUpload}
              disabled={uploading || !file || !conceptId}
              className="btn-primary"
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </div>
        {uploadError && <div className="error-box">{uploadError}</div>}
        {uploadResult && (
          <div style={{ marginTop: 12, padding: '12px 16px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #86efac', fontSize: 14 }}>
            Uploaded: <strong>{uploadResult.filename}</strong> ({uploadResult.size_bytes} bytes)<br />
            Path: <code>{uploadResult.source_path}</code><br />
            Document ID: <code>{uploadResult.document_id}</code>
          </div>
        )}
      </section>

      {/* Section 3: Build Bank (visible after upload) */}
      {uploadResult && (
        <section className="card">
          <h2>Build Bank</h2>
          <p style={{ marginBottom: 12, fontSize: 14, color: '#555' }}>
            Concept: <strong>{conceptId}</strong> &nbsp;|&nbsp; Document: <strong>{documentId || uploadResult.document_id}</strong>
          </p>
          <button onClick={handleBuild} disabled={building} className="btn-primary">
            {building ? 'Building…' : 'Build Bank'}
          </button>
          {buildError && <div className="error-box">{buildError}</div>}
          {buildResult && (
            <div style={{ marginTop: 16 }}>
              <p style={{ marginBottom: 8, fontSize: 14 }}>
                Blocks: <strong>{buildResult.block_count}</strong> &nbsp;|&nbsp;
                Questions: <strong>{buildResult.question_count}</strong>
              </p>
              <Link to={`/review/${buildResult.concept_id}`} className="btn-primary">
                Review Questions &rarr;
              </Link>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

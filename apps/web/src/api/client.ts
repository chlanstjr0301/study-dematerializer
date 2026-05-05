import type {
  HealthResponse,
  DueConceptItem,
  StudyMdResponse,
  BankSummaryItem,
  QuestionItem,
  SessionSummaryItem,
  SessionResponse,
  SummaryResponse,
  RunSessionRequest,
  RunSessionResponse,
  ProjectStatus,
  BootstrapResponse,
  SourceItem,
  UploadSourceResponse,
  BuildBankRequest,
  BuildBankResponse,
  GeneratedQuestionItem,
  ReviewBankRequest,
  ReviewBankResponse,
  ExportAcceptedResponse,
  ConceptItem,
  CompileConceptRequest,
  CompileConceptResponse,
  WeakRepItem,
  StudyValidationReport,
  AnalyzeRequest,
  AnalyzeResponse,
} from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function getText(path: string): Promise<string> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.text();
}

export const getHealth         = (): Promise<HealthResponse>         => get('/health');
export const getDue            = (): Promise<DueConceptItem[]>       => get('/due');
export const getStudyMd        = (): Promise<StudyMdResponse>        => get('/study-md');
export const getBanks          = (): Promise<BankSummaryItem[]>      => get('/bank');
export const getBank           = (id: string): Promise<QuestionItem[]> => get(`/bank/${id}`);
export const getSessions       = (): Promise<SessionSummaryItem[]>   => get('/sessions');
export const getSession        = (id: string): Promise<SessionResponse> => get(`/sessions/${id}`);
export const getSessionSummary = (id: string): Promise<SummaryResponse> =>
  get(`/sessions/${id}/summary`);

export const getVisualization = (id: string, artifact: string): Promise<unknown> => {
  const path = `/sessions/${id}/visualization/${artifact}`;
  return artifact.endsWith('_mmd') ? getText(path) : get(path);
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const runSession = (payload: RunSessionRequest): Promise<RunSessionResponse> =>
  post('/sessions', payload);

// ---------------------------------------------------------------------------
// MVP4-E: Project
// ---------------------------------------------------------------------------

export const getProjectStatus = (): Promise<ProjectStatus> =>
  get('/project/status');

export const bootstrapProject = (overwrite = false): Promise<BootstrapResponse> =>
  post(`/project/bootstrap${overwrite ? '?overwrite=true' : ''}`, {});

// ---------------------------------------------------------------------------
// MVP4-E: Sources
// ---------------------------------------------------------------------------

export const getSources = (): Promise<SourceItem[]> => get('/sources');

export const uploadSource = async (
  file: File,
  conceptId: string,
  documentId?: string,
): Promise<UploadSourceResponse> => {
  const form = new FormData();
  form.append('file', file);
  form.append('concept_id', conceptId);
  if (documentId) form.append('document_id', documentId);
  // Do NOT set Content-Type manually — browser sets multipart boundary automatically
  const res = await fetch(`${BASE}/sources/upload`, { method: 'POST', body: form });
  if (!res.ok) {
    const d = await res.text();
    throw new Error(`${res.status}: ${d}`);
  }
  return res.json() as Promise<UploadSourceResponse>;
};

// ---------------------------------------------------------------------------
// MVP4-E: Build bank / review / export
// ---------------------------------------------------------------------------

export const buildBank = (p: BuildBankRequest): Promise<BuildBankResponse> =>
  post('/banks/build', p);

export const getGeneratedBank = (id: string): Promise<GeneratedQuestionItem[]> =>
  get(`/banks/${id}/generated`);

export const reviewBank = (
  id: string,
  p: ReviewBankRequest,
): Promise<ReviewBankResponse> => post(`/banks/${id}/review`, p);

export const exportAccepted = (id: string): Promise<ExportAcceptedResponse> =>
  post(`/banks/${id}/export-accepted`, {});

// ---------------------------------------------------------------------------
// MVP4-G0: Concept Compiler
// ---------------------------------------------------------------------------

export const getConcepts = (): Promise<ConceptItem[]> =>
  get('/concepts');

export const compileConcept = (
  conceptId: string,
  req: CompileConceptRequest,
): Promise<CompileConceptResponse> =>
  post(`/concepts/${conceptId}/compile`, req);

// ---------------------------------------------------------------------------
// MVP4-G: Weakness-driven Review Loop
// ---------------------------------------------------------------------------

export const getWeak = (): Promise<WeakRepItem[]> =>
  get('/weak');

// ---------------------------------------------------------------------------
// MVP4-J: STUDY.md Validation
// ---------------------------------------------------------------------------

export const getValidation = (): Promise<StudyValidationReport> =>
  get('/study/validate');

// ---------------------------------------------------------------------------
// MVP4-R0: Chat Compiler Analyzer
// ---------------------------------------------------------------------------

export const analyzeMessage = (req: AnalyzeRequest): Promise<AnalyzeResponse> =>
  post('/compiler/analyze', req);

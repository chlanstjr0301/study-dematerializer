import type {
  HealthResponse,
  DueConceptItem,
  StudyMdResponse,
  BankSummaryItem,
  QuestionItem,
  SessionSummaryItem,
  SessionResponse,
  SummaryResponse,
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

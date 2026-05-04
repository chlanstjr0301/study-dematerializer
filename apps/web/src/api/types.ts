export interface HealthResponse {
  status: string;
}

export interface DueConceptItem {
  concept_id: string;
  next_review: string | null;
  overdue: boolean;
}

export interface StudyMdResponse {
  content: string;
}

export interface BankSummaryItem {
  concept_id: string;
  question_count: number;
}

export interface QuestionItem {
  id: string;
  question: string;
  question_type: string;
  difficulty?: string;
  expected_answer?: string;
  status: string;
  evidence?: Record<string, unknown>;
}

export interface SessionSummaryItem {
  session_id: string;
  concept_id: string;
  started_at: string;
  ended_at?: string | null;
}

export interface SessionResponse {
  session: Record<string, unknown>;
  attempts: Record<string, unknown>[];
}

export interface SummaryResponse {
  content: string;
}

// Visualization artifact shapes matching MVP3.1 outputs

export interface MasteryMapData {
  concept_id?: string;
  overall_mastery?: string;
  weakest_links?: unknown[];
  representations?: unknown[];
}

// recall_feedback.json is a list — one entry per attempt
export type RecallFeedbackData = Array<Record<string, unknown>>;

// review_queue.json is a list — one entry per concept
export type ReviewQueueData = Array<Record<string, unknown>>;

// POST /api/sessions request/response

export interface AnswerInput {
  question_id: string;
  learner_response: string;
}

export interface RunSessionRequest {
  concept_id: string;
  questions_path: string;
  grader: 'mock';
  model?: string;
  limit?: number | null;
  answers?: AnswerInput[];
}

export interface RunSessionResponse {
  session_id: string;
  summary_md: string;
  attempt_count: number;
}

// ---------------------------------------------------------------------------
// MVP4-E: Project
// ---------------------------------------------------------------------------

export interface ProjectStatus {
  project_root: string;
  study_md_exists: boolean;
  banks_dir_exists: boolean;
  runs_dir_exists: boolean;
  sources_dir_exists: boolean;
}

export interface BootstrapResponse {
  created: string[];
  skipped: string[];
}

// ---------------------------------------------------------------------------
// MVP4-E: Sources
// ---------------------------------------------------------------------------

export interface SourceItem {
  source_id: string;
  filename: string;
  relative_path: string;
  size_bytes: number;
  created_at: string;
}

export interface UploadSourceResponse {
  source_path: string;
  filename: string;
  size_bytes: number;
  document_id: string;
}

// ---------------------------------------------------------------------------
// MVP4-E: Build bank
// ---------------------------------------------------------------------------

export interface BuildBankRequest {
  concept_id: string;
  source_relative_path: string;
  document_id: string;
}

export interface BuildBankResponse {
  concept_id: string;
  document_id: string;
  block_count: number;
  question_count: number;
  bank_dir: string;
}

// ---------------------------------------------------------------------------
// MVP4-E: Review / export
// ---------------------------------------------------------------------------

export interface GeneratedQuestionItem {
  question_id: string;
  question: string;
  question_type: string;
  difficulty: string;
  expected_answer: string;
  status: string;
  evidence: Record<string, unknown>;
}

export interface ReviewAction {
  question_id: string;
  action: 'accept' | 'reject' | 'edit' | 'skip';
  updated_question?: string;
  updated_expected_answer?: string;
}

export interface ReviewBankRequest {
  actions: ReviewAction[];
}

export interface ReviewBankResponse {
  total: number;
  accepted: number;
  rejected: number;
  edited: number;
  skipped: number;
}

export interface ExportAcceptedResponse {
  accepted_count: number;
}

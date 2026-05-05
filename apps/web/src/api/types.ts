export interface HealthResponse {
  status: string;
}

export interface DueConceptItem {
  concept_id: string;
  next_review: string | null;
  overdue: boolean;
  // MVP4-I scheduler enrichment
  overall_mastery: string;
  weak_rep_count: number;
  target_representations: string[];
  suggested_mode: string;   // "weak_only" | "full_recall"
  reason: string;
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

export interface MasteryRepresentation {
  type: string;           // formal | intuitive | visual | counterexample | proof_schema
  before: string;         // unknown | partial | solid
  after: string;
  accuracy_score: number; // 0.0–1.0
}

export interface MasteryMapData {
  concept_id: string;
  overall_mastery: string;
  representations: MasteryRepresentation[];
  weakest_links: string[];
}

// recall_feedback.json is a list — one entry per attempt
export interface RecallFeedbackItem {
  question_id: string;
  representation_type: string;
  learner_response: string;
  accuracy_score: number;
  missing_elements: string[];
  errors: string[];
  feedback: string;
  needs_human_review: boolean;
}
export type RecallFeedbackData = RecallFeedbackItem[];

// review_queue.json is a list — one entry per concept
export interface ReviewQueueItem {
  concept_id: string;
  next_review_date: string;       // YYYY-MM-DD
  weakest_representation: string;
  due_status: string;             // overdue | due_today | upcoming
}
export type ReviewQueueData = ReviewQueueItem[];

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

// ---------------------------------------------------------------------------
// MVP4-G0: Concept Compiler
// ---------------------------------------------------------------------------

export interface ConceptItem {
  concept_id: string;
  canonical_name: string;
  domain: string;
  prerequisites: string[];
}

export interface CompileConceptRequest {
  source_relative_path: string;
  document_id: string;
  grader?: 'mock';
}

export interface CompileConceptResponse {
  session_id: string;
  concept_id: string;
  representation_count: number;
  prerequisite_count: number;
  misconception_count: number;
  question_count: number;
  bank_dir: string;
}

// ---------------------------------------------------------------------------
// MVP4-G: Weakness-driven Review Loop
// ---------------------------------------------------------------------------

export interface WeakRepItem {
  concept_id: string;
  rep_type: string;           // formal | intuitive | visual | counterexample | proof_schema
  mastery: string;            // unknown | partial
  last_reviewed: string | null;
  next_review: string | null;
  due_status: string;         // overdue | due_today | upcoming | not_scheduled
}

// ---------------------------------------------------------------------------
// MVP4-J: STUDY.md Validation
// ---------------------------------------------------------------------------

export interface ViolationItem {
  code: string;
  concept_id: string | null;
  field: string | null;
  message: string;
}

export interface StudyValidationReport {
  valid: boolean;
  error_count: number;
  warning_count: number;
  errors: ViolationItem[];
  warnings: ViolationItem[];
}

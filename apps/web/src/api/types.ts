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
  grader: 'mock' | 'llm' | 'self';
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
  grader?: 'mock' | 'llm' | 'self';
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

// ---------------------------------------------------------------------------
// MVP4-R0: Chat Compiler Analyzer
// ---------------------------------------------------------------------------

export interface AnalyzeRequest {
  message: string;
  source_id?: string;
  recent_messages?: string[];
}

export interface PrerequisiteCheck {
  concept_id: string;
  name_ko: string;
  name_en: string;
  status: string;
}

export interface RecommendedAction {
  action_id: string;
  label_ko: string;
  description_ko: string;
  route: string | null;
}

export interface AnalyzeResponse {
  language: string;
  concept_id: string | null;
  canonical_name_ko: string | null;
  canonical_name_en: string | null;
  suspected_gap: string;
  correction: string | null;
  prerequisite_checks: PrerequisiteCheck[];
  recommended_actions: RecommendedAction[];
  representations: Record<string, string> | null;
  intent: string;
  direct_answer: string | null;
}

// ---------------------------------------------------------------------------
// MVP6: Mapping Tasks + Confusion Map
// ---------------------------------------------------------------------------

export interface MappingTaskItem {
  task_id: string;
  task_type: string;
  prompt: string;
  source_representations: string[];
  target_representation: string;
}

export interface MappingTasksResponse {
  session_id: string;
  concept_id: string;
  tasks: MappingTaskItem[];
}

export interface MappingSubmitResult {
  task_id: string;
  task_type: string;
  score: number;
  passed: boolean;
  missing_elements: string[];
  misconception_tags: string[];
  mapping_failures: string[];
  feedback: string;
  next_recall_trigger: string;
  confusion_map: ConfusionMapData;
}

export interface PrerequisiteNodeItem {
  concept_id: string;
  mastery: string;
  self_reported: string | null;
}

export interface MappingEdgeItem {
  from_rep: string;
  to_rep: string;
  task_type: string;
  passed: boolean;
  score: number;
}

export interface EvidenceSnippetItem {
  step: string;
  task_type: string | null;
  learner_text: string;
  issue: string;
}

export interface ConfusionMapData {
  concept_id: string;
  session_id: string;
  prerequisite_nodes: PrerequisiteNodeItem[];
  mapping_edges: MappingEdgeItem[];
  misconception_tags: string[];
  next_recall_triggers: string[];
  evidence_snippets: EvidenceSnippetItem[];
  last_updated_step: string;
}

// ---------------------------------------------------------------------------
// MVP5-3: Study Session
// ---------------------------------------------------------------------------

export interface StudyPrerequisiteInfo {
  concept_id: string;
  name_ko: string;
  mastery: string;  // "unknown" | "partial" | "solid"
}

export interface MisconceptionInfo {
  id: string;
  claim: string;
  is_correct: boolean;
}

export interface CreateStudySessionRequest {
  concept_id: string;
  source_relative_path?: string | null;
}

export interface CreateStudySessionResponse {
  session_id: string;
  concept_id: string;
  canonical_name_ko: string;
  current_step: number;
  steps: string[];
  representations: Record<string, string>;
  prerequisites: StudyPrerequisiteInfo[];
  misconceptions: MisconceptionInfo[];
}

export interface DiagnoseRequest {
  prior_knowledge: string;
  gap_description: string;
}

export interface DiagnoseResponse {
  initial_mastery_estimate: string;
  identified_gaps: string[];
  recommendation: string;
}

export interface AdvanceStepRequest {
  completed_step: string;
}

export interface AdvanceStepResponse {
  current_step: number;
  current_step_name: string;
  steps_completed: string[];
}

export interface DiagnosisData {
  prior_knowledge: string;
  gap_description: string;
  initial_mastery_estimate: string;
  identified_gaps: string[];
  recommendation: string;
}

export interface StudySessionStateResponse {
  session_id: string;
  concept_id: string;
  canonical_name_ko: string;
  current_step: number;
  steps: string[];
  steps_completed: string[];
  diagnosis: DiagnosisData | null;
  self_explanations: Record<string, unknown> | null;
  recall_completed: boolean;
  recall_session_id: string | null;
  completed: boolean;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// MVP5-4: Study Session Completion Loop
// ---------------------------------------------------------------------------

export interface SelfExplainRequest {
  representation_type: string;
  learner_explanation: string;
}

export interface SelfExplainResponse {
  representation_type: string;
  accuracy_score: number;
  missing_elements: string[];
  errors: string[];
  feedback: string;
  grader_source?: string;
}

export interface RecallSubmitRequest {
  learner_response: string;
}

export interface RecallSubmitResponse {
  accuracy_score: number;
  missing_elements: string[];
  errors: string[];
  feedback: string;
  grader_source?: string;
}

export interface MasteryUpdateItem {
  representation_type: string;
  before: string;
  after: string;
  accuracy_score: number;
}

export interface CompleteStudySessionResponse {
  session_id: string;
  completed: boolean;
  mastery_updates: MasteryUpdateItem[];
  next_review_date: string;
  study_md_updated: boolean;
  study_patch_path: string | null;
  completion_summary: string;
}

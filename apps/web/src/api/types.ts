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

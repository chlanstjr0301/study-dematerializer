"""
Pydantic request/response schemas for the Gonghaebun API.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from gonghaebun.llm.config import DEFAULT_OPENAI_MODEL


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict[str, str]
    default_grader: str = "mock"  # "llm" when available, "mock" otherwise


class DueConceptItem(BaseModel):
    concept_id: str
    next_review: str | None
    overdue: bool
    # MVP4-I: scheduler enrichment
    overall_mastery: str                # unknown | partial | solid
    weak_rep_count: int                 # len(target_representations)
    target_representations: list[str]   # non-solid rep types sorted: unknown first, then partial
    suggested_mode: str                 # "weak_only" | "full_recall"
    reason: str                         # human-readable summary


class StudyMdResponse(BaseModel):
    content: str


class BankSummaryItem(BaseModel):
    concept_id: str
    question_count: int


class QuestionItem(BaseModel):
    id: str
    question: str
    question_type: str
    expected_answer: str
    status: str


class SessionSummaryItem(BaseModel):
    session_id: str
    concept_id: str
    started_at: str
    ended_at: str | None = None


class SessionResponse(BaseModel):
    session: dict[str, Any]
    attempts: list[dict[str, Any]]


class RunSessionResponse(BaseModel):
    session_id: str
    summary_md: str
    attempt_count: int


class SummaryResponse(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Request schemas (POST /api/sessions)
# ---------------------------------------------------------------------------

class AnswerInput(BaseModel):
    question_id: str
    learner_response: str
    self_score: int | None = None   # required when grader="self"


class RunSessionRequest(BaseModel):
    concept_id: str
    questions_path: str             # relative to BANK_ROOT; validated by safe_resolve_under()
    grader: Literal["self", "mock", "llm"] = "mock"
    model: str = DEFAULT_OPENAI_MODEL
    limit: int | None = None
    answers: list[AnswerInput] | None = None        # explicit per-question answers
    default_answer: str | None = None               # fallback for smoke/non-interactive runs


# ---------------------------------------------------------------------------
# MVP4-E: Project bootstrap
# ---------------------------------------------------------------------------

class ProjectStatus(BaseModel):
    project_root: str
    study_md_exists: bool
    banks_dir_exists: bool
    runs_dir_exists: bool
    sources_dir_exists: bool


class BootstrapResponse(BaseModel):
    created: list[str]
    skipped: list[str]


# ---------------------------------------------------------------------------
# MVP4-E: Sources
# ---------------------------------------------------------------------------

class SourceItem(BaseModel):
    source_id: str
    filename: str
    relative_path: str
    size_bytes: int
    created_at: str


class UploadSourceResponse(BaseModel):
    source_path: str
    filename: str
    size_bytes: int
    document_id: str


# ---------------------------------------------------------------------------
# MVP4-E: Build bank
# ---------------------------------------------------------------------------

class BuildBankRequest(BaseModel):
    concept_id: str
    source_relative_path: str
    document_id: str


class BuildBankResponse(BaseModel):
    concept_id: str
    document_id: str
    block_count: int
    question_count: int
    bank_dir: str


# ---------------------------------------------------------------------------
# MVP4-E: Review / export
# ---------------------------------------------------------------------------

class GeneratedQuestionItem(BaseModel):
    question_id: str
    question: str
    question_type: str
    difficulty: str
    expected_answer: str
    status: str
    evidence: dict[str, Any]


class ReviewActionItem(BaseModel):
    question_id: str
    action: Literal["accept", "reject", "edit", "skip"]
    updated_question: str | None = None
    updated_expected_answer: str | None = None


class ReviewBankRequest(BaseModel):
    actions: list[ReviewActionItem]


class ReviewBankResponse(BaseModel):
    total: int
    accepted: int
    rejected: int
    edited: int
    skipped: int


class ExportAcceptedResponse(BaseModel):
    accepted_count: int


# ---------------------------------------------------------------------------
# MVP4-G0: Concept Compiler
# ---------------------------------------------------------------------------

class ConceptItem(BaseModel):
    concept_id: str
    canonical_name: str
    domain: str
    prerequisites: list[str]


class CompileConceptRequest(BaseModel):
    source_relative_path: str
    document_id: str
    grader: Literal["mock"] = "mock"


class CompileConceptResponse(BaseModel):
    session_id: str
    concept_id: str
    representation_count: int
    prerequisite_count: int
    misconception_count: int
    question_count: int
    bank_dir: str


# ---------------------------------------------------------------------------
# MVP4-G: Weakness-driven Review Loop
# ---------------------------------------------------------------------------

class WeakRepItem(BaseModel):
    concept_id: str
    rep_type: str           # formal | intuitive | visual | counterexample | proof_schema
    mastery: str            # unknown | partial
    last_reviewed: str | None   # YYYY-MM-DD or null
    next_review: str | None     # concept-level next_review date
    due_status: str         # overdue | due_today | upcoming | not_scheduled


# ---------------------------------------------------------------------------
# MVP4-H: STUDY.md Canonical State Validation
# ---------------------------------------------------------------------------

class ViolationItem(BaseModel):
    code: str               # E001–E005, W001–W003
    concept_id: str | None  # None = file-level violation (e.g. E005)
    field: str | None       # "overall_mastery", "rep[formal].mastery", etc.
    message: str


class StudyValidationReport(BaseModel):
    valid: bool
    error_count: int
    warning_count: int
    errors: list[ViolationItem]
    warnings: list[ViolationItem]


# ---------------------------------------------------------------------------
# MVP4-R0: Chat Compiler Analyzer
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    message: str
    source_id: str | None = None
    recent_messages: list[str] | None = None


class PrerequisiteCheck(BaseModel):
    concept_id: str
    name_ko: str
    name_en: str
    status: str  # "미확인"


class RecommendedAction(BaseModel):
    action_id: str
    label_ko: str
    description_ko: str
    route: str | None = None  # None = inline action, no navigation


class StudyUpdateCandidateSchema(BaseModel):
    concept_id: str | None = None
    summary: str = ""
    evidence: list[str] = []
    misconception_tags: list[str] = []
    next_recall_tasks: list[str] = []


class AnalyzeResponse(BaseModel):
    language: str  # always "ko"
    concept_id: str | None
    canonical_name_ko: str | None
    canonical_name_en: str | None
    suspected_gap: str
    correction: str | None = None
    prerequisite_checks: list[PrerequisiteCheck]
    recommended_actions: list[RecommendedAction]
    representations: dict[str, str] | None = None
    intent: str = "concept_lookup"
    direct_answer: str | None = None
    render_mode: str = "card"  # "card" (full AnalysisCard) | "bubble" (text only)
    # LLM Tutor overlay fields
    llm_used: bool = False
    rag_used: bool = False
    retrieved_context: list[dict] | None = None
    learning_task: str | None = None
    misconception_tags: list[str] | None = None
    missing_elements: list[str] | None = None
    study_update_candidate: StudyUpdateCandidateSchema | None = None


# ---------------------------------------------------------------------------
# MVP5-2: Study Session API
# ---------------------------------------------------------------------------

class CreateStudySessionRequest(BaseModel):
    concept_id: str
    source_relative_path: str | None = None


class PrerequisiteInfo(BaseModel):
    concept_id: str
    name_ko: str
    mastery: str  # "unknown" | "partial" | "solid"


class MisconceptionInfo(BaseModel):
    id: str
    claim: str
    is_correct: bool


class CreateStudySessionResponse(BaseModel):
    session_id: str
    concept_id: str
    canonical_name_ko: str
    current_step: int
    steps: list[str]
    representations: dict[str, str]
    prerequisites: list[PrerequisiteInfo]
    misconceptions: list[MisconceptionInfo]


class DiagnosisData(BaseModel):
    prior_knowledge: str
    gap_description: str
    initial_mastery_estimate: str
    identified_gaps: list[str]
    recommendation: str


class StudySessionStateResponse(BaseModel):
    session_id: str
    concept_id: str
    canonical_name_ko: str
    current_step: int
    steps: list[str]
    steps_completed: list[str]
    diagnosis: DiagnosisData | None = None
    self_explanations: dict[str, Any] | None = None
    recall_completed: bool
    recall_session_id: str | None = None
    completed: bool
    completed_at: str | None = None
    created_at: str
    updated_at: str


class DiagnoseRequest(BaseModel):
    prior_knowledge: str = ""
    gap_description: str = ""


class DiagnoseResponse(BaseModel):
    initial_mastery_estimate: str
    identified_gaps: list[str]
    recommendation: str


class AdvanceStepRequest(BaseModel):
    completed_step: str


class AdvanceStepResponse(BaseModel):
    current_step: int
    current_step_name: str
    steps_completed: list[str]


# ---------------------------------------------------------------------------
# MVP5-4: Study Session Completion Loop
# ---------------------------------------------------------------------------

class SelfExplainRequest(BaseModel):
    representation_type: str
    learner_explanation: str


class SelfExplainResponse(BaseModel):
    representation_type: str
    accuracy_score: float
    missing_elements: list[str]
    errors: list[str]
    feedback: str
    grader_source: str = "mock"


class RecallSubmitRequest(BaseModel):
    learner_response: str


class RecallSubmitResponse(BaseModel):
    accuracy_score: float
    missing_elements: list[str]
    errors: list[str]
    feedback: str
    grader_source: str = "mock"


class MasteryUpdateItem(BaseModel):
    representation_type: str
    before: str
    after: str
    accuracy_score: float


class CompleteStudySessionResponse(BaseModel):
    session_id: str
    completed: bool
    mastery_updates: list[MasteryUpdateItem]
    next_review_date: str
    study_md_updated: bool
    study_patch_path: str | None
    completion_summary: str


# ---------------------------------------------------------------------------
# MVP6: Mapping Tasks + Confusion Map
# ---------------------------------------------------------------------------

class MappingTaskItem(BaseModel):
    task_id: str
    task_type: str
    prompt: str                         # Korean
    source_representations: list[str]
    target_representation: str


class MappingTasksResponse(BaseModel):
    session_id: str
    concept_id: str
    tasks: list[MappingTaskItem]


class MappingSubmitRequest(BaseModel):
    task_id: str
    learner_response: str               # Korean text


class PrerequisiteNodeItem(BaseModel):
    concept_id: str
    mastery: str
    self_reported: str | None = None


class MappingEdgeItem(BaseModel):
    from_rep: str
    to_rep: str
    task_type: str
    passed: bool
    score: float


class EvidenceSnippetItem(BaseModel):
    step: str
    task_type: str | None = None
    learner_text: str
    issue: str


class ConfusionMapResponse(BaseModel):
    concept_id: str
    session_id: str
    prerequisite_nodes: list[PrerequisiteNodeItem]
    mapping_edges: list[MappingEdgeItem]
    misconception_tags: list[str]
    next_recall_triggers: list[str]
    evidence_snippets: list[EvidenceSnippetItem]
    last_updated_step: str


class MappingSubmitResponse(BaseModel):
    task_id: str
    task_type: str
    score: float
    passed: bool
    missing_elements: list[str]
    misconception_tags: list[str]
    mapping_failures: list[str]
    feedback: str                       # Korean
    next_recall_trigger: str
    confusion_map: ConfusionMapResponse

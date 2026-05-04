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


class DueConceptItem(BaseModel):
    concept_id: str
    next_review: str | None
    overdue: bool


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

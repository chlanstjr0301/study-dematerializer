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

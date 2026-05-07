"""
Mapping task and result models for MVP6.

MappingTask: a single mapping task presented to the learner during a study session.
MappingResult: the evaluated result of one mapping task submission.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator


class MappingTaskType(str, Enum):
    FORMAL_TO_COUNTEREXAMPLE = "formal_to_counterexample"
    COUNTEREXAMPLE_TO_FORMAL = "counterexample_to_formal"
    FORMAL_COUNTEREXAMPLE_TO_PROOF_SCHEMA = "formal_counterexample_to_proof_schema"


class MappingTask(BaseModel):
    """A single mapping task presented to the learner."""

    task_id: str
    session_id: str
    concept_id: str
    task_type: MappingTaskType
    prompt: str
    required_terms: list[str]
    grounding_notes: str
    source_representations: list[str]
    target_representation: str

    @field_validator("required_terms")
    @classmethod
    def _terms_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_terms must not be empty")
        return v

    @field_validator("source_representations")
    @classmethod
    def _source_reps_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("source_representations must not be empty")
        return v


class MappingResult(BaseModel):
    """Result of evaluating one mapping task submission."""

    task_id: str
    task_type: MappingTaskType
    learner_response: str
    score: float  # 0.0–1.0
    passed: bool  # score >= 0.70
    missing_elements: list[str]
    incorrect_claims: list[str]
    misconception_tags: list[str]
    mapping_failures: list[str]
    feedback: str
    next_recall_trigger: str
    needs_human_review: bool = False
    evaluated_at: str  # ISO datetime

    @field_validator("score")
    @classmethod
    def _score_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score must be between 0.0 and 1.0, got {v}")
        return v

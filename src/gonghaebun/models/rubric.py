"""
Rubric models for MVP6.

A ConceptRubric defines evaluation criteria for one concept: required terms
(with weights and aliases), misconception trigger patterns, pass thresholds,
and scoring methods — per task type.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class TermCheck(BaseModel):
    """One required term with weight and optional aliases."""

    term: str
    weight: float = 1.0
    aliases: list[str] = []

    @field_validator("weight")
    @classmethod
    def _weight_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"weight must be positive, got {v}")
        return v


class MisconceptionCheck(BaseModel):
    """One misconception pattern to detect."""

    misconception_id: str
    trigger_patterns: list[str]
    severity: Literal["critical", "moderate", "minor"] = "moderate"

    @field_validator("trigger_patterns")
    @classmethod
    def _patterns_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("trigger_patterns must not be empty")
        return v


class TaskRubric(BaseModel):
    """Rubric for one task type."""

    task_type: str
    required_terms: list[TermCheck]
    misconception_checks: list[MisconceptionCheck]
    pass_threshold: float = 0.70
    scoring_method: Literal["term_coverage", "weighted_terms"] = "term_coverage"

    @field_validator("pass_threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"pass_threshold must be between 0.0 and 1.0, got {v}")
        return v


class ConceptRubric(BaseModel):
    """Complete rubric for one concept."""

    concept_id: str
    domain: str
    version: str = "1.0"
    task_rubrics: dict[str, TaskRubric]
    global_misconception_checks: list[MisconceptionCheck]

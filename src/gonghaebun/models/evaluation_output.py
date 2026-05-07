"""
Unified evaluator output model for MVP6.

EvaluationOutput is used by the DeterministicEvaluator (and future LLM evaluator)
for all task types: self-explanation, mapping, recall, and misconception quiz.
Kept separate from the existing GradingResult for backward compatibility.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class EvaluationOutput(BaseModel):
    """Unified evaluator output for all task types."""

    score: float  # 0.0–1.0
    mastery: Literal["unknown", "partial", "solid"]
    passed: bool  # score >= threshold
    missing_elements: list[str]
    incorrect_claims: list[str]
    misconception_tags: list[str]
    mapping_failures: list[str]
    needs_human_review: bool = False
    feedback: str
    next_recall_trigger: str = ""

    @field_validator("score")
    @classmethod
    def _score_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score must be between 0.0 and 1.0, got {v}")
        return v

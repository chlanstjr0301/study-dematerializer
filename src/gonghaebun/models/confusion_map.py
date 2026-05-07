"""
Confusion map models for MVP6.

A ConfusionMap is a per-session learner diagnostic artifact that tracks
prerequisite mastery, mapping edge results, misconception detections,
and evidence snippets across all session steps.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class PrerequisiteNode(BaseModel):
    concept_id: str
    mastery: Literal["unknown", "partial", "solid"]
    self_reported: str | None = None  # "known", "unsure", "never_seen"


class MappingEdge(BaseModel):
    from_rep: str
    to_rep: str
    task_type: str
    passed: bool
    score: float
    attempt_count: int = 1

    @field_validator("score")
    @classmethod
    def _score_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("attempt_count")
    @classmethod
    def _attempt_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"attempt_count must be >= 1, got {v}")
        return v


class EvidenceSnippet(BaseModel):
    step: str
    task_type: str | None = None
    learner_text: str  # max 200 chars (enforced by validator)
    issue: str

    @field_validator("learner_text")
    @classmethod
    def _truncate_text(cls, v: str) -> str:
        if len(v) > 200:
            return v[:200]
        return v


class ConfusionMap(BaseModel):
    """Per-session learner diagnostic artifact."""

    concept_id: str
    session_id: str
    prerequisite_nodes: list[PrerequisiteNode]
    mapping_edges: list[MappingEdge]
    misconception_tags: list[str]
    next_recall_triggers: list[str]
    evidence_snippets: list[EvidenceSnippet]
    last_updated_step: str
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from .concept import MasteryLevel
from .representations import RepresentationType

SessionType = Literal["new_concept", "review", "deep_dive"]


@dataclass
class RecallEvaluation:
    accuracy_score: float        # 0.0 – 1.0
    missing_elements: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    feedback: str = ""


@dataclass
class RecallAttempt:
    session_id: str
    concept_id: str
    representation_type: RepresentationType
    learner_response: str
    evaluation: RecallEvaluation
    attempted_at: str            # ISO 8601


@dataclass
class MasteryUpdate:
    concept_id: str
    representation_type: RepresentationType
    before: MasteryLevel
    after: MasteryLevel
    next_review_date: str        # YYYY-MM-DD


@dataclass
class StudySession:
    session_id: str
    session_type: SessionType
    concept_ids: list[str]
    started_at: str              # ISO 8601
    ended_at: str | None = None
    llm_backend: str = "mock"
    # Source grounding
    source_path: str = ""
    source_hash: str = ""
    grounding_mode: str = "local_private_source"
    source_excerpt_path: str = ""
    source_manifest_path: str = ""
    # Results
    mastery_updates: list[MasteryUpdate] = field(default_factory=list)
    recall_attempts: list[RecallAttempt] = field(default_factory=list)

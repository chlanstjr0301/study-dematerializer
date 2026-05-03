from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from .concept import MasteryLevel

RepresentationType = Literal["formal", "intuitive", "visual", "counterexample", "proof_schema"]


@dataclass
class Representation:
    type: RepresentationType
    content: str
    mastery_state: MasteryLevel = "unknown"
    last_reviewed: str | None = None  # ISO 8601


@dataclass
class RepresentationSet:
    concept_id: str
    formal: Representation = field(default_factory=lambda: Representation(type="formal", content=""))
    intuitive: Representation = field(default_factory=lambda: Representation(type="intuitive", content=""))
    visual: Representation = field(default_factory=lambda: Representation(type="visual", content=""))
    counterexample: Representation = field(default_factory=lambda: Representation(type="counterexample", content=""))
    proof_schema: Representation = field(default_factory=lambda: Representation(type="proof_schema", content=""))
    generated_at: str = ""
    model_used: str = "mock"

    def as_list(self) -> list[Representation]:
        return [self.formal, self.intuitive, self.visual, self.counterexample, self.proof_schema]

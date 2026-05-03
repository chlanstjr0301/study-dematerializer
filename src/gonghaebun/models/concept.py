from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

MasteryLevel = Literal["unknown", "partial", "solid"]


@dataclass
class Concept:
    concept_id: str
    canonical_name: str
    domain: str
    aliases: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

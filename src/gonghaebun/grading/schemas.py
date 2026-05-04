"""
GradingResult dataclass — the canonical output of any AnswerGrader.

All graders (SelfGrader, LLMGrader) produce a GradingResult.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_MASTERY_VALUES = {"unknown", "partial", "solid"}
_ALIGNMENT_VALUES = {"supported", "partially_supported", "unsupported"}


@dataclass
class GradingResult:
    """
    Structured result from grading a learner's answer.

    Fields
    ------
    accuracy_score    : float 0.0–1.0
    missing_elements  : elements present in the expected answer but absent in the response
    errors            : explicit errors or misconceptions detected
    feedback          : human-readable summary for the learner
    mastery_suggestion: "unknown" | "partial" | "solid"
    confidence        : grader's confidence in the result (0.0–1.0)
    needs_human_review: True when the grader cannot reliably evaluate the response
    evidence_alignment: how well the learner response aligns with the source evidence
    raw_response      : verbatim grader output ("self:{score}" for SelfGrader;
                        raw LLM text for LLMGrader)
    """

    accuracy_score: float
    missing_elements: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    feedback: str = ""
    mastery_suggestion: str = "unknown"
    confidence: float = 1.0
    needs_human_review: bool = False
    evidence_alignment: str = "supported"
    raw_response: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.accuracy_score <= 1.0:
            raise ValueError(
                f"accuracy_score must be in [0.0, 1.0], got {self.accuracy_score!r}"
            )
        if self.mastery_suggestion not in _MASTERY_VALUES:
            raise ValueError(
                f"mastery_suggestion must be one of {sorted(_MASTERY_VALUES)}, "
                f"got {self.mastery_suggestion!r}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence!r}"
            )
        if self.evidence_alignment not in _ALIGNMENT_VALUES:
            raise ValueError(
                f"evidence_alignment must be one of {sorted(_ALIGNMENT_VALUES)}, "
                f"got {self.evidence_alignment!r}"
            )

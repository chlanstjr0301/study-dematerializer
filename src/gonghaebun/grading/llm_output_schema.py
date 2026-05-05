"""
Intermediate schema for LLM grading output.

LLMGradingOutput is the expected shape of the JSON dict returned by the LLM.
It is decoupled from GradingResult to allow the LLM response schema to evolve
independently of the internal grading data model.

llm_output_to_grading_result() is the compatibility bridge between the two.
"""
from __future__ import annotations

from dataclasses import dataclass

from gonghaebun.grading.schemas import GradingResult

_MASTERY_VALUES = {"unknown", "partial", "solid"}

# JSON Schema dict for provider-level structured output enforcement.
# Passed to LLMClient.complete_structured(); also used locally by validate_llm_output().
LLM_GRADING_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "accuracy_score": {"type": "number"},
        "mastery_after": {"type": "string", "enum": ["unknown", "partial", "solid"]},
        "missing_elements": {"type": "array", "items": {"type": "string"}},
        "errors": {"type": "array", "items": {"type": "string"}},
        "misconception_flags": {"type": "array", "items": {"type": "string"}},
        "evidence_alignment_score": {"type": "number"},
        "needs_human_review": {"type": "boolean"},
        "short_feedback": {"type": "string"},
    },
    "required": [
        "accuracy_score",
        "mastery_after",
        "missing_elements",
        "errors",
        "misconception_flags",
        "evidence_alignment_score",
        "needs_human_review",
        "short_feedback",
    ],
    "additionalProperties": False,
}


@dataclass
class LLMGradingOutput:
    """Structured output expected from the LLM grading call."""

    accuracy_score: float
    mastery_after: str              # "unknown" | "partial" | "solid"
    missing_elements: list[str]
    errors: list[str]
    misconception_flags: list[str]
    evidence_alignment_score: float  # 0.0–1.0
    needs_human_review: bool
    short_feedback: str


def validate_llm_output(data: dict) -> LLMGradingOutput:
    """
    Validate a raw dict against LLMGradingOutput.

    Raises ValueError with a field-level message on any violation.
    Returns a validated LLMGradingOutput on success.
    """
    required = [
        "accuracy_score", "mastery_after", "missing_elements", "errors",
        "misconception_flags", "evidence_alignment_score", "needs_human_review",
        "short_feedback",
    ]
    for key in required:
        if key not in data:
            raise ValueError(f"LLM output missing required field: {key!r}")

    accuracy = data["accuracy_score"]
    if not isinstance(accuracy, (int, float)):
        raise ValueError(
            f"accuracy_score must be a number, got {type(accuracy).__name__}"
        )
    if not 0.0 <= float(accuracy) <= 1.0:
        raise ValueError(
            f"accuracy_score must be in [0.0, 1.0], got {accuracy!r}"
        )

    mastery = data["mastery_after"]
    if mastery not in _MASTERY_VALUES:
        raise ValueError(
            f"mastery_after must be one of {sorted(_MASTERY_VALUES)}, got {mastery!r}"
        )

    eas = data["evidence_alignment_score"]
    if not isinstance(eas, (int, float)):
        raise ValueError(
            f"evidence_alignment_score must be a number, got {type(eas).__name__}"
        )
    if not 0.0 <= float(eas) <= 1.0:
        raise ValueError(
            f"evidence_alignment_score must be in [0.0, 1.0], got {eas!r}"
        )

    for list_field in ("missing_elements", "errors", "misconception_flags"):
        val = data[list_field]
        if not isinstance(val, list):
            raise ValueError(
                f"{list_field!r} must be a list, got {type(val).__name__}"
            )

    if not isinstance(data["needs_human_review"], bool):
        raise ValueError(
            f"needs_human_review must be a bool, "
            f"got {type(data['needs_human_review']).__name__}"
        )

    if not isinstance(data["short_feedback"], str):
        raise ValueError(
            f"short_feedback must be a string, "
            f"got {type(data['short_feedback']).__name__}"
        )

    return LLMGradingOutput(
        accuracy_score=float(data["accuracy_score"]),
        mastery_after=data["mastery_after"],
        missing_elements=list(data["missing_elements"]),
        errors=list(data["errors"]),
        misconception_flags=list(data["misconception_flags"]),
        evidence_alignment_score=float(data["evidence_alignment_score"]),
        needs_human_review=bool(data["needs_human_review"]),
        short_feedback=str(data["short_feedback"]),
    )


def llm_output_to_grading_result(
    out: LLMGradingOutput,
    raw_response: str,
) -> GradingResult:
    """
    Convert an LLMGradingOutput to a GradingResult.

    Field mappings
    --------------
    mastery_after            → mastery_suggestion
    short_feedback           → feedback
    evidence_alignment_score → evidence_alignment (bucketed: ≥0.7=supported,
                               ≥0.4=partially_supported, <0.4=unsupported)
    misconception_flags      → appended to errors list
    confidence               → derived from evidence_alignment_score
    raw_response             → stored verbatim
    """
    eas = out.evidence_alignment_score
    if eas >= 0.7:
        evidence_alignment = "supported"
    elif eas >= 0.4:
        evidence_alignment = "partially_supported"
    else:
        evidence_alignment = "unsupported"

    return GradingResult(
        accuracy_score=out.accuracy_score,
        missing_elements=out.missing_elements,
        errors=out.errors + out.misconception_flags,
        feedback=out.short_feedback,
        mastery_suggestion=out.mastery_after,
        confidence=out.evidence_alignment_score,
        needs_human_review=out.needs_human_review,
        evidence_alignment=evidence_alignment,
        raw_response=raw_response,
    )

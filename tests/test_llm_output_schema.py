"""Tests for grading/llm_output_schema.py (MVP4-J0)."""
from __future__ import annotations

import pytest

from gonghaebun.grading.llm_output_schema import (
    LLMGradingOutput,
    LLM_GRADING_OUTPUT_SCHEMA,
    llm_output_to_grading_result,
    validate_llm_output,
)
from gonghaebun.grading.schemas import GradingResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_DICT: dict = {
    "accuracy_score": 0.75,
    "mastery_after": "partial",
    "missing_elements": ["formal epsilon-delta definition"],
    "errors": [],
    "misconception_flags": [],
    "evidence_alignment_score": 0.85,
    "needs_human_review": False,
    "short_feedback": "Good intuitive understanding. Missing formal precision.",
}


# ---------------------------------------------------------------------------
# TestValidateLLMOutput
# ---------------------------------------------------------------------------


class TestValidateLLMOutput:
    def test_valid_dict_returns_llm_grading_output(self):
        result = validate_llm_output(_VALID_DICT)
        assert isinstance(result, LLMGradingOutput)

    def test_accuracy_score_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.accuracy_score == pytest.approx(0.75)

    def test_mastery_after_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.mastery_after == "partial"

    def test_missing_elements_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.missing_elements == ["formal epsilon-delta definition"]

    def test_misconception_flags_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.misconception_flags == []

    def test_evidence_alignment_score_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.evidence_alignment_score == pytest.approx(0.85)

    def test_needs_human_review_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert result.needs_human_review is False

    def test_short_feedback_preserved(self):
        result = validate_llm_output(_VALID_DICT)
        assert "intuitive" in result.short_feedback

    # Missing keys
    def test_missing_accuracy_score_raises(self):
        bad = {k: v for k, v in _VALID_DICT.items() if k != "accuracy_score"}
        with pytest.raises(ValueError, match="accuracy_score"):
            validate_llm_output(bad)

    def test_missing_mastery_after_raises(self):
        bad = {k: v for k, v in _VALID_DICT.items() if k != "mastery_after"}
        with pytest.raises(ValueError, match="mastery_after"):
            validate_llm_output(bad)

    def test_missing_short_feedback_raises(self):
        bad = {k: v for k, v in _VALID_DICT.items() if k != "short_feedback"}
        with pytest.raises(ValueError, match="short_feedback"):
            validate_llm_output(bad)

    def test_missing_misconception_flags_raises(self):
        bad = {k: v for k, v in _VALID_DICT.items() if k != "misconception_flags"}
        with pytest.raises(ValueError, match="misconception_flags"):
            validate_llm_output(bad)

    # Range violations
    def test_accuracy_score_below_zero_raises(self):
        bad = {**_VALID_DICT, "accuracy_score": -0.1}
        with pytest.raises(ValueError, match="accuracy_score"):
            validate_llm_output(bad)

    def test_accuracy_score_above_one_raises(self):
        bad = {**_VALID_DICT, "accuracy_score": 1.1}
        with pytest.raises(ValueError, match="accuracy_score"):
            validate_llm_output(bad)

    def test_evidence_alignment_score_below_zero_raises(self):
        bad = {**_VALID_DICT, "evidence_alignment_score": -0.5}
        with pytest.raises(ValueError, match="evidence_alignment_score"):
            validate_llm_output(bad)

    def test_evidence_alignment_score_above_one_raises(self):
        bad = {**_VALID_DICT, "evidence_alignment_score": 1.5}
        with pytest.raises(ValueError, match="evidence_alignment_score"):
            validate_llm_output(bad)

    # Invalid enum
    def test_invalid_mastery_after_raises(self):
        bad = {**_VALID_DICT, "mastery_after": "excellent"}
        with pytest.raises(ValueError, match="mastery_after"):
            validate_llm_output(bad)

    # Type violations
    def test_missing_elements_not_list_raises(self):
        bad = {**_VALID_DICT, "missing_elements": "not a list"}
        with pytest.raises(ValueError, match="missing_elements"):
            validate_llm_output(bad)

    def test_needs_human_review_not_bool_raises(self):
        bad = {**_VALID_DICT, "needs_human_review": "yes"}
        with pytest.raises(ValueError, match="needs_human_review"):
            validate_llm_output(bad)

    # Edge: all valid mastery values
    def test_all_mastery_values_accepted(self):
        for m in ("unknown", "partial", "solid"):
            d = {**_VALID_DICT, "mastery_after": m}
            out = validate_llm_output(d)
            assert out.mastery_after == m

    # Edge: boundary scores
    def test_accuracy_score_exactly_zero_ok(self):
        d = {**_VALID_DICT, "accuracy_score": 0.0}
        out = validate_llm_output(d)
        assert out.accuracy_score == pytest.approx(0.0)

    def test_accuracy_score_exactly_one_ok(self):
        d = {**_VALID_DICT, "accuracy_score": 1.0}
        out = validate_llm_output(d)
        assert out.accuracy_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# TestLLMOutputToGradingResult
# ---------------------------------------------------------------------------


class TestLLMOutputToGradingResult:
    def _out(self, **overrides) -> LLMGradingOutput:
        base = LLMGradingOutput(
            accuracy_score=0.75,
            mastery_after="partial",
            missing_elements=["element A"],
            errors=["error B"],
            misconception_flags=["misconception C"],
            evidence_alignment_score=0.85,
            needs_human_review=False,
            short_feedback="Good but incomplete.",
        )
        for k, v in overrides.items():
            object.__setattr__(base, k, v)
        return base

    def test_returns_grading_result(self):
        gr = llm_output_to_grading_result(self._out(), "raw")
        assert isinstance(gr, GradingResult)

    def test_mastery_after_maps_to_mastery_suggestion(self):
        gr = llm_output_to_grading_result(self._out(mastery_after="solid"), "raw")
        assert gr.mastery_suggestion == "solid"

    def test_short_feedback_maps_to_feedback(self):
        gr = llm_output_to_grading_result(self._out(short_feedback="Excellent!"), "raw")
        assert gr.feedback == "Excellent!"

    def test_misconception_flags_appended_to_errors(self):
        out = self._out(errors=["err1"], misconception_flags=["misc1", "misc2"])
        gr = llm_output_to_grading_result(out, "raw")
        assert "err1" in gr.errors
        assert "misc1" in gr.errors
        assert "misc2" in gr.errors
        assert len(gr.errors) == 3

    def test_evidence_alignment_high_is_supported(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.9), "raw")
        assert gr.evidence_alignment == "supported"

    def test_evidence_alignment_mid_is_partially_supported(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.5), "raw")
        assert gr.evidence_alignment == "partially_supported"

    def test_evidence_alignment_low_is_unsupported(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.2), "raw")
        assert gr.evidence_alignment == "unsupported"

    def test_evidence_alignment_boundary_07_is_supported(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.7), "raw")
        assert gr.evidence_alignment == "supported"

    def test_evidence_alignment_boundary_04_is_partially_supported(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.4), "raw")
        assert gr.evidence_alignment == "partially_supported"

    def test_confidence_derived_from_evidence_alignment_score(self):
        gr = llm_output_to_grading_result(self._out(evidence_alignment_score=0.6), "raw")
        assert gr.confidence == pytest.approx(0.6)

    def test_raw_response_stored_verbatim(self):
        gr = llm_output_to_grading_result(self._out(), "my verbatim raw response")
        assert gr.raw_response == "my verbatim raw response"

    def test_needs_human_review_preserved(self):
        gr = llm_output_to_grading_result(self._out(needs_human_review=True), "raw")
        assert gr.needs_human_review is True

    def test_accuracy_score_preserved(self):
        gr = llm_output_to_grading_result(self._out(accuracy_score=0.9), "raw")
        assert gr.accuracy_score == pytest.approx(0.9)

    def test_missing_elements_preserved(self):
        gr = llm_output_to_grading_result(
            self._out(missing_elements=["x", "y"]), "raw"
        )
        assert gr.missing_elements == ["x", "y"]

    def test_empty_misconception_flags_leaves_errors_unchanged(self):
        out = self._out(errors=["only error"], misconception_flags=[])
        gr = llm_output_to_grading_result(out, "raw")
        assert gr.errors == ["only error"]


# ---------------------------------------------------------------------------
# TestLLMGradingOutputSchema
# ---------------------------------------------------------------------------


class TestLLMGradingOutputSchema:
    def test_schema_is_dict(self):
        assert isinstance(LLM_GRADING_OUTPUT_SCHEMA, dict)

    def test_schema_has_required_fields(self):
        required = LLM_GRADING_OUTPUT_SCHEMA.get("required", [])
        for field in [
            "accuracy_score", "mastery_after", "missing_elements", "errors",
            "misconception_flags", "evidence_alignment_score",
            "needs_human_review", "short_feedback",
        ]:
            assert field in required

    def test_schema_type_is_object(self):
        assert LLM_GRADING_OUTPUT_SCHEMA["type"] == "object"

"""Tests for blank-answer detection in grading pipeline.

Blank answers must always score 0.0 regardless of grader type.
"""
from __future__ import annotations

import pytest

from gonghaebun.grading.schemas import GradingResult


# ---------------------------------------------------------------------------
# LLMGrader blank detection (uses MockLLMClient internally)
# ---------------------------------------------------------------------------

class TestLLMGraderBlankDetection:
    """LLMGrader.grade() must return 0.0 for blank answers without calling LLM."""

    @pytest.fixture()
    def grader(self):
        from gonghaebun.grading.factory import make_grader
        return make_grader("mock")

    def test_empty_string_scores_zero(self, grader):
        result = grader.grade("Define X", "expected", "evidence", "")
        assert result.accuracy_score == 0.0
        assert result.mastery_suggestion == "unknown"

    def test_whitespace_only_scores_zero(self, grader):
        result = grader.grade("Define X", "expected", "evidence", "   \t\n  ")
        assert result.accuracy_score == 0.0

    def test_blank_does_not_consume_call_count(self, grader):
        grader.grade("Q", "A", "E", "")
        assert grader._call_count == 0

    def test_blank_feedback_indicates_no_answer(self, grader):
        result = grader.grade("Q", "A", "E", "")
        assert "no answer" in result.feedback.lower() or "provided" in result.feedback.lower()

    def test_non_blank_proceeds_to_llm(self, grader):
        """Non-blank answer should proceed to normal grading (not 0.0)."""
        result = grader.grade("Define X", "expected", "evidence", "some answer")
        # Mock grader returns fixture value (0.75), not 0.0
        assert result.accuracy_score > 0.0

    def test_blank_needs_human_review_false(self, grader):
        result = grader.grade("Q", "A", "E", "")
        assert result.needs_human_review is False


# ---------------------------------------------------------------------------
# Standalone GradingResult for blank — used in session_service.py
# ---------------------------------------------------------------------------

class TestBlankGradingResult:
    """Verify the blank GradingResult shape is valid."""

    def test_blank_result_has_required_fields(self):
        result = GradingResult(
            accuracy_score=0.0,
            needs_human_review=False,
            feedback="No answer provided.",
            mastery_suggestion="unknown",
            raw_response="",
        )
        assert result.accuracy_score == 0.0
        assert result.mastery_suggestion == "unknown"
        assert result.missing_elements == []
        assert result.errors == []

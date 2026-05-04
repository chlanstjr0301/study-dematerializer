"""Tests for grading/llm_grader.py (MVP3 Step 3)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from gonghaebun.grading.llm_grader import LLMGrader
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.llm.errors import LLMResponseError
from gonghaebun.llm.mock import MockLLMClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_GRADING_DICT = {
    "accuracy_score": 0.75,
    "missing_elements": ["formal epsilon-delta definition"],
    "errors": [],
    "feedback": "Good intuitive understanding.",
    "mastery_suggestion": "partial",
    "confidence": 0.9,
    "needs_human_review": False,
    "evidence_alignment": "supported",
    "raw_response": "",
}


def _mock_llm(response_text: str) -> MagicMock:
    """Return a fake LLMClient whose complete() always returns response_text."""
    m = MagicMock()
    m.complete.return_value = response_text
    return m


# ---------------------------------------------------------------------------
# TestLLMGraderWithMockLLMClient
# ---------------------------------------------------------------------------


class TestLLMGraderWithMockLLMClient:
    """End-to-end: LLMGrader + real MockLLMClient + fixture file."""

    def test_grade_returns_grading_result(self):
        grader = LLMGrader(MockLLMClient())
        result = grader.grade(
            question="What is compactness?",
            expected_answer="A space is compact if every open cover has a finite subcover.",
            evidence_text="A topological space X is compact if...",
            learner_response="Compact means every open cover has a finite subcover.",
        )
        assert isinstance(result, GradingResult)

    def test_grade_accuracy_score_from_fixture(self):
        grader = LLMGrader(MockLLMClient())
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.accuracy_score == pytest.approx(0.75)

    def test_grade_mastery_suggestion_from_fixture(self):
        grader = LLMGrader(MockLLMClient())
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.mastery_suggestion == "partial"

    def test_grade_raw_response_stored(self):
        grader = LLMGrader(MockLLMClient())
        result = grader.grade("q", "ea", "ev", "lr")
        # raw_response should be the verbatim JSON string returned by the LLM
        assert isinstance(result.raw_response, str)
        assert len(result.raw_response) > 0


# ---------------------------------------------------------------------------
# TestLLMGraderRetry
# ---------------------------------------------------------------------------


class TestLLMGraderRetry:
    def test_first_call_bad_json_retries_and_succeeds(self):
        """First call returns bad JSON, second returns valid JSON."""
        valid_json = json.dumps(_VALID_GRADING_DICT)
        mock = MagicMock()
        mock.complete.side_effect = ["not valid json {{", valid_json]

        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert isinstance(result, GradingResult)
        assert mock.complete.call_count == 2

    def test_both_calls_bad_json_raises_response_error(self):
        """Both calls return bad JSON → LLMResponseError."""
        mock = _mock_llm("still not json")
        grader = LLMGrader(mock)

        with pytest.raises(LLMResponseError):
            grader.grade("q", "ea", "ev", "lr")

        assert mock.complete.call_count == 2

    def test_first_call_invalid_schema_retries(self):
        """First call returns valid JSON but with wrong schema values."""
        bad_data = {**_VALID_GRADING_DICT, "mastery_suggestion": "excellent"}
        good_data = _VALID_GRADING_DICT

        mock = MagicMock()
        mock.complete.side_effect = [
            json.dumps(bad_data),
            json.dumps(good_data),
        ]

        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.mastery_suggestion == "partial"
        assert mock.complete.call_count == 2

    def test_both_invalid_schema_raises_response_error(self):
        bad_data = {**_VALID_GRADING_DICT, "mastery_suggestion": "excellent"}
        mock = _mock_llm(json.dumps(bad_data))

        grader = LLMGrader(mock)
        with pytest.raises(LLMResponseError):
            grader.grade("q", "ea", "ev", "lr")

        assert mock.complete.call_count == 2


# ---------------------------------------------------------------------------
# TestLLMGraderMiscellaneous
# ---------------------------------------------------------------------------


class TestLLMGraderMiscellaneous:
    def test_is_answer_grader_subclass(self):
        from gonghaebun.grading.answer_grader import AnswerGrader

        assert issubclass(LLMGrader, AnswerGrader)

    def test_raw_response_set_to_actual_llm_output(self):
        valid_json = json.dumps(_VALID_GRADING_DICT)
        mock = _mock_llm(valid_json)
        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.raw_response == valid_json

    def test_empty_learner_response_still_grades(self):
        valid_json = json.dumps(_VALID_GRADING_DICT)
        mock = _mock_llm(valid_json)
        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", learner_response="")
        assert isinstance(result, GradingResult)

    def test_prompt_is_passed_to_llm(self):
        valid_json = json.dumps(_VALID_GRADING_DICT)
        mock = _mock_llm(valid_json)
        grader = LLMGrader(mock)
        grader.grade("My Question", "ea", "ev", "lr")
        call_args = mock.complete.call_args
        # The user prompt (second arg) should contain the question
        user_prompt = call_args[0][1]
        assert "My Question" in user_prompt

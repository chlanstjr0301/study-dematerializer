"""Tests for grading/llm_grader.py (MVP4-J0)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from gonghaebun.grading.llm_grader import LLMGrader
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.llm.errors import LLMError
from gonghaebun.llm.mock import MockLLMClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# New LLMGradingOutput field names (used in fixture and mock returns)
_VALID_LLM_OUTPUT_DICT = {
    "accuracy_score": 0.75,
    "mastery_after": "partial",
    "missing_elements": ["formal epsilon-delta definition"],
    "errors": [],
    "misconception_flags": [],
    "evidence_alignment_score": 0.85,
    "needs_human_review": False,
    "short_feedback": "Good intuitive understanding.",
}

_BAD_SCHEMA_DICT = {**_VALID_LLM_OUTPUT_DICT, "mastery_after": "excellent"}


def _mock_llm(response_dict: dict) -> MagicMock:
    """Return a fake LLMClient whose complete_structured() always returns response_dict."""
    m = MagicMock()
    m.complete_structured.return_value = response_dict
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
        assert isinstance(result.raw_response, str)
        assert len(result.raw_response) > 0


# ---------------------------------------------------------------------------
# TestLLMGraderRetry
# ---------------------------------------------------------------------------


class TestLLMGraderRetry:
    def test_first_call_invalid_schema_retries_and_succeeds(self):
        """First call returns bad schema dict, second returns valid dict."""
        mock = MagicMock()
        mock.complete_structured.side_effect = [_BAD_SCHEMA_DICT, _VALID_LLM_OUTPUT_DICT]

        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert isinstance(result, GradingResult)
        assert mock.complete_structured.call_count == 2

    def test_both_calls_invalid_schema_returns_fallback(self):
        """Both calls return bad schema → fallback GradingResult."""
        mock = _mock_llm(_BAD_SCHEMA_DICT)
        grader = LLMGrader(mock)

        result = grader.grade("q", "ea", "ev", "lr")
        assert result.needs_human_review is True
        assert mock.complete_structured.call_count == 2

    def test_first_call_invalid_schema_retries(self):
        """First call returns schema with bad mastery_after, second is valid."""
        mock = MagicMock()
        mock.complete_structured.side_effect = [_BAD_SCHEMA_DICT, _VALID_LLM_OUTPUT_DICT]

        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.mastery_suggestion == "partial"
        assert mock.complete_structured.call_count == 2

    def test_both_invalid_schema_returns_fallback(self):
        mock = _mock_llm(_BAD_SCHEMA_DICT)

        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.needs_human_review is True
        assert mock.complete_structured.call_count == 2


# ---------------------------------------------------------------------------
# TestLLMGraderMiscellaneous
# ---------------------------------------------------------------------------


class TestLLMGraderMiscellaneous:
    def test_is_answer_grader_subclass(self):
        from gonghaebun.grading.answer_grader import AnswerGrader

        assert issubclass(LLMGrader, AnswerGrader)

    def test_raw_response_is_json_serialized_output(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        # raw_response should be JSON serialization of the structured output dict
        assert isinstance(result.raw_response, str)
        parsed = json.loads(result.raw_response)
        assert parsed["accuracy_score"] == pytest.approx(0.75)

    def test_empty_learner_response_still_grades(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", learner_response="")
        assert isinstance(result, GradingResult)

    def test_prompt_is_passed_to_llm(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock)
        grader.grade("My Question", "ea", "ev", "lr")
        call_args = mock.complete_structured.call_args
        # The user prompt (second positional arg) should contain the question
        user_prompt = call_args[0][1]
        assert "My Question" in user_prompt


# ---------------------------------------------------------------------------
# TestLLMGraderTracing
# ---------------------------------------------------------------------------


class TestLLMGraderTracing:
    def test_traces_list_starts_empty(self):
        grader = LLMGrader(MockLLMClient())
        assert grader.traces == []

    def test_successful_grade_appends_one_trace(self):
        grader = LLMGrader(MockLLMClient())
        grader.grade("q", "ea", "ev", "lr")
        assert len(grader.traces) == 1

    def test_successful_trace_has_one_attempt(self):
        grader = LLMGrader(MockLLMClient())
        grader.grade("q", "ea", "ev", "lr")
        assert len(grader.traces[0].attempts) == 1

    def test_successful_attempt_parsed_ok_true(self):
        grader = LLMGrader(MockLLMClient())
        grader.grade("q", "ea", "ev", "lr")
        assert grader.traces[0].attempts[0].parsed_ok is True

    def test_retry_trace_has_two_attempts(self):
        """First attempt fails validation, second succeeds → 1 trace with 2 attempts."""
        mock = MagicMock()
        mock.complete_structured.side_effect = [_BAD_SCHEMA_DICT, _VALID_LLM_OUTPUT_DICT]
        grader = LLMGrader(mock)
        grader.grade("q", "ea", "ev", "lr")
        assert len(grader.traces) == 1
        assert len(grader.traces[0].attempts) == 2
        assert grader.traces[0].attempts[0].call_index == 0
        assert grader.traces[0].attempts[0].parsed_ok is False
        assert grader.traces[0].attempts[1].call_index == 1
        assert grader.traces[0].attempts[1].parsed_ok is True

    def test_two_questions_produce_two_traces(self):
        grader = LLMGrader(MockLLMClient())
        grader.grade("q1", "ea", "ev", "lr")
        grader.grade("q2", "ea", "ev", "lr")
        assert len(grader.traces) == 2

    def test_question_id_stored_from_set_context(self):
        grader = LLMGrader(MockLLMClient())
        grader._set_context("compactness", "formal", "q_my_id")
        grader.grade("q", "ea", "ev", "lr")
        assert grader.traces[0].question_id == "q_my_id"

    def test_structured_output_used_true_in_attempts(self):
        grader = LLMGrader(MockLLMClient())
        grader.grade("q", "ea", "ev", "lr")
        assert grader.traces[0].attempts[0].structured_output_used is True

    def test_concept_id_stored_from_set_context(self):
        grader = LLMGrader(MockLLMClient())
        grader._set_context("connectedness", "intuitive")
        grader.grade("q", "ea", "ev", "lr")
        assert grader.traces[0].concept_id == "connectedness"


# ---------------------------------------------------------------------------
# TestLLMGraderMaxCalls
# ---------------------------------------------------------------------------


class TestLLMGraderMaxCalls:
    def test_max_calls_zero_returns_fallback_immediately(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock, max_calls=0)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.needs_human_review is True
        assert mock.complete_structured.call_count == 0

    def test_max_calls_zero_no_trace_appended(self):
        """Immediate cap fallback (before any LLM call) doesn't add to traces."""
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock, max_calls=0)
        grader.grade("q", "ea", "ev", "lr")
        assert len(grader.traces) == 0

    def test_max_calls_one_second_grade_returns_fallback(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock, max_calls=1)
        grader.grade("q1", "ea", "ev", "lr")  # uses 1 call
        result = grader.grade("q2", "ea", "ev", "lr")  # should fallback
        assert result.needs_human_review is True
        assert mock.complete_structured.call_count == 1

    def test_max_calls_five_first_grade_succeeds(self):
        mock = _mock_llm(_VALID_LLM_OUTPUT_DICT)
        grader = LLMGrader(mock, max_calls=5)
        result = grader.grade("q", "ea", "ev", "lr")
        assert isinstance(result, GradingResult)
        assert result.needs_human_review is False


# ---------------------------------------------------------------------------
# TestLLMGraderProviderError
# ---------------------------------------------------------------------------


class TestLLMGraderProviderError:
    def test_llm_error_returns_fallback_not_raise(self):
        mock = MagicMock()
        mock.complete_structured.side_effect = LLMError("provider error")
        grader = LLMGrader(mock)
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.needs_human_review is True
        assert isinstance(result, GradingResult)

    def test_llm_error_appends_trace(self):
        mock = MagicMock()
        mock.complete_structured.side_effect = LLMError("provider error")
        grader = LLMGrader(mock)
        grader.grade("q", "ea", "ev", "lr")
        assert len(grader.traces) == 1

    def test_llm_error_attempt_has_fallback_true(self):
        mock = MagicMock()
        mock.complete_structured.side_effect = LLMError("provider error")
        grader = LLMGrader(mock)
        grader.grade("q", "ea", "ev", "lr")
        assert grader.traces[0].attempts[0].fallback is True

    def test_llm_error_only_one_call_made(self):
        """Provider errors don't retry — fall back immediately."""
        mock = MagicMock()
        mock.complete_structured.side_effect = LLMError("provider error")
        grader = LLMGrader(mock)
        grader.grade("q", "ea", "ev", "lr")
        assert mock.complete_structured.call_count == 1

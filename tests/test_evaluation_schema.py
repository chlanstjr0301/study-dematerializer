"""Tests for evaluation_schema.py — validation of self-explanation/recall output."""
from __future__ import annotations

import pytest

from gonghaebun.llm.errors import LLMResponseError
from gonghaebun.models.session_models import RecallEvaluation
from gonghaebun.pipeline.evaluation_schema import validate_evaluation_output


def _valid_data(**overrides) -> dict:
    base = {
        "accuracy_score": 0.7,
        "missing_elements": ["finite subcover condition"],
        "errors": [],
        "feedback": "Good explanation.",
    }
    base.update(overrides)
    return base


class TestValidOutput:
    def test_valid_evaluation_output(self):
        result = validate_evaluation_output(_valid_data())
        assert isinstance(result, RecallEvaluation)
        assert result.accuracy_score == 0.7
        assert result.missing_elements == ["finite subcover condition"]
        assert result.errors == []
        assert result.feedback == "Good explanation."

    def test_accuracy_score_zero(self):
        result = validate_evaluation_output(_valid_data(accuracy_score=0.0))
        assert result.accuracy_score == 0.0

    def test_accuracy_score_one(self):
        result = validate_evaluation_output(_valid_data(accuracy_score=1.0))
        assert result.accuracy_score == 1.0

    def test_feedback_empty_allowed(self):
        result = validate_evaluation_output(_valid_data(feedback=""))
        assert result.feedback == ""

    def test_empty_lists_allowed(self):
        result = validate_evaluation_output(_valid_data(missing_elements=[], errors=[]))
        assert result.missing_elements == []
        assert result.errors == []


class TestAccuracyScoreRejection:
    def test_negative_rejected(self):
        with pytest.raises(LLMResponseError, match="0.0~1.0"):
            validate_evaluation_output(_valid_data(accuracy_score=-0.1))

    def test_over_one_rejected(self):
        with pytest.raises(LLMResponseError, match="0.0~1.0"):
            validate_evaluation_output(_valid_data(accuracy_score=1.01))

    def test_not_number_rejected(self):
        with pytest.raises(LLMResponseError, match="숫자"):
            validate_evaluation_output(_valid_data(accuracy_score="high"))


class TestListFieldRejection:
    def test_missing_elements_not_list_rejected(self):
        with pytest.raises(LLMResponseError, match="missing_elements"):
            validate_evaluation_output(_valid_data(missing_elements="foo"))

    def test_errors_not_list_rejected(self):
        with pytest.raises(LLMResponseError, match="errors"):
            validate_evaluation_output(_valid_data(errors=123))

    def test_list_element_not_string_rejected(self):
        with pytest.raises(LLMResponseError, match="문자열"):
            validate_evaluation_output(_valid_data(missing_elements=[1, 2]))

    def test_errors_element_not_string_rejected(self):
        with pytest.raises(LLMResponseError, match="문자열"):
            validate_evaluation_output(_valid_data(errors=[True]))


class TestMissingField:
    def test_feedback_missing_rejected(self):
        data = _valid_data()
        del data["feedback"]
        with pytest.raises(LLMResponseError, match="feedback"):
            validate_evaluation_output(data)

    def test_accuracy_score_missing_rejected(self):
        data = _valid_data()
        del data["accuracy_score"]
        with pytest.raises(LLMResponseError, match="accuracy_score"):
            validate_evaluation_output(data)

    def test_missing_elements_missing_rejected(self):
        data = _valid_data()
        del data["missing_elements"]
        with pytest.raises(LLMResponseError, match="missing_elements"):
            validate_evaluation_output(data)


class TestExtraFields:
    def test_extra_field_rejected(self):
        data = _valid_data()
        data["unexpected_key"] = "value"
        with pytest.raises(LLMResponseError, match="허용되지 않는 필드"):
            validate_evaluation_output(data)

    def test_multiple_extra_fields_rejected(self):
        data = _valid_data()
        data["foo"] = 1
        data["bar"] = 2
        with pytest.raises(LLMResponseError, match="허용되지 않는 필드"):
            validate_evaluation_output(data)


class TestFeedbackType:
    def test_feedback_not_string_rejected(self):
        with pytest.raises(LLMResponseError, match="feedback"):
            validate_evaluation_output(_valid_data(feedback=123))

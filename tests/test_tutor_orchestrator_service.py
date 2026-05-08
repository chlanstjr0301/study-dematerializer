"""
Tests for LLM Tutor orchestrator service.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.api.services.tutor_orchestrator_service import (
    TUTOR_OUTPUT_SCHEMA,
    StudyUpdateCandidate,
    TutorResponse,
    classify_learning_task,
    tutor_respond,
)


class TestClassifyLearningTask:
    """Rule-based learning task classification."""

    def test_why_question(self):
        assert classify_learning_task("왜 compact하지 않아?") == "why_question"

    def test_proof_schema(self):
        assert classify_learning_task("증명 구조를 설명해") == "proof_schema_question"

    def test_self_explanation(self):
        assert classify_learning_task("내가 이해한 건 이거야") == "self_explanation_evaluation"

    def test_study_update_request(self):
        assert classify_learning_task("STUDY.md에 정리해줘") == "study_update_request"

    def test_definition_question(self):
        assert classify_learning_task("finite subcover가 뭐야?") == "definition_question"

    def test_comparison(self):
        assert classify_learning_task("compact와 connected의 차이") == "comparison_question"

    def test_followup(self):
        assert classify_learning_task("다시 알려줘") == "followup_clarification"

    def test_generic_fallback(self):
        assert classify_learning_task("hello world") == "followup_clarification"


class TestTutorRespondDisabled:
    """Tutor returns None when LLM is disabled."""

    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")
        result = tutor_respond("compact가 뭐야?")
        assert result is None

    def test_returns_none_when_disabled_default(self):
        """Default is LLM disabled."""
        # Don't set env var — default should be "1"
        result = tutor_respond("compact가 뭐야?")
        assert result is None


class TestTutorRespondMocked:
    """Tutor with mocked LLM client."""

    @pytest.fixture(autouse=True)
    def _enable_llm(self, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")

    def _make_mock_response(self, **overrides):
        """Build a valid tutor response dict."""
        base = {
            "direct_answer": "옹골(compact) 집합은 모든 열린 덮개가 유한 부분덮개를 가지는 집합입니다.",
            "primary_concept": "compactness",
            "supporting_concepts": ["open_cover"],
            "learning_task": "definition_question",
            "misconception_tags": [],
            "missing_elements": [],
            "study_update_candidate": None,
            "confidence": 0.85,
        }
        base.update(overrides)
        return base

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_success_returns_tutor_response(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response()
        mock_factory.return_value = mock_client

        result = tutor_respond("compactness가 뭐야?", concept_id="compactness")
        assert result is not None
        assert isinstance(result, TutorResponse)
        assert result.direct_answer != ""
        assert result.primary_concept == "compactness"
        assert result.llm_used is True
        assert result.confidence >= 0.5

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_low_confidence_returns_none(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response(
            confidence=0.2
        )
        mock_factory.return_value = mock_client

        result = tutor_respond("something vague", concept_id="compactness")
        assert result is None

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_llm_error_returns_none(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = RuntimeError("API error")
        mock_factory.return_value = mock_client

        result = tutor_respond("compactness가 뭐야?", concept_id="compactness")
        assert result is None

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_rag_used_flag(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response()
        mock_factory.return_value = mock_client

        result = tutor_respond("open cover가 뭐야?", concept_id="compactness")
        assert result is not None
        assert result.rag_used is True
        assert len(result.retrieved_context) > 0

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_misconception_tags_propagated(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response(
            misconception_tags=["closed_bounded_always"],
        )
        mock_factory.return_value = mock_client

        result = tutor_respond(
            "compact는 closed and bounded 아냐?",
            concept_id="compactness",
        )
        assert result is not None
        assert "closed_bounded_always" in result.misconception_tags

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_study_update_candidate_structure(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response(
            study_update_candidate={
                "concept_id": "compactness",
                "summary": "Heine-Borel 범위 오해",
                "evidence": ["R에서만 성립"],
                "misconception_tags": ["heine_borel_scope"],
                "next_recall_tasks": ["일반 metric space 예시"],
            },
        )
        mock_factory.return_value = mock_client

        result = tutor_respond(
            "STUDY.md에 정리해줘",
            concept_id="compactness",
            recent_messages=["R에서 compact = closed + bounded라고 배웠는데"],
        )
        assert result is not None
        assert result.study_update_candidate is not None
        assert result.study_update_candidate.concept_id == "compactness"
        assert "Heine-Borel" in result.study_update_candidate.summary

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_concept_resolved_from_message(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response()
        mock_factory.return_value = mock_client

        # No concept_id passed, but message contains "compactness"
        result = tutor_respond("compactness가 뭐야?")
        assert result is not None
        assert result.primary_concept == "compactness"

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_concept_resolved_from_recent(self, mock_factory):
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response()
        mock_factory.return_value = mock_client

        result = tutor_respond(
            "설명해봐",
            recent_messages=["compactness가 뭐야?"],
        )
        assert result is not None


class TestTutorOutputSchema:
    """Validate the JSON schema structure."""

    def test_schema_has_required_fields(self):
        required = TUTOR_OUTPUT_SCHEMA["required"]
        assert "direct_answer" in required
        assert "primary_concept" in required
        assert "confidence" in required
        assert "misconception_tags" in required
        assert "study_update_candidate" in required

    def test_schema_no_additional_properties(self):
        assert TUTOR_OUTPUT_SCHEMA["additionalProperties"] is False

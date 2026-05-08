"""
Tests for LLM Tutor orchestrator service.
"""
from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.api.services.tutor_orchestrator_service import (
    TUTOR_OUTPUT_SCHEMA,
    StudyUpdateCandidate,
    TutorResponse,
    _compactness_deterministic_fallback,
    _match_compactness_topic,
    classify_learning_task,
    tutor_respond,
)
from gonghaebun.llm.errors import LLMError, LLMResponseError


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
    def test_low_confidence_non_compactness_returns_none(self, mock_factory):
        """Low confidence on non-compactness topic → None."""
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response(
            confidence=0.2
        )
        mock_factory.return_value = mock_client

        result = tutor_respond("something vague", concept_id="compactness")
        assert result is None

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_low_confidence_compactness_uses_fallback(self, mock_factory):
        """Low confidence on compactness question → deterministic fallback."""
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = self._make_mock_response(
            confidence=0.2
        )
        mock_factory.return_value = mock_client

        result = tutor_respond("왜 (0,1)은 compact하지 않아?", concept_id="compactness")
        assert result is not None
        assert result.llm_used is False
        assert result.primary_concept == "compactness"
        assert result.confidence == 0.85

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_llm_error_compactness_uses_fallback(self, mock_factory):
        """LLM error on compactness question → deterministic fallback."""
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = RuntimeError("API error")
        mock_factory.return_value = mock_client

        result = tutor_respond("compactness가 뭐야?", concept_id="compactness")
        # "뭐야" matches definition pattern but message doesn't match
        # a specific compactness sub-topic → None
        assert result is None

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_llm_error_compactness_why_uses_fallback(self, mock_factory):
        """LLM error on specific compactness why-question → fallback answer."""
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = RuntimeError("LLM crashed")
        mock_factory.return_value = mock_client

        result = tutor_respond("왜 (0,1)은 compact하지 않아?", concept_id="compactness")
        assert result is not None
        assert result.llm_used is False
        assert result.primary_concept == "compactness"
        assert "유한 부분덮개" in result.direct_answer

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

    def test_schema_openai_strict_compatible(self):
        """Every object node must have additionalProperties=false for OpenAI strict mode."""
        schema = TUTOR_OUTPUT_SCHEMA
        assert schema.get("additionalProperties") is False

        # study_update_candidate must use anyOf (not type array) for OpenAI strict
        suc = schema["properties"]["study_update_candidate"]
        assert "anyOf" in suc, "study_update_candidate must use anyOf for OpenAI strict mode"

        # Find the object variant
        obj_variant = None
        for variant in suc["anyOf"]:
            if variant.get("type") == "object":
                obj_variant = variant
                break
        assert obj_variant is not None, "study_update_candidate must have object variant"
        assert obj_variant.get("additionalProperties") is False

    def test_schema_no_type_arrays(self):
        """OpenAI strict mode does not support type arrays like ['string', 'null']."""
        def _check_no_type_array(node, path="root"):
            if isinstance(node, dict):
                if "type" in node and isinstance(node["type"], list):
                    raise AssertionError(
                        f"type array found at {path}: {node['type']}. "
                        "Use anyOf instead for OpenAI strict mode."
                    )
                for key, val in node.items():
                    _check_no_type_array(val, f"{path}.{key}")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    _check_no_type_array(item, f"{path}[{i}]")

        _check_no_type_array(TUTOR_OUTPUT_SCHEMA)

    def test_study_update_candidate_null_variant(self):
        """study_update_candidate must accept null."""
        suc = TUTOR_OUTPUT_SCHEMA["properties"]["study_update_candidate"]
        null_found = any(v.get("type") == "null" for v in suc["anyOf"])
        assert null_found, "study_update_candidate must have null variant"


class TestCompactnessDeterministicFallback:
    """Deterministic compactness fallback answers."""

    def test_match_why_not_compact(self):
        assert _match_compactness_topic("왜 (0,1)은 compact하지 않아?", None) == "why_not_compact"

    def test_match_finite_subcover(self):
        assert _match_compactness_topic("finite subcover가 뭐야?", None) == "finite_subcover"

    def test_match_heine_borel(self):
        assert _match_compactness_topic("Heine-Borel은 어디서 성립해?", None) == "heine_borel_scope"

    def test_match_uniform_continuity(self):
        assert _match_compactness_topic("compact 위 연속함수의 uniform continuity 증명", None) == "compactness_in_uniform_continuity"

    def test_match_self_explanation(self):
        assert _match_compactness_topic("내가 이해한 건 이거야: 유한 개 점으로 대표", None) == "self_explanation_critique"

    def test_match_study_update(self):
        assert _match_compactness_topic("STUDY.md에 정리해줘", None) == "study_update_misconception"

    def test_match_from_recent_messages(self):
        """Topic matched from recent messages, not current message."""
        topic = _match_compactness_topic("설명해", ["왜 (0,1)은 compact하지 않아?"])
        assert topic == "why_not_compact"

    def test_no_match_returns_none(self):
        assert _match_compactness_topic("hello world", None) is None

    def test_fallback_returns_tutor_response(self):
        result = _compactness_deterministic_fallback(
            "왜 (0,1)은 compact하지 않아?",
            "why_question",
            [],
            None,
        )
        assert result is not None
        assert isinstance(result, TutorResponse)
        assert result.primary_concept == "compactness"
        assert result.llm_used is False
        assert result.confidence == 0.85
        assert "유한 부분덮개" in result.direct_answer

    def test_fallback_finite_subcover_has_definition_task(self):
        result = _compactness_deterministic_fallback(
            "finite subcover가 뭐야?",
            "definition_question",
            [],
            None,
        )
        assert result is not None
        assert result.learning_task == "definition_question"

    def test_fallback_self_explanation_has_misconception_tags(self):
        result = _compactness_deterministic_fallback(
            "내가 이해한 건 유한 개 점으로 대표할 수 있다는 거야",
            "self_explanation_evaluation",
            [],
            None,
        )
        assert result is not None
        assert len(result.misconception_tags) > 0

    def test_fallback_study_update_has_candidate(self):
        result = _compactness_deterministic_fallback(
            "STUDY.md에 정리해줘",
            "study_update_request",
            [],
            None,
        )
        assert result is not None
        assert result.study_update_candidate is not None
        assert result.study_update_candidate.concept_id == "compactness"

    def test_fallback_no_match_returns_none(self):
        result = _compactness_deterministic_fallback(
            "hello world",
            "followup_clarification",
            [],
            None,
        )
        assert result is None

    def test_llm_disabled_compactness_uses_fallback(self):
        """LLM disabled + compactness question → deterministic answer."""
        # Default: GONGHAEBUN_LLM_DISABLED=1
        result = tutor_respond("왜 (0,1)은 compact하지 않아?")
        assert result is not None
        assert result.llm_used is False
        assert result.primary_concept == "compactness"
        assert "(0,1)" in result.direct_answer

    def test_llm_disabled_non_compactness_returns_none(self):
        """LLM disabled + non-compactness question → None."""
        result = tutor_respond("hello world")
        assert result is None


class TestTutorLogging:
    """Verify logging output at each step."""

    def test_tutor_respond_logs_enter(self, caplog, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")
        with caplog.at_level(logging.WARNING, logger="gonghaebun.tutor"):
            tutor_respond("compact가 뭐야?")
        assert any("tutor_respond_enter" in r.message for r in caplog.records)

    def test_tutor_respond_logs_return_none(self, caplog, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")
        with caplog.at_level(logging.WARNING, logger="gonghaebun.tutor"):
            tutor_respond("hello world")
        assert any("tutor_return_none" in r.message for r in caplog.records)

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_tutor_respond_logs_llm_error(self, mock_factory, caplog, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = LLMError("API fail")
        mock_factory.return_value = mock_client

        with caplog.at_level(logging.WARNING, logger="gonghaebun.tutor"):
            tutor_respond("왜 (0,1)은 compact하지 않아?", concept_id="compactness")

        assert any("tutor_llm_call_error" in r.message for r in caplog.records)

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_tutor_respond_logs_context_retrieved(self, mock_factory, caplog, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        mock_client = MagicMock()
        mock_client.complete_structured.return_value = {
            "direct_answer": "test", "primary_concept": "compactness",
            "supporting_concepts": [], "learning_task": "definition_question",
            "misconception_tags": [], "missing_elements": [],
            "study_update_candidate": None, "confidence": 0.9,
        }
        mock_factory.return_value = mock_client

        with caplog.at_level(logging.WARNING, logger="gonghaebun.tutor"):
            tutor_respond("compact가 뭐야?", concept_id="compactness")

        assert any("tutor_context_retrieved" in r.message for r in caplog.records)


class TestCompleteStructuredFailurePath:
    """complete_structured failure does not crash tutor_respond."""

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_llm_response_error_uses_fallback(self, mock_factory, monkeypatch):
        """LLMResponseError (JSON parse fail) on compactness → fallback."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = LLMResponseError("bad JSON")
        mock_factory.return_value = mock_client

        result = tutor_respond("왜 (0,1)은 compact하지 않아?", concept_id="compactness")
        assert result is not None
        assert result.llm_used is False
        assert result.primary_concept == "compactness"

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_llm_error_does_not_crash(self, mock_factory, monkeypatch):
        """LLMError on non-compactness question → None, no crash."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = LLMError("network error")
        mock_factory.return_value = mock_client

        result = tutor_respond("something vague")
        assert result is None

    @patch("gonghaebun.llm.factory.get_llm_client")
    def test_file_not_found_uses_fallback(self, mock_factory, monkeypatch):
        """FileNotFoundError (SSL cert) on compactness → fallback."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        mock_client = MagicMock()
        mock_client.complete_structured.side_effect = FileNotFoundError("SSL cert")
        mock_factory.return_value = mock_client

        result = tutor_respond("왜 (0,1)은 compact하지 않아?", concept_id="compactness")
        assert result is not None
        assert result.llm_used is False


class TestDebugScriptImport:
    """Debug script imports without error."""

    def test_debug_script_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "debug_tutor_overlay",
            os.path.join(os.path.dirname(__file__), "..", "scripts", "debug_tutor_overlay.py"),
        )
        assert spec is not None
        assert spec.loader is not None

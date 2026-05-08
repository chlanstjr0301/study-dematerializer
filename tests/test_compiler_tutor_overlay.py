"""
Integration tests for the tutor overlay in compiler_analyzer_service.

Verifies that:
1. Question-like messages attempt tutor overlay
2. Greetings skip tutor
3. Bare alias (concept_lookup) skips tutor
4. Tutor failure falls back to deterministic
5. Successful tutor returns render_mode="bubble" with enriched fields
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.api.services.compiler_analyzer_service import analyze_message


def _mock_tutor_response(**overrides):
    """Build a mock TutorResponse-like object."""
    from apps.api.services.tutor_orchestrator_service import TutorResponse, StudyUpdateCandidate

    defaults = dict(
        direct_answer="옹골 집합의 정의는...",
        primary_concept="compactness",
        supporting_concepts=["open_cover"],
        learning_task="definition_question",
        misconception_tags=[],
        missing_elements=[],
        study_update_candidate=None,
        confidence=0.85,
        retrieved_context=[{"source_id": "card:compactness:definition", "title": "정의", "text": "...", "score": 0.9, "source_type": "ground_truth_card"}],
        llm_used=True,
        rag_used=True,
    )
    defaults.update(overrides)
    return TutorResponse(**defaults)


class TestTutorOverlayTrigger:
    """Tutor overlay triggers for question-like messages."""

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_question_triggers_tutor(self, mock_tutor, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response()

        result = analyze_message("compactness가 뭐야?")
        mock_tutor.assert_called_once()
        assert result["render_mode"] == "bubble"
        assert result["llm_used"] is True
        assert result["direct_answer"] == "옹골 집합의 정의는..."

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_why_question_triggers_tutor(self, mock_tutor, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response(
            learning_task="why_question",
            direct_answer="bounded만으로는 compact하지 않습니다.",
        )

        result = analyze_message("왜 (0,1)은 compact하지 않아?")
        assert result["render_mode"] == "bubble"
        assert result["learning_task"] == "why_question"

    def test_greeting_skips_tutor(self):
        """Greetings should NOT trigger tutor."""
        result = analyze_message("안녕")
        assert result["intent"] == "greeting"
        assert result.get("llm_used", False) is False

    def test_bare_alias_uses_deterministic_when_tutor_disabled(self):
        """With LLM disabled, bare alias goes to deterministic concept_lookup."""
        result = analyze_message("옹골성")
        assert result["intent"] == "concept_lookup"
        assert result["render_mode"] == "card"
        assert result.get("llm_used", False) is False


class TestTutorOverlayFallback:
    """Tutor failures fall back to deterministic flow."""

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_tutor_none_falls_back(self, mock_tutor):
        """When tutor returns None, deterministic flow handles it."""
        mock_tutor.return_value = None

        result = analyze_message("compactness가 뭐야?")
        # Should still work via deterministic path
        assert result["concept_id"] == "compactness"
        # Deterministic definition answer
        assert result["intent"] == "definition_question"

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_tutor_exception_falls_back(self, mock_tutor):
        """When tutor raises, deterministic flow handles it."""
        mock_tutor.side_effect = RuntimeError("LLM crashed")

        result = analyze_message("compactness 설명해줘")
        # Should not crash — falls back
        assert result["concept_id"] == "compactness"

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_low_confidence_falls_back(self, mock_tutor):
        """Tutor with confidence < 0.5 should fall back."""
        mock_tutor.return_value = _mock_tutor_response(confidence=0.3)

        result = analyze_message("compactness가 뭐야?")
        # Tutor returned low confidence → analyzer ignores it
        # Falls to deterministic path
        assert result["concept_id"] == "compactness"


class TestTutorResponseFields:
    """Verify enriched response fields when tutor succeeds."""

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_has_rag_used(self, mock_tutor, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response()

        result = analyze_message("compactness가 뭐야?")
        assert result["rag_used"] is True

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_has_retrieved_context(self, mock_tutor, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response()

        result = analyze_message("open cover가 뭐야?")
        assert result["retrieved_context"] is not None
        assert len(result["retrieved_context"]) > 0

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_has_misconception_tags(self, mock_tutor, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response(
            misconception_tags=["closed_bounded_always"],
        )

        result = analyze_message("compact는 closed + bounded 아닌가?")
        assert result["misconception_tags"] == ["closed_bounded_always"]

    @patch("apps.api.services.tutor_orchestrator_service.tutor_respond")
    def test_has_study_update_candidate(self, mock_tutor, monkeypatch):
        from apps.api.services.tutor_orchestrator_service import StudyUpdateCandidate
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        mock_tutor.return_value = _mock_tutor_response(
            study_update_candidate=StudyUpdateCandidate(
                concept_id="compactness",
                summary="Heine-Borel scope misconception",
                evidence=["only in R^n"],
                misconception_tags=["heine_borel_scope"],
                next_recall_tasks=["general metric space example"],
            ),
        )

        result = analyze_message("STUDY.md에 정리해줘")
        assert result["study_update_candidate"] is not None
        assert result["study_update_candidate"]["concept_id"] == "compactness"


class TestCompactnessFallbackInAnalyzer:
    """Compactness fallback answers surface through analyze_message."""

    def test_why_not_compact_returns_bubble_not_open_set(self):
        """(0,1) compact question must NOT misroute to open_set card."""
        result = analyze_message("왜 (0,1)은 compact하지 않아?")
        # Must NOT return open_set — this was the original bug
        assert result.get("concept_id") != "open_set"
        # Should get a direct answer about compactness
        assert result["direct_answer"] is not None

    def test_demo_question_returns_bubble(self):
        """Full demo question returns bubble render mode, not card."""
        result = analyze_message(
            "그럼 (0,1)은 bounded인데 왜 compact하지 않다고 하는 거야? "
            "open cover 관점에서 설명해줘"
        )
        assert result.get("concept_id") != "open_set"
        assert result["render_mode"] == "bubble"
        assert result["intent"] == "tutor_response"
        assert result["direct_answer"] is not None
        assert "유한 부분덮개" in result["direct_answer"]

    def test_finite_subcover_returns_answer(self):
        """finite subcover question gets deterministic answer."""
        result = analyze_message("finite subcover가 뭐야?")
        assert result["direct_answer"] is not None
        assert "유한" in result["direct_answer"]

    def test_heine_borel_returns_answer(self):
        """Heine-Borel scope question gets deterministic answer."""
        result = analyze_message("closed and bounded이면 compact 아니야?")
        assert result["direct_answer"] is not None


class TestAnalyzerLogging:
    """Verify analyzer emits structured logs."""

    def test_logs_compiler_analyze_received(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="gonghaebun.compiler.analyzer"):
            analyze_message("옹골성")
        assert any("compiler_analyze_received" in r.message for r in caplog.records)

    def test_logs_tutor_overlay_check(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="gonghaebun.compiler.analyzer"):
            analyze_message("compact가 뭐야?")
        assert any("tutor_overlay_check" in r.message for r in caplog.records)


class TestBackwardCompatibility:
    """Existing behavior preserved when tutor is disabled."""

    def test_concept_lookup_fields_unchanged(self):
        """Plain concept lookup still returns all expected fields."""
        result = analyze_message("옹골성")
        assert result["language"] == "ko"
        assert result["concept_id"] == "compactness"
        assert result["representations"] is not None
        assert result["prerequisite_checks"] is not None
        assert result["recommended_actions"] is not None
        assert result["intent"] == "concept_lookup"
        assert result["render_mode"] == "card"

    def test_definition_question_still_works(self):
        """Definition question still returns direct_answer via deterministic path."""
        result = analyze_message("옹골성이 뭐야?")
        assert result["intent"] == "definition_question"
        assert result["direct_answer"] is not None

"""
Tests for MVP6-0B: Structured evaluation output integration.

Verifies:
- complete_structured is called (not complete_json) for self-explain and recall
- Invalid LLM responses → 502 (not 500)
- LLM failures do not pollute session state
- Existing 400/404/409 errors are not overridden
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from gonghaebun.llm.errors import LLMError, LLMResponseError

client = TestClient(app)


@pytest.fixture()
def study_env(tmp_path: Path, monkeypatch):
    """Isolated environment with source file for full pipeline tests."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    bank_root = tmp_path / "banks"
    bank_root.mkdir()
    study_md = tmp_path / "STUDY.md"
    study_md.write_text("# Study Progress\n", encoding="utf-8")
    data_root = tmp_path

    sample_source = Path("tests/data/sample_source.md")
    (sources_dir / "test_source.md").write_text(
        sample_source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    import apps.api.services.study_session_service as svc_mod
    monkeypatch.setattr(svc_mod.config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(svc_mod.config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(svc_mod.config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(svc_mod.config, "STUDY_MD", study_md)
    monkeypatch.setattr(svc_mod.config, "DATA_ROOT", data_root)
    monkeypatch.setenv("GONGHAEBUN_FIXTURE_DIR", str(Path("tests/fixtures").resolve()))

    return {
        "runs_dir": runs_dir,
        "sources_dir": sources_dir,
        "bank_root": bank_root,
        "study_md": study_md,
        "data_root": data_root,
    }


def _create_and_advance_to_representations(study_env) -> str:
    """Create session, diagnose, advance to step 3 (representations)."""
    resp = client.post("/api/study-session", json={"concept_id": "compactness"})
    assert resp.status_code == 201
    sid = resp.json()["session_id"]

    client.post(f"/api/study-session/{sid}/diagnose", json={
        "prior_knowledge": "열린 덮개",
        "gap_description": "유한 부분 덮개 모르겠어",
    })
    client.post(f"/api/study-session/{sid}/advance", json={"completed_step": "prerequisites"})
    return sid


def _create_and_advance_to_recall(study_env) -> str:
    """Create session, advance through all steps to reach recall (step 5)."""
    sid = _create_and_advance_to_representations(study_env)
    client.post(f"/api/study-session/{sid}/advance", json={"completed_step": "representations"})
    client.post(f"/api/study-session/{sid}/advance", json={"completed_step": "misconceptions"})
    return sid


# ---------------------------------------------------------------------------
# Test: complete_structured is used
# ---------------------------------------------------------------------------


class TestStructuredOutputCalled:
    def test_self_explain_uses_complete_structured(self, study_env, monkeypatch):
        """Self-explain calls complete_structured, not complete_json."""
        sid = _create_and_advance_to_representations(study_env)

        calls = {"structured": 0, "json": 0}
        from gonghaebun.llm.mock import MockLLMClient
        original_structured = MockLLMClient.complete_structured
        original_json = MockLLMClient.complete_json

        def track_structured(self, system, user, schema):
            calls["structured"] += 1
            return original_structured(self, system, user, schema)

        def track_json(self, system, user):
            calls["json"] += 1
            return original_json(self, system, user)

        monkeypatch.setattr(MockLLMClient, "complete_structured", track_structured)
        monkeypatch.setattr(MockLLMClient, "complete_json", track_json)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "Compactness means every open cover has a finite subcover.",
        })
        assert resp.status_code == 200
        # complete_structured should have been called (which internally calls complete_json in mock)
        assert calls["structured"] >= 1

    def test_recall_uses_complete_structured(self, study_env, monkeypatch):
        """Recall calls complete_structured, not complete_json directly."""
        sid = _create_and_advance_to_recall(study_env)

        calls = {"structured": 0}
        from gonghaebun.llm.mock import MockLLMClient
        original_structured = MockLLMClient.complete_structured

        def track_structured(self, system, user, schema):
            calls["structured"] += 1
            return original_structured(self, system, user, schema)

        monkeypatch.setattr(MockLLMClient, "complete_structured", track_structured)

        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "Compactness means every open cover has a finite subcover...",
        })
        assert resp.status_code == 200
        assert calls["structured"] >= 1


# ---------------------------------------------------------------------------
# Test: Invalid LLM response → 502
# ---------------------------------------------------------------------------


class TestInvalidResponseReturns502:
    def test_self_explain_invalid_score_returns_502(self, study_env, monkeypatch):
        """accuracy_score=2.0 → validation failure → 502."""
        sid = _create_and_advance_to_representations(study_env)

        from gonghaebun.llm.mock import MockLLMClient

        def bad_structured(self, system, user, schema):
            return {
                "accuracy_score": 2.0,  # out of range
                "missing_elements": [],
                "errors": [],
                "feedback": "bad",
            }

        monkeypatch.setattr(MockLLMClient, "complete_structured", bad_structured)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "test explanation",
        })
        assert resp.status_code == 502
        assert "유효하지 않습니다" in resp.json()["detail"]

    def test_recall_invalid_score_returns_502(self, study_env, monkeypatch):
        """accuracy_score=-0.5 → validation failure → 502."""
        sid = _create_and_advance_to_recall(study_env)

        from gonghaebun.llm.mock import MockLLMClient

        def bad_structured(self, system, user, schema):
            return {
                "accuracy_score": -0.5,
                "missing_elements": [],
                "errors": [],
                "feedback": "bad",
            }

        monkeypatch.setattr(MockLLMClient, "complete_structured", bad_structured)

        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "test recall",
        })
        assert resp.status_code == 502

    def test_self_explain_llm_error_returns_502(self, study_env, monkeypatch):
        """LLMError (provider failure) → 502."""
        sid = _create_and_advance_to_representations(study_env)

        from gonghaebun.llm.mock import MockLLMClient

        def raise_llm_error(self, system, user, schema):
            raise LLMError("OpenAI API error: 503 Service Unavailable")

        monkeypatch.setattr(MockLLMClient, "complete_structured", raise_llm_error)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "A compact set has every open cover with a finite subcover",
        })
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Test: State pollution prevention
# ---------------------------------------------------------------------------


class TestStatePollutionPrevention:
    def test_self_explain_failure_does_not_pollute_state(self, study_env, monkeypatch):
        """If LLM eval fails, self_explanations should NOT contain the failed type."""
        sid = _create_and_advance_to_representations(study_env)

        from gonghaebun.llm.mock import MockLLMClient

        def raise_error(self, system, user, schema):
            raise LLMResponseError("malformed response")

        monkeypatch.setattr(MockLLMClient, "complete_structured", raise_error)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "A compact set has every open cover with a finite subcover",
        })
        assert resp.status_code == 502

        # Verify state is not polluted
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["self_explanations"] is None or "formal" not in (state["self_explanations"] or {})

    def test_recall_failure_does_not_pollute_state(self, study_env, monkeypatch):
        """If LLM eval fails, recall_completed should remain False."""
        sid = _create_and_advance_to_recall(study_env)

        from gonghaebun.llm.mock import MockLLMClient

        def raise_error(self, system, user, schema):
            raise LLMResponseError("malformed response")

        monkeypatch.setattr(MockLLMClient, "complete_structured", raise_error)

        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "test recall",
        })
        assert resp.status_code == 502

        # Verify state is not polluted
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["recall_completed"] is False
        assert state.get("recall_evaluation") is None


# ---------------------------------------------------------------------------
# Test: Existing error codes are not overridden
# ---------------------------------------------------------------------------


class TestExistingErrorCodesPreserved:
    def test_self_explain_invalid_rep_type_still_400(self, study_env):
        """ValueError from invalid rep type → 400 (not 502)."""
        sid = _create_and_advance_to_representations(study_env)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "invalid_type",
            "learner_explanation": "A compact set has every open cover with a finite subcover",
        })
        assert resp.status_code == 400

    def test_self_explain_empty_explanation_still_400(self, study_env):
        """ValueError from empty explanation → 400."""
        sid = _create_and_advance_to_representations(study_env)

        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "   ",
        })
        assert resp.status_code == 400

    def test_recall_empty_response_still_400(self, study_env):
        """ValueError from empty response → 400."""
        sid = _create_and_advance_to_recall(study_env)

        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "  ",
        })
        assert resp.status_code == 400

    def test_self_explain_session_not_found_still_404(self, study_env):
        """FileNotFoundError → 404."""
        resp = client.post("/api/study-session/nonexistent-id/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "A compact set has every open cover with a finite subcover",
        })
        assert resp.status_code == 404

    def test_recall_session_not_found_still_404(self, study_env):
        """FileNotFoundError → 404."""
        resp = client.post("/api/study-session/nonexistent-id/recall", json={
            "learner_response": "test",
        })
        assert resp.status_code == 404

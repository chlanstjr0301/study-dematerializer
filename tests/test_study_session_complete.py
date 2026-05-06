"""
Tests for MVP5-4A: Study Session Completion Loop.

Covers POST /api/study-session/{id}/self-explain, /recall, /complete.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

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


def _create_session(study_env) -> str:
    """Create a session and return session_id."""
    resp = client.post("/api/study-session", json={"concept_id": "compactness"})
    assert resp.status_code == 201
    return resp.json()["session_id"]


def _diagnose(session_id: str) -> None:
    """Submit diagnosis to advance to step 2."""
    resp = client.post(f"/api/study-session/{session_id}/diagnose", json={
        "prior_knowledge": "열린 덮개 알아",
        "gap_description": "유한 부분 덮개 모르겠어",
    })
    assert resp.status_code == 200


def _advance_to_recall(session_id: str) -> None:
    """Advance through prerequisites → representations → misconceptions to reach recall step."""
    for step in ["prerequisites", "representations", "misconceptions"]:
        resp = client.post(f"/api/study-session/{session_id}/advance", json={
            "completed_step": step,
        })
        assert resp.status_code == 200


def _submit_required_self_explanations(session_id: str) -> None:
    """Submit formal + proof_schema self-explanations (minimum required)."""
    for rep_type in ["formal", "proof_schema"]:
        resp = client.post(f"/api/study-session/{session_id}/self-explain", json={
            "representation_type": rep_type,
            "learner_explanation": f"My explanation of {rep_type} for compactness...",
        })
        assert resp.status_code == 200


def _submit_recall(session_id: str) -> None:
    """Submit recall response."""
    resp = client.post(f"/api/study-session/{session_id}/recall", json={
        "learner_response": "Compactness means every open cover has a finite subcover...",
    })
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Self-Explain Tests
# ---------------------------------------------------------------------------


class TestSelfExplain:
    def test_valid_submission_returns_evaluation(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "A set is compact if every open cover has a finite subcover.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["representation_type"] == "formal"
        assert 0.0 <= data["accuracy_score"] <= 1.0
        assert isinstance(data["missing_elements"], list)
        assert isinstance(data["errors"], list)
        assert isinstance(data["feedback"], str)

    def test_invalid_representation_type_400(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "invalid_type",
            "learner_explanation": "test",
        })
        assert resp.status_code == 400
        assert "유효하지 않은 표현 유형입니다" in resp.json()["detail"]

    def test_empty_explanation_400(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "   ",
        })
        assert resp.status_code == 400
        assert "자기 설명을 입력해 주세요" in resp.json()["detail"]

    def test_session_not_found_404(self, study_env):
        resp = client.post("/api/study-session/nonexistent-id/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "test",
        })
        assert resp.status_code == 404

    def test_completed_session_rejects_409(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        # Complete the session
        client.post(f"/api/study-session/{sid}/complete")
        # Now try self-explain
        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "intuitive",
            "learner_explanation": "test",
        })
        assert resp.status_code == 409
        assert "이미 완료된 세션입니다" in resp.json()["detail"]

    def test_multiple_submissions_same_rep_overwrites(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        # Submit twice for formal
        client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "first attempt",
        })
        resp = client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "second attempt",
        })
        assert resp.status_code == 200
        # Verify state has second attempt
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["self_explanations"]["formal"]["learner_explanation"] == "second attempt"

    def test_stores_in_state_self_explanations(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "My explanation",
        })
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert "formal" in state["self_explanations"]
        assert state["self_explanations"]["formal"]["accuracy_score"] == 0.6


# ---------------------------------------------------------------------------
# Recall Tests
# ---------------------------------------------------------------------------


class TestRecall:
    def test_valid_submission_returns_evaluation(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _advance_to_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "Compactness is when every open cover has a finite subcover.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert 0.0 <= data["accuracy_score"] <= 1.0
        assert isinstance(data["missing_elements"], list)
        assert isinstance(data["errors"], list)
        assert isinstance(data["feedback"], str)

    def test_empty_response_400(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "   ",
        })
        assert resp.status_code == 400
        assert "인출 응답을 입력해 주세요" in resp.json()["detail"]

    def test_session_not_found_404(self, study_env):
        resp = client.post("/api/study-session/nonexistent-id/recall", json={
            "learner_response": "test",
        })
        assert resp.status_code == 404

    def test_completed_session_rejects_409(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        client.post(f"/api/study-session/{sid}/complete")
        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "test",
        })
        assert resp.status_code == 409

    def test_sets_recall_completed_true(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_recall(sid)
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["recall_completed"] is True

    def test_resubmit_overwrites_previous(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "first attempt",
        })
        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "second attempt with more detail",
        })
        assert resp.status_code == 200
        # State should show recall_completed still true
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["recall_completed"] is True


# ---------------------------------------------------------------------------
# Complete Tests
# ---------------------------------------------------------------------------


class TestComplete:
    def test_success_returns_mastery_updates(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True
        assert len(data["mastery_updates"]) >= 2
        # Check mastery update structure
        for mu in data["mastery_updates"]:
            assert "representation_type" in mu
            assert "before" in mu
            assert "after" in mu
            assert "accuracy_score" in mu

    def test_recall_not_completed_400(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        # Do NOT submit recall
        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 400
        assert "인출 연습을 먼저 완료해야 합니다" in resp.json()["detail"]

    def test_insufficient_self_explanations_400(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        # Submit only formal (missing proof_schema)
        client.post(f"/api/study-session/{sid}/self-explain", json={
            "representation_type": "formal",
            "learner_explanation": "test",
        })
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 400
        assert "최소 formal, proof_schema 자기 설명을 완료해야 합니다" in resp.json()["detail"]

    def test_idempotent_returns_existing_result(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp1 = client.post(f"/api/study-session/{sid}/complete")
        resp2 = client.post(f"/api/study-session/{sid}/complete")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["session_id"] == resp2.json()["session_id"]
        assert resp2.json()["completed"] is True

    def test_study_md_updated_true(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/complete")
        data = resp.json()
        assert data["study_md_updated"] is True
        # Verify STUDY.md was actually modified
        content = study_env["study_md"].read_text(encoding="utf-8")
        assert "compactness" in content

    def test_study_patch_written(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        client.post(f"/api/study-session/{sid}/complete")
        patch_path = study_env["runs_dir"] / sid / "STUDY.patch.md"
        assert patch_path.exists()
        content = patch_path.read_text(encoding="utf-8")
        assert "Session" in content

    def test_next_review_date_computed(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/complete")
        data = resp.json()
        # next_review_date should be a valid date string
        assert len(data["next_review_date"]) == 10  # YYYY-MM-DD
        assert "-" in data["next_review_date"]

    def test_completed_true_in_state(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        client.post(f"/api/study-session/{sid}/complete")
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["completed"] is True
        assert state["completed_at"] is not None

    def test_session_not_found_404(self, study_env):
        resp = client.post("/api/study-session/nonexistent-id/complete")
        assert resp.status_code == 404

    def test_completion_summary_in_korean(self, study_env):
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)
        resp = client.post(f"/api/study-session/{sid}/complete")
        data = resp.json()
        assert "완료" in data["completion_summary"]

    def test_apply_patch_failure_keeps_completed_false(self, study_env, monkeypatch):
        """If apply_patch raises, session must NOT be marked completed."""
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)

        # Make apply_patch fail
        from gonghaebun.study_md import writer
        monkeypatch.setattr(writer, "apply_patch", lambda *a, **kw: (_ for _ in ()).throw(ValueError("mock failure")))

        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 500
        assert "STUDY.md 업데이트에 실패했습니다" in resp.json()["detail"]

        # Verify state remains completed=false
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["completed"] is False

    def test_apply_patch_failure_completed_at_is_null(self, study_env, monkeypatch):
        """If apply_patch raises, completed_at must remain null."""
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)

        from gonghaebun.study_md import writer
        monkeypatch.setattr(writer, "apply_patch", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("disk full")))

        client.post(f"/api/study-session/{sid}/complete")

        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["completed_at"] is None

    def test_apply_patch_failure_returns_500(self, study_env, monkeypatch):
        """apply_patch failure must return HTTP 500 with clear error message."""
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)

        from gonghaebun.study_md import writer
        monkeypatch.setattr(writer, "apply_patch", lambda *a, **kw: (_ for _ in ()).throw(ValueError("validation failed")))

        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert "STUDY.md 업데이트에 실패했습니다" in detail

    def test_failed_complete_is_not_idempotent_success(self, study_env, monkeypatch):
        """A failed complete (completed=false) must NOT return success on retry."""
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)

        from gonghaebun.study_md import writer
        original_apply = writer.apply_patch

        # First call: fail
        monkeypatch.setattr(writer, "apply_patch", lambda *a, **kw: (_ for _ in ()).throw(ValueError("fail")))
        resp1 = client.post(f"/api/study-session/{sid}/complete")
        assert resp1.status_code == 500

        # Second call: restore real apply_patch → should succeed now
        monkeypatch.setattr(writer, "apply_patch", original_apply)
        resp2 = client.post(f"/api/study-session/{sid}/complete")
        assert resp2.status_code == 200
        assert resp2.json()["completed"] is True

    def test_idempotent_only_after_successful_complete(self, study_env):
        """Idempotent behavior only applies to already-completed sessions."""
        sid = _create_session(study_env)
        _diagnose(sid)
        _submit_required_self_explanations(sid)
        _advance_to_recall(sid)
        _submit_recall(sid)

        # First complete succeeds
        resp1 = client.post(f"/api/study-session/{sid}/complete")
        assert resp1.status_code == 200
        assert resp1.json()["completed"] is True

        # Second complete is idempotent
        resp2 = client.post(f"/api/study-session/{sid}/complete")
        assert resp2.status_code == 200
        assert resp2.json()["completed"] is True
        assert resp2.json()["session_id"] == resp1.json()["session_id"]


# ---------------------------------------------------------------------------
# Full Flow Integration Test
# ---------------------------------------------------------------------------


class TestFullFlow:
    def test_complete_study_session_flow(self, study_env):
        """End-to-end: create → diagnose → self-explain → advance → recall → complete."""
        # 1. Create session
        sid = _create_session(study_env)

        # 2. Diagnose
        _diagnose(sid)

        # 3. Self-explain (all 5 representations)
        for rep_type in ["formal", "intuitive", "visual", "counterexample", "proof_schema"]:
            resp = client.post(f"/api/study-session/{sid}/self-explain", json={
                "representation_type": rep_type,
                "learner_explanation": f"Explanation of {rep_type}...",
            })
            assert resp.status_code == 200

        # 4. Advance through steps
        _advance_to_recall(sid)

        # 5. Submit recall
        resp = client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "Full recall of compactness...",
        })
        assert resp.status_code == 200
        recall_data = resp.json()
        assert recall_data["accuracy_score"] == 0.68

        # 6. Complete
        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True
        assert len(data["mastery_updates"]) == 5
        assert data["study_md_updated"] is True
        assert data["next_review_date"]
        assert data["completion_summary"]

        # 7. Verify final state
        state_resp = client.get(f"/api/study-session/{sid}")
        state = state_resp.json()
        assert state["completed"] is True
        assert state["recall_completed"] is True
        assert len(state["self_explanations"]) == 5

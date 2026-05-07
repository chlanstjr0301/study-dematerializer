"""API integration tests for Study Session endpoints (MVP5-2)."""
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

    # Copy test source
    sample_source = Path("tests/data/sample_source.md")
    (sources_dir / "test_source.md").write_text(
        sample_source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Monkeypatch config
    import apps.api.services.study_session_service as svc_mod
    monkeypatch.setattr(svc_mod.config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(svc_mod.config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(svc_mod.config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(svc_mod.config, "STUDY_MD", study_md)
    monkeypatch.setattr(svc_mod.config, "DATA_ROOT", data_root)

    # Ensure MockLLMClient finds fixtures
    monkeypatch.setenv("GONGHAEBUN_FIXTURE_DIR", str(Path("tests/fixtures").resolve()))

    return {
        "runs_dir": runs_dir,
        "sources_dir": sources_dir,
        "bank_root": bank_root,
        "study_md": study_md,
        "data_root": data_root,
    }


def _create_session(study_env) -> dict:
    """Helper to create a session and return response JSON."""
    resp = client.post("/api/study-session", json={"concept_id": "compactness"})
    assert resp.status_code == 201
    return resp.json()


def _submit_all_mapping_tasks(session_id: str) -> None:
    """Submit all 3 mapping tasks with minimal responses."""
    tasks_resp = client.get(f"/api/study-session/{session_id}/mapping-tasks")
    assert tasks_resp.status_code == 200
    for task in tasks_resp.json()["tasks"]:
        resp = client.post(f"/api/study-session/{session_id}/mapping-submit", json={
            "task_id": task["task_id"],
            "learner_response": "테스트 응답입니다.",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestCreateStudySession
# ---------------------------------------------------------------------------


class TestCreateStudySession:
    def test_returns_201_with_valid_concept(self, study_env):
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        assert resp.status_code == 201

    def test_response_has_session_id_and_representations(self, study_env):
        data = _create_session(study_env)
        assert "session_id" in data
        assert data["session_id"]
        assert "representations" in data
        assert isinstance(data["representations"], dict)

    def test_response_has_prerequisites_and_misconceptions(self, study_env):
        data = _create_session(study_env)
        assert "prerequisites" in data
        assert isinstance(data["prerequisites"], list)
        assert "misconceptions" in data
        assert isinstance(data["misconceptions"], list)

    def test_response_fields_complete(self, study_env):
        data = _create_session(study_env)
        assert data["concept_id"] == "compactness"
        assert data["canonical_name_ko"] == "옹골성"
        assert data["current_step"] == 1
        assert data["steps"] == ["diagnose", "prerequisites", "representations", "mapping", "misconceptions", "recall", "summary"]

    def test_session_dir_contains_pipeline_artifacts(self, study_env):
        data = _create_session(study_env)
        session_dir = study_env["runs_dir"] / data["session_id"]
        assert session_dir.is_dir()
        assert (session_dir / "session.json").exists()
        assert (session_dir / "representation_set.json").exists()
        assert (session_dir / "prerequisite_graph.json").exists()
        assert (session_dir / "diagnosis.json").exists()

    def test_study_session_state_json_written(self, study_env):
        data = _create_session(study_env)
        state_path = study_env["runs_dir"] / data["session_id"] / "study_session_state.json"
        assert state_path.exists()

    def test_bank_auto_prepared_in_tmp_bank_root(self, study_env):
        _create_session(study_env)
        bank_dir = study_env["bank_root"] / "compactness"
        assert (bank_dir / "questions.generated.json").exists()
        assert (bank_dir / "questions.accepted.json").exists()

    def test_unknown_concept_returns_422(self, study_env):
        resp = client.post("/api/study-session", json={"concept_id": "nonexistent_concept"})
        assert resp.status_code == 422

    def test_no_source_returns_422(self, study_env):
        # Remove all source files
        for f in study_env["sources_dir"].iterdir():
            f.unlink()
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        assert resp.status_code == 422
        assert "소스 파일을 찾을 수 없습니다" in resp.json()["detail"]

    def test_explicit_source_path_used(self, study_env):
        resp = client.post("/api/study-session", json={
            "concept_id": "compactness",
            "source_relative_path": "sources/test_source.md",
        })
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# TestGetStudySession
# ---------------------------------------------------------------------------


class TestGetStudySession:
    def test_returns_200_with_full_state_schema(self, study_env):
        data = _create_session(study_env)
        resp = client.get(f"/api/study-session/{data['session_id']}")
        assert resp.status_code == 200
        state = resp.json()
        # All fields present
        assert state["session_id"] == data["session_id"]
        assert state["concept_id"] == "compactness"
        assert state["current_step"] == 1
        assert state["steps"] == ["diagnose", "prerequisites", "representations", "mapping", "misconceptions", "recall", "summary"]
        assert state["steps_completed"] == []
        assert state["diagnosis"] is None
        assert state["self_explanations"] is None
        assert state["recall_completed"] is False
        assert state["recall_session_id"] is None
        assert state["completed"] is False
        assert state["completed_at"] is None
        assert "created_at" in state
        assert "updated_at" in state

    def test_returns_404_nonexistent(self, study_env):
        resp = client.get("/api/study-session/nonexistent-session-id")
        assert resp.status_code == 404

    def test_reflects_diagnosis_after_submit(self, study_env):
        data = _create_session(study_env)
        client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "열린 덮개 알아",
            "gap_description": "모르겠어",
        })
        resp = client.get(f"/api/study-session/{data['session_id']}")
        state = resp.json()
        assert state["diagnosis"] is not None
        assert state["diagnosis"]["prior_knowledge"] == "열린 덮개 알아"
        assert "diagnose" in state["steps_completed"]
        assert state["current_step"] == 2

    def test_reflects_step_advancement(self, study_env):
        data = _create_session(study_env)
        # Diagnose first
        client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "x", "gap_description": "y",
        })
        # Advance prerequisites
        client.post(f"/api/study-session/{data['session_id']}/advance", json={
            "completed_step": "prerequisites",
        })
        resp = client.get(f"/api/study-session/{data['session_id']}")
        state = resp.json()
        assert state["current_step"] == 3
        assert "prerequisites" in state["steps_completed"]


# ---------------------------------------------------------------------------
# TestDiagnose
# ---------------------------------------------------------------------------


class TestDiagnose:
    def test_returns_200_with_estimate(self, study_env):
        data = _create_session(study_env)
        resp = client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "열린 덮개가 뭔지는 알아",
            "gap_description": "증명이 이해 안 돼",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "initial_mastery_estimate" in body
        assert "identified_gaps" in body
        assert "recommendation" in body

    def test_empty_input_returns_unknown_mastery(self, study_env):
        data = _create_session(study_env)
        resp = client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "",
            "gap_description": "",
        })
        assert resp.status_code == 200
        assert resp.json()["initial_mastery_estimate"] == "unknown"

    def test_gap_cues_populate_identified_gaps(self, study_env):
        data = _create_session(study_env)
        resp = client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "",
            "gap_description": "모르겠어 왜 이런지",
        })
        body = resp.json()
        assert body["initial_mastery_estimate"] == "partial"
        assert len(body["identified_gaps"]) >= 2  # "모르겠" + "왜"

    def test_auto_advances_to_step_2(self, study_env):
        data = _create_session(study_env)
        client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "x", "gap_description": "y",
        })
        state = client.get(f"/api/study-session/{data['session_id']}").json()
        assert state["current_step"] == 2
        assert "diagnose" in state["steps_completed"]

    def test_returns_404_nonexistent_session(self, study_env):
        resp = client.post("/api/study-session/bad-id/diagnose", json={
            "prior_knowledge": "x", "gap_description": "y",
        })
        assert resp.status_code == 404

    def test_returns_409_already_diagnosed(self, study_env):
        data = _create_session(study_env)
        client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "x", "gap_description": "y",
        })
        resp = client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "a", "gap_description": "b",
        })
        assert resp.status_code == 409
        assert "이미 진단이 완료되었습니다" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# TestAdvanceStep
# ---------------------------------------------------------------------------


class TestAdvanceStep:
    def _create_and_diagnose(self, study_env) -> str:
        data = _create_session(study_env)
        client.post(f"/api/study-session/{data['session_id']}/diagnose", json={
            "prior_knowledge": "x", "gap_description": "y",
        })
        return data["session_id"]

    def test_advances_prerequisites_to_representations(self, study_env):
        sid = self._create_and_diagnose(study_env)
        resp = client.post(f"/api/study-session/{sid}/advance", json={
            "completed_step": "prerequisites",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == 3
        assert body["current_step_name"] == "representations"
        assert "prerequisites" in body["steps_completed"]

    def test_sequential_advancement_through_all_steps(self, study_env):
        sid = self._create_and_diagnose(study_env)
        for step, expected_next in [
            ("prerequisites", 3),
            ("representations", 4),
        ]:
            resp = client.post(f"/api/study-session/{sid}/advance", json={
                "completed_step": step,
            })
            assert resp.status_code == 200
            assert resp.json()["current_step"] == expected_next

        # Mapping step requires all tasks to be submitted
        _submit_all_mapping_tasks(sid)
        for step, expected_next in [
            ("mapping", 5),
            ("misconceptions", 6),
            ("recall", 7),
        ]:
            resp = client.post(f"/api/study-session/{sid}/advance", json={
                "completed_step": step,
            })
            assert resp.status_code == 200
            assert resp.json()["current_step"] == expected_next

    def test_returns_409_diagnose_already_done(self, study_env):
        sid = self._create_and_diagnose(study_env)
        resp = client.post(f"/api/study-session/{sid}/advance", json={
            "completed_step": "diagnose",
        })
        assert resp.status_code == 409
        assert "이미 완료된 단계입니다" in resp.json()["detail"]

    def test_returns_400_diagnose_not_done(self, study_env):
        # Create session without diagnosing
        data = _create_session(study_env)
        resp = client.post(f"/api/study-session/{data['session_id']}/advance", json={
            "completed_step": "diagnose",
        })
        assert resp.status_code == 400
        assert "diagnose를 먼저 호출하세요" in resp.json()["detail"]

    def test_returns_400_step_order_violation(self, study_env):
        sid = self._create_and_diagnose(study_env)
        # Try to advance representations before prerequisites
        resp = client.post(f"/api/study-session/{sid}/advance", json={
            "completed_step": "representations",
        })
        assert resp.status_code == 400
        assert "이전 단계를 먼저 완료해야 합니다" in resp.json()["detail"]

    def test_returns_400_invalid_step_name(self, study_env):
        sid = self._create_and_diagnose(study_env)
        resp = client.post(f"/api/study-session/{sid}/advance", json={
            "completed_step": "invalid_step",
        })
        assert resp.status_code == 400
        assert "유효하지 않은 단계입니다" in resp.json()["detail"]

    def test_returns_400_at_final_step(self, study_env):
        sid = self._create_and_diagnose(study_env)
        # Advance through steps before mapping
        for step in ["prerequisites", "representations"]:
            client.post(f"/api/study-session/{sid}/advance", json={"completed_step": step})
        # Submit mapping tasks, then advance through remaining steps
        _submit_all_mapping_tasks(sid)
        for step in ["mapping", "misconceptions", "recall"]:
            client.post(f"/api/study-session/{sid}/advance", json={"completed_step": step})
        # Now at summary (step 7) — try invalid advance
        resp = client.post(f"/api/study-session/{sid}/advance", json={
            "completed_step": "recall",
        })
        assert resp.status_code == 400

    def test_returns_404_nonexistent_session(self, study_env):
        resp = client.post("/api/study-session/nonexistent/advance", json={
            "completed_step": "prerequisites",
        })
        assert resp.status_code == 404

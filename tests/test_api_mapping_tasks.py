"""
API tests for mapping-tasks and mapping-submit endpoints.

Step 8: Mapping + Confusion Map API Router.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"


@pytest.fixture()
def mapping_env(tmp_path: Path, monkeypatch):
    """Isolated environment with a session ready for mapping tests.

    Sets up:
    - A fake session dir with study_session_state.json
    - Config pointing to tmp dirs and real CARDS_DIR
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Monkeypatch config used by the mapping router
    import apps.api.config as cfg
    monkeypatch.setattr(cfg, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(cfg, "CARDS_DIR", CARDS_DIR)

    # Clear card caches so monkeypatched CARDS_DIR is picked up
    from apps.api.services.card_service import clear_cache
    clear_cache()

    return {"runs_dir": runs_dir}


def _create_fake_session(runs_dir: Path, session_id: str = "test-sess-001", concept_id: str = "compactness") -> Path:
    """Create a minimal session dir with state file."""
    session_dir = runs_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "session_id": session_id,
        "concept_id": concept_id,
        "canonical_name_ko": "옹골성",
        "current_step": 3,
        "steps": ["diagnose", "prerequisites", "representations", "mapping", "misconceptions", "recall", "summary"],
        "steps_completed": ["diagnose", "prerequisites", "representations"],
        "diagnosis": None,
        "self_explanations": None,
        "recall_completed": False,
        "recall_session_id": None,
        "completed": False,
        "completed_at": None,
        "created_at": "2026-05-08T00:00:00Z",
        "updated_at": "2026-05-08T00:00:00Z",
    }
    (session_dir / "study_session_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return session_dir


# ---------------------------------------------------------------------------
# GET /api/study-session/{session_id}/mapping-tasks
# ---------------------------------------------------------------------------


class TestGetMappingTasks:
    def test_returns_three_tasks(self, mapping_env):
        _create_fake_session(mapping_env["runs_dir"])
        resp = client.get("/api/study-session/test-sess-001/mapping-tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 3

    def test_response_structure(self, mapping_env):
        _create_fake_session(mapping_env["runs_dir"])
        resp = client.get("/api/study-session/test-sess-001/mapping-tasks")
        data = resp.json()
        assert data["session_id"] == "test-sess-001"
        assert data["concept_id"] == "compactness"
        for task in data["tasks"]:
            assert "task_id" in task
            assert "task_type" in task
            assert "prompt" in task
            assert "source_representations" in task
            assert "target_representation" in task

    def test_tasks_persisted_on_first_call(self, mapping_env):
        session_dir = _create_fake_session(mapping_env["runs_dir"])
        assert not (session_dir / "mapping_tasks.json").exists()
        client.get("/api/study-session/test-sess-001/mapping-tasks")
        assert (session_dir / "mapping_tasks.json").exists()

    def test_idempotent_returns_same_tasks(self, mapping_env):
        _create_fake_session(mapping_env["runs_dir"])
        resp1 = client.get("/api/study-session/test-sess-001/mapping-tasks")
        resp2 = client.get("/api/study-session/test-sess-001/mapping-tasks")
        assert resp1.json()["tasks"] == resp2.json()["tasks"]

    def test_session_not_found_returns_404(self, mapping_env):
        resp = client.get("/api/study-session/nonexistent/mapping-tasks")
        assert resp.status_code == 404

    def test_unknown_concept_card_returns_404(self, mapping_env):
        runs_dir = mapping_env["runs_dir"]
        session_dir = runs_dir / "bad-concept-sess"
        session_dir.mkdir()
        state = {
            "session_id": "bad-concept-sess",
            "concept_id": "nonexistent_concept",
            "canonical_name_ko": "없음",
            "current_step": 3,
            "steps": [],
            "steps_completed": [],
            "diagnosis": None,
            "self_explanations": None,
            "recall_completed": False,
            "recall_session_id": None,
            "completed": False,
            "completed_at": None,
            "created_at": "2026-05-08T00:00:00Z",
            "updated_at": "2026-05-08T00:00:00Z",
        }
        (session_dir / "study_session_state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
        resp = client.get("/api/study-session/bad-concept-sess/mapping-tasks")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/study-session/{session_id}/mapping-submit
# ---------------------------------------------------------------------------


class TestSubmitMapping:
    def _setup_session_with_tasks(self, mapping_env) -> str:
        session_dir = _create_fake_session(mapping_env["runs_dir"])
        # Pre-generate tasks via GET
        client.get("/api/study-session/test-sess-001/mapping-tasks")
        return "test-sess-001"

    def test_submit_correct_answer(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]
        f2c = next(t for t in tasks if t["task_type"] == "formal_to_counterexample")

        resp = client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": f2c["task_id"],
            "learner_response": (
                "(0,1)의 open cover {(1/n, 1)}을 생각하자. 이 열린 덮개에서 "
                "어떤 유한 부분모임을 택하더라도 (0,1)을 덮을 수 없으므로 "
                "no finite subcover가 존재하지 않는다. 따라서 compact하지 않다."
            ),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is True
        assert data["score"] >= 0.70
        assert data["task_id"] == f2c["task_id"]
        assert "confusion_map" in data

    def test_submit_incorrect_answer(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]
        f2c = next(t for t in tasks if t["task_type"] == "formal_to_counterexample")

        resp = client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": f2c["task_id"],
            "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is False
        assert len(data["mapping_failures"]) >= 1

    def test_submit_empty_response_returns_422(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]

        resp = client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": tasks[0]["task_id"],
            "learner_response": "   ",
        })
        assert resp.status_code == 422

    def test_submit_nonexistent_task_returns_404(self, mapping_env):
        self._setup_session_with_tasks(mapping_env)
        resp = client.post("/api/study-session/test-sess-001/mapping-submit", json={
            "task_id": "nonexistent_task",
            "learner_response": "some text",
        })
        assert resp.status_code == 404

    def test_submit_duplicate_returns_400(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]
        task = tasks[0]

        client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": task["task_id"],
            "learner_response": "first attempt",
        })
        resp = client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": task["task_id"],
            "learner_response": "second attempt",
        })
        assert resp.status_code == 400
        assert "already submitted" in resp.json()["detail"]

    def test_submit_session_not_found_returns_404(self, mapping_env):
        resp = client.post("/api/study-session/nonexistent/mapping-submit", json={
            "task_id": "x",
            "learner_response": "test",
        })
        assert resp.status_code == 404

    def test_mapping_results_persisted(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        session_dir = mapping_env["runs_dir"] / sid
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]

        client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": tasks[0]["task_id"],
            "learner_response": "test response",
        })

        results_path = session_dir / "mapping_results.json"
        assert results_path.exists()
        results = json.loads(results_path.read_text(encoding="utf-8"))
        assert len(results) == 1
        assert results[0]["task_id"] == tasks[0]["task_id"]

    def test_confusion_map_updated_after_submit(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]

        resp = client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": tasks[0]["task_id"],
            "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
        })
        cmap = resp.json()["confusion_map"]
        assert len(cmap["mapping_edges"]) == 1
        assert cmap["last_updated_step"] == "mapping"

    def test_confusion_map_persisted_to_disk(self, mapping_env):
        sid = self._setup_session_with_tasks(mapping_env)
        session_dir = mapping_env["runs_dir"] / sid
        tasks = client.get(f"/api/study-session/{sid}/mapping-tasks").json()["tasks"]

        client.post(f"/api/study-session/{sid}/mapping-submit", json={
            "task_id": tasks[0]["task_id"],
            "learner_response": "test",
        })
        assert (session_dir / "confusion_map.json").exists()

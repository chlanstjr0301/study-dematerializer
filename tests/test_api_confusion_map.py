"""
API tests for GET /api/study-session/{session_id}/confusion-map endpoint.

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
def cmap_env(tmp_path: Path, monkeypatch):
    """Isolated environment for confusion map tests."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    import apps.api.config as cfg
    monkeypatch.setattr(cfg, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(cfg, "CARDS_DIR", CARDS_DIR)

    from apps.api.services.card_service import clear_cache
    clear_cache()

    return {"runs_dir": runs_dir}


def _create_fake_session(runs_dir: Path, session_id: str = "sess-cmap-001", concept_id: str = "compactness") -> Path:
    """Create a minimal session dir."""
    session_dir = runs_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "session_id": session_id,
        "concept_id": concept_id,
        "canonical_name_ko": "옹골성",
        "current_step": 3,
        "steps": ["diagnose", "prerequisites", "representations", "mapping"],
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
# GET /api/study-session/{session_id}/confusion-map
# ---------------------------------------------------------------------------


class TestGetConfusionMap:
    def test_returns_initialized_map_when_no_file(self, cmap_env):
        """When no confusion_map.json yet, returns initialized map from card."""
        _create_fake_session(cmap_env["runs_dir"])
        resp = client.get("/api/study-session/sess-cmap-001/confusion-map")
        assert resp.status_code == 200
        data = resp.json()
        assert data["concept_id"] == "compactness"
        assert data["session_id"] == "sess-cmap-001"
        assert data["last_updated_step"] == "init"
        assert len(data["prerequisite_nodes"]) > 0

    def test_returns_prerequisite_nodes_from_card(self, cmap_env):
        _create_fake_session(cmap_env["runs_dir"])
        resp = client.get("/api/study-session/sess-cmap-001/confusion-map")
        data = resp.json()
        prereq_ids = [n["concept_id"] for n in data["prerequisite_nodes"]]
        assert "metric_space" in prereq_ids
        assert "open_cover" in prereq_ids
        assert all(n["mastery"] == "unknown" for n in data["prerequisite_nodes"])

    def test_returns_empty_collections_initially(self, cmap_env):
        _create_fake_session(cmap_env["runs_dir"])
        resp = client.get("/api/study-session/sess-cmap-001/confusion-map")
        data = resp.json()
        assert data["mapping_edges"] == []
        assert data["misconception_tags"] == []
        assert data["next_recall_triggers"] == []
        assert data["evidence_snippets"] == []

    def test_returns_persisted_map(self, cmap_env):
        """When confusion_map.json exists, returns that state."""
        session_dir = _create_fake_session(cmap_env["runs_dir"])
        # Write a confusion map to disk
        from apps.api.services.card_service import load_ground_truth_card
        from apps.api.services.confusion_map_service import (
            initialize_confusion_map,
            persist_confusion_map,
            update_from_diagnosis,
        )
        card = load_ground_truth_card("compactness", use_cache=False)
        cmap = initialize_confusion_map("sess-cmap-001", "compactness", card)
        cmap = update_from_diagnosis(cmap, {
            "mastery_estimates": {"metric_space": "solid"},
            "misconception_cues": ["bounded_implies_compact"],
        })
        persist_confusion_map(cmap, session_dir)

        resp = client.get("/api/study-session/sess-cmap-001/confusion-map")
        data = resp.json()
        assert data["last_updated_step"] == "diagnosis"
        assert "bounded_implies_compact" in data["misconception_tags"]
        node_map = {n["concept_id"]: n for n in data["prerequisite_nodes"]}
        assert node_map["metric_space"]["mastery"] == "solid"

    def test_after_mapping_submit(self, cmap_env):
        """After submitting a mapping answer, confusion map reflects it."""
        _create_fake_session(cmap_env["runs_dir"])
        # Generate tasks
        client.get("/api/study-session/sess-cmap-001/mapping-tasks")
        tasks = client.get("/api/study-session/sess-cmap-001/mapping-tasks").json()["tasks"]
        f2c = next(t for t in tasks if t["task_type"] == "formal_to_counterexample")

        # Submit a failing answer
        client.post("/api/study-session/sess-cmap-001/mapping-submit", json={
            "task_id": f2c["task_id"],
            "learner_response": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
        })

        # Check confusion map
        resp = client.get("/api/study-session/sess-cmap-001/confusion-map")
        data = resp.json()
        assert data["last_updated_step"] == "mapping"
        assert len(data["mapping_edges"]) == 1
        edge = data["mapping_edges"][0]
        assert edge["task_type"] == "formal_to_counterexample"
        assert edge["passed"] is False

    def test_session_not_found_returns_404(self, cmap_env):
        resp = client.get("/api/study-session/nonexistent/confusion-map")
        assert resp.status_code == 404

    def test_unknown_concept_returns_empty_map(self, cmap_env):
        """Session with unknown concept (no card) → minimal empty map."""
        runs_dir = cmap_env["runs_dir"]
        session_dir = runs_dir / "no-card-sess"
        session_dir.mkdir()
        state = {
            "session_id": "no-card-sess",
            "concept_id": "unknown_concept_xyz",
            "canonical_name_ko": "없음",
            "current_step": 1,
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
        resp = client.get("/api/study-session/no-card-sess/confusion-map")
        assert resp.status_code == 200
        data = resp.json()
        assert data["concept_id"] == "unknown_concept_xyz"
        assert data["prerequisite_nodes"] == []
        assert data["last_updated_step"] == "init"

"""
Tests for GET /api/sessions, GET /api/sessions/{id}, GET /api/sessions/{id}/summary,
and GET /api/sessions/{id}/visualization/{artifact}.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.session_service as session_svc

client = TestClient(app)


@pytest.fixture()
def runs_dir(tmp_path: Path) -> Path:
    """Create a fake runs directory with one session."""
    session_id = "test-session-001"
    session_dir = tmp_path / session_id
    session_dir.mkdir()

    session_data = {
        "session_id": session_id,
        "concept_id": "compactness",
        "source_path": "banks/compactness/questions.accepted.json",
        "started_at": "2026-01-01T10:00:00Z",
        "ended_at": "2026-01-01T10:05:00Z",
        "grader_type": "mock",
        "mastery_updates": [],
    }
    (session_dir / "session.json").write_text(
        json.dumps(session_data, indent=2), encoding="utf-8"
    )

    attempts = [
        {
            "question_id": "q001",
            "learner_response": "A compact set has a finite open cover.",
            "grading": {
                "accuracy": 0.6,
                "mastery_suggestion": "partial",
                "errors": [],
                "missing_elements": [],
                "confidence": 0.8,
                "needs_human_review": False,
            },
        }
    ]
    (session_dir / "recall_attempts.json").write_text(
        json.dumps(attempts, indent=2), encoding="utf-8"
    )

    summary = "# Session Summary\n\nCompactness review complete.\n"
    (session_dir / "session_summary.md").write_text(summary, encoding="utf-8")

    # Visualization artifacts
    viz_dir = session_dir / "visualization"
    viz_dir.mkdir()

    mastery_map = {
        "session_id": session_id,
        "concept_id": "compactness",
        "overall_mastery": "partial",
        "weakest_links": [],
        "representations": [],
    }
    (viz_dir / "mastery_map.json").write_text(
        json.dumps(mastery_map, indent=2), encoding="utf-8"
    )

    recall_feedback = {"session_id": session_id, "items": []}
    (viz_dir / "recall_feedback.json").write_text(
        json.dumps(recall_feedback, indent=2), encoding="utf-8"
    )

    review_queue = {"session_id": session_id, "items": []}
    (viz_dir / "review_queue.json").write_text(
        json.dumps(review_queue, indent=2), encoding="utf-8"
    )

    (viz_dir / "mastery_map.mmd").write_text("graph LR\n  A-->B\n", encoding="utf-8")
    (viz_dir / "session_flow.mmd").write_text("graph TD\n  Start-->End\n", encoding="utf-8")

    return tmp_path


class TestListSessions:
    def test_returns_empty_when_no_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", tmp_path / "nonexistent")
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_session_list(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "test-session-001"
        assert data[0]["concept_id"] == "compactness"

    def test_schema_fields(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions")
        item = resp.json()[0]
        assert "session_id" in item
        assert "concept_id" in item
        assert "started_at" in item


class TestGetSession:
    def test_returns_session_data(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001")
        assert resp.status_code == 200
        data = resp.json()
        assert "session" in data
        assert "attempts" in data
        assert data["session"]["concept_id"] == "compactness"
        assert len(data["attempts"]) == 1

    def test_404_for_missing_session(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/does-not-exist")
        assert resp.status_code == 404


class TestGetSummary:
    def test_returns_summary_content(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/summary")
        assert resp.status_code == 200
        assert "Session Summary" in resp.json()["content"]

    def test_404_for_missing_session(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/does-not-exist/summary")
        assert resp.status_code == 404


class TestGetVisualization:
    def test_returns_mastery_map_json(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/visualization/mastery_map")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "test-session-001"
        assert data["concept_id"] == "compactness"

    def test_returns_recall_feedback_json(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/visualization/recall_feedback")
        assert resp.status_code == 200
        assert "session_id" in resp.json()

    def test_returns_mmd_as_text(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/visualization/mastery_map_mmd")
        assert resp.status_code == 200
        assert "graph" in resp.text

    def test_returns_session_flow_mmd(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/visualization/session_flow_mmd")
        assert resp.status_code == 200
        assert "graph" in resp.text

    def test_400_for_invalid_artifact(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/test-session-001/visualization/not_an_artifact")
        assert resp.status_code == 400

    def test_404_for_missing_session(self, runs_dir, monkeypatch):
        monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
        resp = client.get("/api/sessions/does-not-exist/visualization/mastery_map")
        assert resp.status_code == 404



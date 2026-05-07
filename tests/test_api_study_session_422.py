"""
Tests for MVP6-Hotfix: Study session 422 regression — normal UI flow must not 422.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI test client with isolated data dirs."""
    import apps.api.config as config

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bank_root = tmp_path / "banks"
    bank_root.mkdir()
    study_md = tmp_path / "STUDY.md"
    study_md.write_text("# STUDY\n", encoding="utf-8")
    sources_dir = tmp_path / "sources"
    # NOTE: sources_dir intentionally NOT created — simulates no uploaded sources

    monkeypatch.setattr(config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(config, "STUDY_MD", study_md)
    monkeypatch.setattr(config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")

    from apps.api.main import app

    return TestClient(app)


class TestStudySession422:
    """POST /api/study-session must not 422 from normal UI flow."""

    def test_create_without_source_no_422(self, client):
        """Frontend sends {concept_id: 'compactness'} with no source → must succeed."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "compactness"},
        )
        # Must NOT be 422
        assert resp.status_code != 422, f"Got 422: {resp.json()}"
        assert resp.status_code == 201
        data = resp.json()
        assert data["concept_id"] == "compactness"
        assert data["session_id"]

    def test_create_with_null_source_no_422(self, client):
        """Frontend may send source_relative_path=null."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "compactness", "source_relative_path": None},
        )
        assert resp.status_code != 422
        assert resp.status_code == 201

    def test_create_with_explicit_missing_source_422(self, client):
        """Explicit nonexistent source path should 422."""
        resp = client.post(
            "/api/study-session",
            json={
                "concept_id": "compactness",
                "source_relative_path": "sources/nonexistent.md",
            },
        )
        assert resp.status_code == 422

    def test_create_unsupported_concept_422(self, client):
        """Unsupported concept_id should 422."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "nonexistent_concept"},
        )
        assert resp.status_code == 422

    def test_response_schema_matches_frontend(self, client):
        """Response must contain fields expected by frontend."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "compactness"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # All required fields
        assert "session_id" in data
        assert "concept_id" in data
        assert "canonical_name_ko" in data
        assert "current_step" in data
        assert "steps" in data
        assert "representations" in data
        assert "prerequisites" in data
        assert "misconceptions" in data

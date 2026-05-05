"""
Tests for GET /api/project/status and POST /api/project/bootstrap.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.config as config

client = TestClient(app)


@pytest.fixture()
def project_env(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_ROOT",   tmp_path)
    monkeypatch.setattr(config, "BANK_ROOT",   tmp_path / "banks")
    monkeypatch.setattr(config, "RUNS_DIR",    tmp_path / "runs")
    monkeypatch.setattr(config, "SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr(config, "STUDY_MD",    tmp_path / "STUDY.md")
    return tmp_path


# ---------------------------------------------------------------------------
# TestProjectStatus
# ---------------------------------------------------------------------------


class TestProjectStatus:
    def test_returns_200(self, project_env):
        resp = client.get("/api/project/status")
        assert resp.status_code == 200

    def test_returns_expected_keys(self, project_env):
        resp = client.get("/api/project/status")
        data = resp.json()
        assert "project_root" in data
        assert "study_md_exists" in data
        assert "banks_dir_exists" in data
        assert "runs_dir_exists" in data
        assert "sources_dir_exists" in data

    def test_dirs_absent_before_bootstrap(self, project_env):
        resp = client.get("/api/project/status")
        data = resp.json()
        assert data["banks_dir_exists"] is False
        assert data["sources_dir_exists"] is False


# ---------------------------------------------------------------------------
# TestProjectBootstrap
# ---------------------------------------------------------------------------


class TestProjectBootstrap:
    def test_returns_200(self, project_env):
        resp = client.post("/api/project/bootstrap")
        assert resp.status_code == 200

    def test_creates_directories(self, project_env):
        client.post("/api/project/bootstrap")
        assert (project_env / "banks").is_dir()
        assert (project_env / "runs").is_dir()
        assert (project_env / "sources").is_dir()

    def test_creates_study_md(self, project_env):
        client.post("/api/project/bootstrap")
        assert (project_env / "STUDY.md").exists()

    def test_bootstrap_response_has_created_list(self, project_env):
        resp = client.post("/api/project/bootstrap")
        data = resp.json()
        assert "created" in data
        assert isinstance(data["created"], list)

    def test_second_bootstrap_without_overwrite_skips_existing(self, project_env):
        # First bootstrap: creates everything
        client.post("/api/project/bootstrap")
        study_md = project_env / "STUDY.md"
        original = study_md.read_text(encoding="utf-8")
        study_md.write_text(original + "\n# edited\n", encoding="utf-8")

        # Second bootstrap without overwrite: STUDY.md must remain edited
        client.post("/api/project/bootstrap")
        assert "# edited" in study_md.read_text(encoding="utf-8")

    def test_bootstrap_overwrite_resets_study_md(self, project_env):
        client.post("/api/project/bootstrap")
        study_md = project_env / "STUDY.md"
        study_md.write_text("custom content\n", encoding="utf-8")

        client.post("/api/project/bootstrap?overwrite=true")
        assert "custom content" not in study_md.read_text(encoding="utf-8")

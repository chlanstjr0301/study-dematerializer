"""
Tests for GET /api/project/status and POST /api/project/bootstrap.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.project_service as project_svc
from gonghaebun.study_md.parser import parse_study_md

client = TestClient(app)


@pytest.fixture()
def project_env(tmp_path: Path, monkeypatch):
    """Patch project_service.config to use tmp_path subdirs."""
    import apps.api.config as cfg
    monkeypatch.setattr(cfg, "DATA_ROOT",    tmp_path)
    monkeypatch.setattr(cfg, "BANK_ROOT",    tmp_path / "banks")
    monkeypatch.setattr(cfg, "RUNS_DIR",     tmp_path / "runs")
    monkeypatch.setattr(cfg, "SOURCES_DIR",  tmp_path / "sources")
    monkeypatch.setattr(cfg, "STUDY_MD",     tmp_path / "STUDY.md")
    return tmp_path


class TestProjectStatus:
    def test_all_missing(self, project_env):
        resp = client.get("/api/project/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["study_md_exists"] is False
        assert data["banks_dir_exists"] is False
        assert data["runs_dir_exists"] is False
        assert data["sources_dir_exists"] is False

    def test_all_present(self, project_env):
        (project_env / "banks").mkdir()
        (project_env / "runs").mkdir()
        (project_env / "sources").mkdir()
        (project_env / "STUDY.md").write_text("# STUDY.md\n", encoding="utf-8")
        resp = client.get("/api/project/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["study_md_exists"] is True
        assert data["banks_dir_exists"] is True
        assert data["runs_dir_exists"] is True
        assert data["sources_dir_exists"] is True


class TestBootstrap:
    def test_creates_dirs_and_study_md(self, project_env):
        resp = client.post("/api/project/bootstrap")
        assert resp.status_code == 200
        data = resp.json()
        assert "banks" in data["created"]
        assert "runs" in data["created"]
        assert "sources" in data["created"]
        assert "STUDY.md" in data["created"]
        assert (project_env / "banks").exists()
        assert (project_env / "runs").exists()
        assert (project_env / "sources").exists()
        assert (project_env / "STUDY.md").exists()

    def test_idempotent(self, project_env):
        client.post("/api/project/bootstrap")
        resp = client.post("/api/project/bootstrap")
        assert resp.status_code == 200
        data = resp.json()
        assert "banks" in data["skipped"]
        assert "runs" in data["skipped"]
        assert "sources" in data["skipped"]
        assert "STUDY.md" in data["skipped"]

    def test_skips_existing_study_md_by_default(self, project_env):
        original = "# My existing STUDY.md\n"
        (project_env / "STUDY.md").write_text(original, encoding="utf-8")
        resp = client.post("/api/project/bootstrap")
        assert resp.status_code == 200
        assert "STUDY.md" in resp.json()["skipped"]
        assert (project_env / "STUDY.md").read_text(encoding="utf-8") == original

    def test_overwrites_study_md_when_overwrite_true(self, project_env):
        original = "# Old STUDY.md\n"
        (project_env / "STUDY.md").write_text(original, encoding="utf-8")
        resp = client.post("/api/project/bootstrap?overwrite=true")
        assert resp.status_code == 200
        assert "STUDY.md" in resp.json()["created"]
        new_content = (project_env / "STUDY.md").read_text(encoding="utf-8")
        assert new_content != original

    def test_study_md_parseable(self, project_env):
        client.post("/api/project/bootstrap")
        result = parse_study_md(project_env / "STUDY.md")
        assert result == {}  # empty-concept skeleton — no concept records yet

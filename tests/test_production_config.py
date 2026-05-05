"""
Tests for MVP4-K production hardening:
- Config safe defaults
- .env.example completeness
- GET /api/ready endpoint
- SPA frontend serving (explicit catch-all)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.api.config as config
import apps.api.services.session_service as session_svc


# ---------------------------------------------------------------------------
# TestConfigSafeDefaults
# ---------------------------------------------------------------------------


class TestConfigSafeDefaults:
    def test_default_grader_is_mock(self):
        assert config.DEFAULT_GRADER == "mock"

    def test_llm_disabled_default_is_true(self):
        # Safe default: LLM must be off unless explicitly enabled
        assert config.LLM_DISABLED is True

    def test_api_host_default_is_loopback(self):
        assert config.API_HOST == "127.0.0.1"

    def test_api_port_default(self):
        assert config.API_PORT == 8000

    def test_cors_origins_are_localhost_only(self):
        for origin in config.CORS_ORIGINS:
            assert "localhost" in origin or "127.0.0.1" in origin, (
                f"Non-localhost CORS origin in defaults: {origin!r}"
            )

    def test_cors_origins_no_empty_strings(self):
        assert "" not in config.CORS_ORIGINS


# ---------------------------------------------------------------------------
# TestEnvExample
# ---------------------------------------------------------------------------

_EXPECTED_VARS = [
    "GONGHAEBUN_DATA_ROOT",
    "GONGHAEBUN_BANK_ROOT",
    "GONGHAEBUN_RUNS_DIR",
    "GONGHAEBUN_STUDY_MD",
    "GONGHAEBUN_SOURCES_DIR",
    "GONGHAEBUN_GRADER",
    "GONGHAEBUN_LLM_DISABLED",
    "GONGHAEBUN_LLM_MAX_CALLS_PER_SESSION",
    "GONGHAEBUN_LLM_TIMEOUT_SECONDS",
    "GONGHAEBUN_API_HOST",
    "GONGHAEBUN_API_PORT",
    "GONGHAEBUN_CORS_ORIGINS",
    "GONGHAEBUN_SERVE_FRONTEND",
    "OPENAI_API_KEY",
]


class TestEnvExample:
    @pytest.fixture
    def env_example_content(self):
        path = Path(".env.example")
        assert path.exists(), ".env.example must exist"
        return path.read_text(encoding="utf-8")

    def test_env_example_exists(self):
        assert Path(".env.example").exists()

    def test_env_example_has_no_real_api_key(self, env_example_content):
        assert "sk-" not in env_example_content

    def test_env_example_has_all_gonghaebun_vars(self, env_example_content):
        for var in _EXPECTED_VARS:
            assert var in env_example_content, (
                f"Missing variable {var!r} in .env.example"
            )


# ---------------------------------------------------------------------------
# TestReadyEndpoint
# ---------------------------------------------------------------------------


class TestReadyEndpoint:
    @pytest.fixture
    def ready_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "data")
        monkeypatch.setattr(config, "STUDY_MD", tmp_path / "data" / "STUDY.md")
        monkeypatch.setattr(config, "LLM_DISABLED", True)
        return tmp_path

    def test_ready_returns_200(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        resp = client.get("/api/ready")
        assert resp.status_code == 200

    def test_ready_response_has_ready_and_checks(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert "ready" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_ready_data_dir_ok_when_creatable(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["checks"]["data_dir"] == "ok"

    def test_ready_study_md_missing_not_failure(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["checks"]["study_md"] == "missing"
        assert data["ready"] is True

    def test_ready_study_md_ok_when_valid(self, ready_env, monkeypatch):
        from apps.api.main import app
        study_md = ready_env / "data" / "STUDY.md"
        study_md.parent.mkdir(parents=True, exist_ok=True)
        study_md.write_text(
            "# STUDY.md\n\n## compactness\n\n"
            "**domain**: real_analysis\n"
            "**overall_mastery**: unknown\n"
            "**next_review**: 2026-01-01\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "STUDY_MD", study_md)
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["checks"]["study_md"] == "ok"

    def test_ready_llm_reports_disabled_by_default(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["checks"]["llm"] == "disabled"

    def test_ready_llm_no_key_reports_no_api_key(self, ready_env, monkeypatch):
        from apps.api.main import app
        monkeypatch.setattr(config, "LLM_DISABLED", False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["checks"]["llm"] == "no_api_key"

    def test_ready_is_true_on_clean_project(self, ready_env):
        from apps.api.main import app
        client = TestClient(app)
        data = client.get("/api/ready").json()
        assert data["ready"] is True


# ---------------------------------------------------------------------------
# TestSPAFrontendServing
# ---------------------------------------------------------------------------


@pytest.fixture
def dist_env(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>SPA</body></html>", encoding="utf-8")
    (dist / "favicon.ico").write_bytes(b"\x00")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "main.js").write_text("// js", encoding="utf-8")
    return dist


@pytest.fixture
def spa_client(dist_env, monkeypatch):
    import apps.api.main as main_mod
    monkeypatch.setattr(main_mod, "_DIST", dist_env)
    monkeypatch.setattr(config, "SERVE_FRONTEND", True)
    fresh_app = main_mod.create_app()
    return TestClient(fresh_app)


class TestSPAFrontendServing:
    def test_api_health_not_shadowed_by_spa(self, spa_client):
        resp = spa_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_api_nonexistent_returns_404_json_not_spa(self, spa_client):
        resp = spa_client.get("/api/does-not-exist")
        assert resp.status_code == 404
        # Must be JSON, NOT the SPA index.html
        body = resp.json()
        assert "detail" in body
        assert "SPA" not in resp.text

    def test_root_serves_index_html(self, spa_client):
        resp = spa_client.get("/")
        assert resp.status_code == 200
        assert "SPA" in resp.text

    def test_deep_link_sources_returns_spa(self, spa_client):
        resp = spa_client.get("/sources")
        assert resp.status_code == 200
        assert "SPA" in resp.text

    def test_deep_link_concept_compiler_returns_spa(self, spa_client):
        resp = spa_client.get("/concept-compiler")
        assert resp.status_code == 200
        assert "SPA" in resp.text

    def test_deep_link_sessions_returns_spa(self, spa_client):
        resp = spa_client.get("/sessions/abc123")
        assert resp.status_code == 200
        assert "SPA" in resp.text

    def test_assets_served(self, spa_client):
        resp = spa_client.get("/assets/main.js")
        assert resp.status_code == 200
        assert "js" in resp.text

    def test_real_file_served_directly(self, spa_client):
        resp = spa_client.get("/favicon.ico")
        assert resp.status_code == 200
        assert resp.content == b"\x00"

    def test_serve_frontend_disabled_no_catch_all(self, dist_env, monkeypatch):
        import apps.api.main as main_mod
        monkeypatch.setattr(main_mod, "_DIST", dist_env)
        monkeypatch.setattr(config, "SERVE_FRONTEND", False)
        fresh_app = main_mod.create_app()
        client = TestClient(fresh_app, raise_server_exceptions=False)
        resp = client.get("/sources")
        # Without SPA catch-all, unknown frontend paths are 404 (FastAPI default)
        assert resp.status_code == 404

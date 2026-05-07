"""
Tests for unsupported prerequisite concept guard.

Prerequisite stubs like open_set, metric_space should return a controlled
422 response — not a 500 from pipeline failure.
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

    monkeypatch.setattr(config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(config, "STUDY_MD", study_md)
    monkeypatch.setattr(config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")

    from apps.api.main import app

    return TestClient(app)


class TestUnsupportedPrerequisiteConcept:
    """Prerequisite stubs must return controlled 422, not 500."""

    def test_open_set_returns_422(self, client):
        """open_set is a known prerequisite stub — must 422 with specific message."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "open_set"},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "선행개념 독립 세션 미지원" in detail

    def test_metric_space_returns_422(self, client):
        """metric_space is a prerequisite stub."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "metric_space"},
        )
        assert resp.status_code == 422
        assert "선행개념 독립 세션 미지원" in resp.json()["detail"]

    def test_open_cover_returns_422(self, client):
        """open_cover is a prerequisite stub."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "open_cover"},
        )
        assert resp.status_code == 422
        assert "선행개념 독립 세션 미지원" in resp.json()["detail"]

    def test_heine_borel_returns_422(self, client):
        """heine_borel is a prerequisite stub."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "heine_borel"},
        )
        assert resp.status_code == 422
        assert "선행개념 독립 세션 미지원" in resp.json()["detail"]

    def test_continuity_returns_422(self, client):
        """continuity is a prerequisite stub."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "continuity"},
        )
        assert resp.status_code == 422
        assert "선행개념 독립 세션 미지원" in resp.json()["detail"]

    def test_not_500_error(self, client):
        """Prerequisite concepts must NEVER return 500 (pipeline crash)."""
        for cid in ["open_set", "metric_space", "open_cover", "heine_borel",
                    "sequential_compactness", "continuity", "path_connected"]:
            resp = client.post(
                "/api/study-session",
                json={"concept_id": cid},
            )
            assert resp.status_code != 500, f"{cid} returned 500: {resp.json()}"

    def test_unknown_concept_still_422(self, client):
        """Completely unknown concept_id should still 422."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "nonexistent_xyz"},
        )
        assert resp.status_code == 422

    def test_compactness_not_blocked(self, client):
        """compactness is a supported concept — must not be blocked by prerequisite guard."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "compactness"},
        )
        # Should not get the "선행개념 독립 세션 미지원" error
        if resp.status_code == 422:
            detail = resp.json().get("detail", "")
            assert "선행개념 독립 세션 미지원" not in detail, \
                "compactness incorrectly blocked by prerequisite guard"
        # If it succeeds (201) that's even better — depends on fixture availability
        assert resp.status_code in (201, 500), f"Unexpected {resp.status_code}: {resp.json()}"

    def test_connectedness_not_blocked(self, client):
        """connectedness is a supported concept — must not be blocked by prerequisite guard."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "connectedness"},
        )
        if resp.status_code == 422:
            detail = resp.json().get("detail", "")
            assert "선행개념 독립 세션 미지원" not in detail
        assert resp.status_code in (201, 500)

    def test_uniform_continuity_not_blocked(self, client):
        """uniform_continuity is a supported concept — must not be blocked."""
        resp = client.post(
            "/api/study-session",
            json={"concept_id": "uniform_continuity"},
        )
        if resp.status_code == 422:
            detail = resp.json().get("detail", "")
            assert "선행개념 독립 세션 미지원" not in detail
        assert resp.status_code in (201, 500)

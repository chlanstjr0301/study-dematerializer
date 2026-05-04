"""
Tests for POST /api/banks/build and GET /api/banks/{concept_id}/generated.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.banks_service as banks_svc

client = TestClient(app)

_SAMPLE_SOURCE = Path("tests/data/sample_source.md")


@pytest.fixture()
def bank_env(tmp_path: Path, monkeypatch):
    """
    Set up a tmp data_root with sources/ dir containing sample_source.md.
    Monkeypatches banks_service.config (DATA_ROOT, BANK_ROOT).
    """
    import apps.api.config as cfg

    sources_dir = tmp_path / "sources"
    sources_dir.mkdir(parents=True)
    shutil.copy(_SAMPLE_SOURCE, sources_dir / "sample_source.md")

    bank_root = tmp_path / "banks"

    monkeypatch.setattr(cfg, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(cfg, "BANK_ROOT", bank_root)

    return tmp_path


def _build(concept_id="compactness", source="sources/sample_source.md", doc_id="sample"):
    return client.post("/api/banks/build", json={
        "concept_id": concept_id,
        "source_relative_path": source,
        "document_id": doc_id,
    })


class TestBuildBank:
    def test_returns_201_with_counts(self, bank_env):
        resp = _build()
        assert resp.status_code == 201
        data = resp.json()
        assert data["concept_id"] == "compactness"
        assert data["document_id"] == "sample"
        assert data["block_count"] >= 0
        assert data["question_count"] >= 0
        assert data["bank_dir"] == "banks/compactness"

    def test_json_files_written(self, bank_env):
        import apps.api.config as cfg
        _build()
        concept_dir = cfg.BANK_ROOT / "compactness"
        assert (concept_dir / "blocks.generated.json").exists()
        assert (concept_dir / "questions.generated.json").exists()

    def test_source_not_under_sources_prefix_returns_400(self, bank_env):
        resp = _build(source="banks/foo/questions.generated.json")
        assert resp.status_code == 400
        assert "sources/" in resp.json()["detail"]

    def test_source_with_dotdot_prefix_returns_400(self, bank_env):
        # "runs/../sources/file.md" does NOT start with "sources/"
        resp = _build(source="runs/../sources/sample_source.md")
        assert resp.status_code == 400

    def test_path_traversal_returns_400(self, bank_env):
        resp = _build(source="../anything")
        assert resp.status_code == 400

    def test_missing_source_file_returns_400(self, bank_env):
        resp = _build(source="sources/nonexistent.md")
        assert resp.status_code == 400


class TestGetGeneratedBank:
    def test_returns_questions_after_build(self, bank_env):
        _build()
        resp = client.get("/api/banks/compactness/generated")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_returns_404_before_build(self, bank_env):
        resp = client.get("/api/banks/compactness/generated")
        assert resp.status_code == 404

    def test_invalid_concept_id_returns_404(self, bank_env):
        # validate_slug raises ValueError → mapped to 404 in router
        resp = client.get("/api/banks/../evil/generated")
        # FastAPI normalises the path, so this may 404 or 400 — just not 200
        assert resp.status_code in (400, 404, 422)

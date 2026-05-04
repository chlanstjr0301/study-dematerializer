"""
Tests for GET /api/concepts and POST /api/concepts/{concept_id}/compile.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_SAMPLE_SOURCE = Path("tests/data/sample_source.md")


@pytest.fixture()
def compiler_env(tmp_path: Path, monkeypatch):
    """
    Isolated data root: sources/ with sample_source.md, empty banks/ and runs/.
    Monkeypatches all path config attrs and the concept_service module's imports.
    """
    import apps.api.config as cfg
    import apps.api.services.concept_service as svc

    sources_dir = tmp_path / "sources"
    sources_dir.mkdir(parents=True)
    shutil.copy(_SAMPLE_SOURCE, sources_dir / "sample_source.md")

    bank_root = tmp_path / "banks"
    runs_dir = tmp_path / "runs"
    study_md = tmp_path / "STUDY.md"

    monkeypatch.setattr(cfg, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(cfg, "BANK_ROOT", bank_root)
    monkeypatch.setattr(cfg, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)

    return {
        "tmp_path": tmp_path,
        "bank_root": bank_root,
        "runs_dir": runs_dir,
        "study_md": study_md,
    }


def _compile(concept_id="compactness", source="sources/sample_source.md", doc_id="sample"):
    return client.post(f"/api/concepts/{concept_id}/compile", json={
        "source_relative_path": source,
        "document_id": doc_id,
    })


# ---------------------------------------------------------------------------
# GET /api/concepts
# ---------------------------------------------------------------------------

class TestListConcepts:
    def test_get_concepts_returns_list(self):
        resp = client.get("/api/concepts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_concepts_contains_all_three_seed_concepts(self):
        resp = client.get("/api/concepts")
        ids = {c["concept_id"] for c in resp.json()}
        assert "compactness" in ids
        assert "connectedness" in ids
        assert "uniform_continuity" in ids

    def test_concept_items_have_required_fields(self):
        resp = client.get("/api/concepts")
        for item in resp.json():
            assert "concept_id" in item
            assert "canonical_name" in item
            assert "domain" in item
            assert "prerequisites" in item
            assert isinstance(item["prerequisites"], list)


# ---------------------------------------------------------------------------
# POST /api/concepts/{concept_id}/compile
# ---------------------------------------------------------------------------

class TestCompileConcept:
    def test_compile_returns_201(self, compiler_env):
        resp = _compile()
        assert resp.status_code == 201

    def test_compile_response_fields_present(self, compiler_env):
        resp = _compile()
        data = resp.json()
        assert "session_id" in data
        assert "concept_id" in data
        assert data["concept_id"] == "compactness"
        assert data["representation_count"] == 5
        assert "prerequisite_count" in data
        assert "misconception_count" in data
        assert "question_count" in data
        assert "bank_dir" in data

    def test_compile_writes_questions_generated_json(self, compiler_env):
        _compile()
        bank_dir = compiler_env["bank_root"] / "compactness"
        assert (bank_dir / "questions.generated.json").exists()
        questions = json.loads((bank_dir / "questions.generated.json").read_text(encoding="utf-8"))
        assert isinstance(questions, list)
        assert len(questions) > 0

    def test_compile_writes_representation_set_to_bank(self, compiler_env):
        _compile()
        bank_dir = compiler_env["bank_root"] / "compactness"
        assert (bank_dir / "representation_set.json").exists()
        rep_set = json.loads((bank_dir / "representation_set.json").read_text(encoding="utf-8"))
        assert isinstance(rep_set, dict)
        assert "formal" in rep_set

    def test_compile_updates_study_md_concept_record(self, compiler_env):
        _compile()
        study_md = compiler_env["study_md"]
        assert study_md.exists()
        content = study_md.read_text(encoding="utf-8")
        assert "compactness" in content

    def test_compile_study_md_has_prerequisites(self, compiler_env):
        _compile()
        content = compiler_env["study_md"].read_text(encoding="utf-8")
        assert "metric_space" in content or "open_set" in content

    def test_compile_study_md_has_misconceptions(self, compiler_env):
        _compile()
        content = compiler_env["study_md"].read_text(encoding="utf-8")
        assert "Misconceptions" in content

    def test_compile_unknown_concept_returns_422(self, compiler_env):
        resp = _compile(concept_id="banana")
        assert resp.status_code == 422

    def test_compile_source_not_under_sources_returns_400(self, compiler_env):
        resp = _compile(source="banks/foo.md")
        assert resp.status_code == 400
        assert "sources/" in resp.json()["detail"]

    def test_compile_missing_source_file_returns_400(self, compiler_env):
        resp = _compile(source="sources/nonexistent.md")
        assert resp.status_code == 400

    def test_compile_question_count_positive(self, compiler_env):
        resp = _compile()
        assert resp.json()["question_count"] > 0

    def test_compile_session_artifacts_written(self, compiler_env):
        resp = _compile()
        session_id = resp.json()["session_id"]
        run_dir = compiler_env["runs_dir"] / session_id
        assert (run_dir / "recall_tasks.json").exists()
        assert (run_dir / "representation_set.json").exists()
        assert (run_dir / "prerequisite_graph.json").exists()
        assert (run_dir / "diagnosis.json").exists()

"""
Tests for GET /api/bank and GET /api/bank/{concept_id}.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.bank_service as bank_svc
from apps.api.services.bank_service import safe_resolve_under

client = TestClient(app)


@pytest.fixture()
def bank_root(tmp_path: Path) -> Path:
    """Create a minimal bank directory with one accepted question bank."""
    concept_dir = tmp_path / "compactness"
    concept_dir.mkdir(parents=True)

    question = {
        "question_id": "q_sample_b000000_def_v1",
        "document_id": "sample",
        "source_block_id": "sample_b000000",
        "question_type": "definition",
        "difficulty": "medium",
        "question": "What is compactness?",
        "expected_answer": "A set K is compact if every open cover has a finite subcover.",
        "rule_id": "def_v1",
        "status": "accepted",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "evidence": {
            "source_text": "A set K is compact if every open cover of K has a finite subcover.",
            "source_file": "tests/data/sample_source.md",
            "start_line": 1,
            "end_line": 2,
            "text_hash": "abc123",
        },
    }
    (concept_dir / "questions.accepted.json").write_text(
        json.dumps([question], indent=2), encoding="utf-8"
    )
    return tmp_path


class TestSafeResolveUnder:
    def test_valid_path(self, tmp_path):
        result = safe_resolve_under(tmp_path, "subdir/file.json")
        assert result == (tmp_path / "subdir/file.json").resolve()

    def test_path_traversal_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Path traversal"):
            safe_resolve_under(tmp_path, "../../etc/passwd")

    def test_double_dot_in_middle_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Path traversal"):
            safe_resolve_under(tmp_path, "a/../../../etc/shadow")


class TestListBanks:
    def test_returns_empty_when_no_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", tmp_path / "nonexistent")
        resp = client.get("/api/bank")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_bank_list(self, bank_root, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", bank_root)
        resp = client.get("/api/bank")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["concept_id"] == "compactness"
        assert data[0]["question_count"] == 1

    def test_schema_fields(self, bank_root, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", bank_root)
        resp = client.get("/api/bank")
        item = resp.json()[0]
        assert "concept_id" in item
        assert "question_count" in item


class TestGetBank:
    def test_returns_questions(self, bank_root, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", bank_root)
        resp = client.get("/api/bank/compactness")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "q_sample_b000000_def_v1"
        assert data[0]["question"] == "What is compactness?"

    def test_question_item_schema(self, bank_root, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", bank_root)
        resp = client.get("/api/bank/compactness")
        item = resp.json()[0]
        assert "id" in item
        assert "question" in item
        assert "question_type" in item
        assert "expected_answer" in item
        assert "status" in item

    def test_404_for_missing_concept(self, bank_root, monkeypatch):
        monkeypatch.setattr(bank_svc.config, "BANK_ROOT", bank_root)
        resp = client.get("/api/bank/nonexistent_concept")
        assert resp.status_code == 404

"""
Tests for POST /api/banks/{concept_id}/review and POST /api/banks/{concept_id}/export-accepted.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.banks_service as banks_svc

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_QUESTION_1 = {
    "question_id": "q_sample_b000000_R01_definition_recall",
    "document_id": "sample",
    "source_block_id": "sample_b000000",
    "question_type": "definition_recall",
    "difficulty": "medium",
    "question": "What is compactness?",
    "expected_answer": "A set K is compact if every open cover has a finite subcover.",
    "rule_id": "R01_definition_recall",
    "status": "candidate",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "evidence": {
        "source_text": "A set K is compact if every open cover has a finite subcover.",
        "source_file": "tests/data/sample_source.md",
        "start_line": 1,
        "end_line": 2,
        "text_hash": "abc123",
    },
}

_QUESTION_2 = {
    **_QUESTION_1,
    "question_id": "q_sample_b000000_R02_example_recall",
    "question_type": "example_recall",
    "rule_id": "R02_example_recall",
    "question": "Give an example of a compact set.",
    "expected_answer": "[0, 1] is compact.",
    "status": "candidate",
}


@pytest.fixture()
def review_env(tmp_path: Path, monkeypatch):
    """
    Set up a tmp bank_dir with questions.generated.json pre-populated.
    Patches banks_service.config.BANK_ROOT.
    """
    import apps.api.config as cfg

    bank_root = tmp_path / "banks"
    concept_dir = bank_root / "compactness"
    concept_dir.mkdir(parents=True)

    (concept_dir / "questions.generated.json").write_text(
        json.dumps([_QUESTION_1, _QUESTION_2], indent=2), encoding="utf-8"
    )

    monkeypatch.setattr(cfg, "BANK_ROOT", bank_root)
    return bank_root


class TestReviewBank:
    def test_accept_reject_returns_counts(self, review_env):
        resp = client.post("/api/banks/compactness/review", json={
            "actions": [
                {"question_id": _QUESTION_1["question_id"], "action": "accept"},
                {"question_id": _QUESTION_2["question_id"], "action": "reject"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["accepted"] == 1
        assert data["rejected"] == 1
        assert data["edited"] == 0
        assert data["skipped"] == 0

    def test_edit_action(self, review_env):
        resp = client.post("/api/banks/compactness/review", json={
            "actions": [{
                "question_id": _QUESTION_1["question_id"],
                "action": "edit",
                "updated_question": "Revised question text.",
                "updated_expected_answer": "Revised answer.",
            }]
        })
        assert resp.status_code == 200
        assert resp.json()["edited"] == 1

    def test_skip_action(self, review_env):
        resp = client.post("/api/banks/compactness/review", json={
            "actions": [{"question_id": _QUESTION_1["question_id"], "action": "skip"}]
        })
        assert resp.status_code == 200
        assert resp.json()["skipped"] == 1

    def test_reviewed_json_written(self, review_env):
        client.post("/api/banks/compactness/review", json={
            "actions": [{"question_id": _QUESTION_1["question_id"], "action": "accept"}]
        })
        assert (review_env / "compactness" / "questions.reviewed.json").exists()

    def test_review_records_json_written(self, review_env):
        client.post("/api/banks/compactness/review", json={
            "actions": [{"question_id": _QUESTION_1["question_id"], "action": "accept"}]
        })
        assert (review_env / "compactness" / "review_records.json").exists()

    def test_returns_404_when_no_bank(self, review_env):
        resp = client.post("/api/banks/nonexistent/review", json={
            "actions": [{"question_id": "q_any", "action": "accept"}]
        })
        assert resp.status_code == 404


class TestExportAccepted:
    def _do_review(self, concept_id="compactness"):
        client.post(f"/api/banks/{concept_id}/review", json={
            "actions": [
                {"question_id": _QUESTION_1["question_id"], "action": "accept"},
                {"question_id": _QUESTION_2["question_id"], "action": "reject"},
            ]
        })

    def test_export_writes_accepted_json(self, review_env):
        self._do_review()
        resp = client.post("/api/banks/compactness/export-accepted")
        assert resp.status_code == 200
        assert resp.json()["accepted_count"] == 1
        assert (review_env / "compactness" / "questions.accepted.json").exists()

    def test_export_only_accepted_questions(self, review_env):
        self._do_review()
        client.post("/api/banks/compactness/export-accepted")
        data = json.loads(
            (review_env / "compactness" / "questions.accepted.json").read_text(encoding="utf-8")
        )
        assert len(data) == 1
        assert data[0]["question_id"] == _QUESTION_1["question_id"]

    def test_export_returns_404_without_review(self, review_env):
        resp = client.post("/api/banks/compactness/export-accepted")
        assert resp.status_code == 404

    def test_accepted_bank_visible_via_existing_endpoint(self, review_env):
        self._do_review()
        client.post("/api/banks/compactness/export-accepted")
        # GET /api/bank/{concept_id} returns a list of QuestionItem
        resp = client.get("/api/bank/compactness")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

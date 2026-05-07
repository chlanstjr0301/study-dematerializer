"""
Tests for blank-answer handling in POST /api/sessions.

Blank answers must score 0.0 and appear as weak questions in recall_feedback.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.session_service as session_svc

client = TestClient(app)

_SAMPLE_QUESTION = {
    "question_id": "q_blank_test_01",
    "document_id": "doc",
    "source_block_id": "doc_b000001",
    "question_type": "definition_recall",
    "difficulty": "medium",
    "question": "State the definition of compactness.",
    "expected_answer": "A compact set is one where every open cover has a finite subcover.",
    "evidence": {
        "source_text": "A compact set is one where every open cover has a finite subcover.",
        "source_file": "test.md",
        "start_line": 1,
        "end_line": 3,
        "text_hash": "abc123",
    },
    "rule_id": "R01_definition_recall",
    "status": "accepted",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}

_SAMPLE_QUESTION_2 = {
    **_SAMPLE_QUESTION,
    "question_id": "q_blank_test_02",
    "question": "Explain the intuition behind compactness.",
    "question_type": "intuition_recall",
}


@pytest.fixture()
def session_env(tmp_path: Path, monkeypatch):
    bank_root = tmp_path / "banks"
    concept_dir = bank_root / "compactness"
    concept_dir.mkdir(parents=True)
    (concept_dir / "questions.accepted.json").write_text(
        json.dumps([_SAMPLE_QUESTION, _SAMPLE_QUESTION_2], indent=2),
        encoding="utf-8",
    )
    study_md = tmp_path / "STUDY.md"
    study_md.write_text(
        "# STUDY.md\n\n## compactness\n\n"
        "**domain**: real_analysis\n"
        "**overall_mastery**: unknown\n"
        "**next_review**: 2026-01-01\n",
        encoding="utf-8",
    )
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(session_svc.config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(session_svc.config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(session_svc.config, "STUDY_MD", study_md)
    return {"runs_dir": runs_dir}


class TestBlankAnswersScoreZero:
    """Blank answers must produce accuracy_score=0.0 in recall_feedback."""

    def test_all_blank_answers_score_zero(self, session_env):
        resp = client.post("/api/sessions", json={
            "concept_id": "compactness",
            "questions_path": "compactness/questions.accepted.json",
            "grader": "mock",
            "answers": [
                {"question_id": "q_blank_test_01", "learner_response": ""},
                {"question_id": "q_blank_test_02", "learner_response": ""},
            ],
        })
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        fb_resp = client.get(f"/api/sessions/{session_id}/visualization/recall_feedback")
        assert fb_resp.status_code == 200
        feedback = fb_resp.json()
        for item in feedback:
            assert item["accuracy_score"] == 0.0, (
                f"Blank answer for {item['question_id']} scored {item['accuracy_score']}, expected 0.0"
            )

    def test_whitespace_only_scores_zero(self, session_env):
        resp = client.post("/api/sessions", json={
            "concept_id": "compactness",
            "questions_path": "compactness/questions.accepted.json",
            "grader": "mock",
            "answers": [
                {"question_id": "q_blank_test_01", "learner_response": "   \t\n  "},
                {"question_id": "q_blank_test_02", "learner_response": "  "},
            ],
        })
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        fb_resp = client.get(f"/api/sessions/{session_id}/visualization/recall_feedback")
        feedback = fb_resp.json()
        for item in feedback:
            assert item["accuracy_score"] == 0.0

    def test_mixed_blank_and_filled(self, session_env):
        """One blank, one filled: blank scores 0.0, filled scores > 0."""
        resp = client.post("/api/sessions", json={
            "concept_id": "compactness",
            "questions_path": "compactness/questions.accepted.json",
            "grader": "mock",
            "answers": [
                {"question_id": "q_blank_test_01", "learner_response": ""},
                {"question_id": "q_blank_test_02", "learner_response": "Compactness means every open cover has a finite subcover."},
            ],
        })
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        fb_resp = client.get(f"/api/sessions/{session_id}/visualization/recall_feedback")
        feedback = fb_resp.json()
        by_id = {f["question_id"]: f for f in feedback}
        assert by_id["q_blank_test_01"]["accuracy_score"] == 0.0
        assert by_id["q_blank_test_02"]["accuracy_score"] > 0.0

    def test_blank_mastery_is_unknown(self, session_env):
        """Mastery map should show unknown for blank answers."""
        resp = client.post("/api/sessions", json={
            "concept_id": "compactness",
            "questions_path": "compactness/questions.accepted.json",
            "grader": "mock",
            "answers": [
                {"question_id": "q_blank_test_01", "learner_response": ""},
                {"question_id": "q_blank_test_02", "learner_response": ""},
            ],
        })
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        mm_resp = client.get(f"/api/sessions/{session_id}/visualization/mastery_map")
        assert mm_resp.status_code == 200
        mastery = mm_resp.json()
        assert mastery["overall_mastery"] == "unknown"

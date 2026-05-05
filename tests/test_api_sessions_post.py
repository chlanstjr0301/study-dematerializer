"""
Tests for POST /api/sessions — MVP4-B (grader=mock).

All tests run without OPENAI_API_KEY.
Config is injected via monkeypatch so no real data directories are touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.session_service as session_svc

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SAMPLE_QUESTION = {
    "question_id": "q_doc_b000001_R01",
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


@pytest.fixture()
def session_env(tmp_path: Path, monkeypatch):
    """
    Set up a minimal bank + STUDY.md + runs_dir in tmp_path.

    Patches session_svc.config so the service uses tmp_path locations.
    """
    bank_root = tmp_path / "banks"
    concept_dir = bank_root / "compactness"
    concept_dir.mkdir(parents=True)
    (concept_dir / "questions.accepted.json").write_text(
        json.dumps([_SAMPLE_QUESTION], indent=2), encoding="utf-8"
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

    return {
        "bank_root": bank_root,
        "study_md": study_md,
        "runs_dir": runs_dir,
        "questions_path": "compactness/questions.accepted.json",
    }


# ---------------------------------------------------------------------------
# grader=mock + default_answer
# ---------------------------------------------------------------------------

class TestMockGraderDefaultAnswer:
    def _post(self, env, **extra):
        payload = {
            "concept_id": "compactness",
            "questions_path": env["questions_path"],
            "grader": "mock",
            "default_answer": "Every open cover has a finite subcover.",
            **extra,
        }
        return client.post("/api/sessions", json=payload)

    def test_returns_201(self, session_env):
        resp = self._post(session_env)
        assert resp.status_code == 201

    def test_response_has_session_id(self, session_env):
        data = self._post(session_env).json()
        assert "session_id" in data
        assert data["session_id"]

    def test_response_has_summary_md(self, session_env):
        data = self._post(session_env).json()
        assert "summary_md" in data

    def test_response_has_attempt_count(self, session_env):
        data = self._post(session_env).json()
        assert data["attempt_count"] == 1  # one question in the bank

    def test_session_dir_written(self, session_env):
        resp = self._post(session_env)
        session_id = resp.json()["session_id"]
        runs_dir = session_env["runs_dir"]
        assert (runs_dir / session_id).is_dir()

    def test_session_json_written(self, session_env):
        resp = self._post(session_env)
        session_id = resp.json()["session_id"]
        runs_dir = session_env["runs_dir"]
        assert (runs_dir / session_id / "session.json").exists()

    def test_recall_attempts_written(self, session_env):
        resp = self._post(session_env)
        session_id = resp.json()["session_id"]
        runs_dir = session_env["runs_dir"]
        assert (runs_dir / session_id / "recall_attempts.json").exists()

    def test_mastery_map_visualization_written(self, session_env):
        resp = self._post(session_env)
        session_id = resp.json()["session_id"]
        runs_dir = session_env["runs_dir"]
        assert (runs_dir / session_id / "visualization" / "mastery_map.json").exists()

    def test_all_visualization_artifacts_present(self, session_env):
        resp = self._post(session_env)
        session_id = resp.json()["session_id"]
        viz_dir = session_env["runs_dir"] / session_id / "visualization"
        for name in ("mastery_map.json", "recall_feedback.json", "review_queue.json",
                     "mastery_map.mmd", "session_flow.mmd"):
            assert (viz_dir / name).exists(), f"Missing: {name}"


# ---------------------------------------------------------------------------
# grader=mock + explicit per-question answers
# ---------------------------------------------------------------------------

class TestMockGraderExplicitAnswers:
    def test_returns_201(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "mock",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "A compact set has a finite open subcover.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201

    def test_explicit_answers_appear_in_artifacts(self, session_env):
        """
        Verify that the submitted learner_response is persisted in recall_attempts.json.
        This guards against silently falling back to empty string or default_answer.
        """
        submitted_response = "My unique explicit answer for compactness Q001"
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "mock",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": submitted_response,
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201

        session_id = resp.json()["session_id"]
        attempts_path = session_env["runs_dir"] / session_id / "recall_attempts.json"
        assert attempts_path.exists()

        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
        recorded_responses = [a["learner_response"] for a in attempts]
        assert submitted_response in recorded_responses

    def test_attempt_count_matches(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "mock",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "compact means finite subcover",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.json()["attempt_count"] == 1


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestValidationErrors:
    def test_path_traversal_returns_400(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": "../../etc/passwd",
            "grader": "mock",
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

    def test_grader_llm_no_api_key_returns_400(self, session_env, monkeypatch):
        """grader=llm with no OPENAI_API_KEY → 400 (LLMAPIKeyError caught as ValueError)."""
        import os
        monkeypatch.setattr(session_svc.config, "LLM_DISABLED", False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "default_answer": "Some answer",
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

    def test_grader_llm_disabled_returns_400(self, session_env, monkeypatch):
        """GONGHAEBUN_LLM_DISABLED=1 → 400 regardless of API key."""
        monkeypatch.setattr(session_svc.config, "LLM_DISABLED", True)
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "default_answer": "Some answer",
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

    def test_grader_self_missing_self_score_returns_400(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "self",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Some answer",
                    # self_score intentionally omitted
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

    def test_grader_self_no_answers_returns_400(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "self",
            # no answers key
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

    def test_grader_self_with_valid_self_score_returns_501(self, session_env):
        """grader=self with valid self_score is deferred to MVP4-E — returns 501."""
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "self",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Some answer",
                    "self_score": 2,
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# Round-trip: POST then GET
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_get_session_after_post(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "mock",
            "default_answer": "compact means finite subcover",
        }
        post_resp = client.post("/api/sessions", json=payload)
        assert post_resp.status_code == 201
        session_id = post_resp.json()["session_id"]

        # Also patch RUNS_DIR for the GET endpoint
        import apps.api.services.session_service as svc
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "compactness" in data["session"]["concept_ids"]
        assert len(data["attempts"]) == 1

    def test_get_visualization_mastery_map_after_post(self, session_env):
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "mock",
            "default_answer": "compact means finite subcover",
        }
        post_resp = client.post("/api/sessions", json=payload)
        assert post_resp.status_code == 201
        session_id = post_resp.json()["session_id"]

        viz_resp = client.get(f"/api/sessions/{session_id}/visualization/mastery_map")
        assert viz_resp.status_code == 200
        data = viz_resp.json()
        assert "concept_id" in data
        assert data["concept_id"] == "compactness"

"""
Integration tests for POST /api/sessions with grader="llm".

Uses fake LLM clients (monkeypatching make_grader) so no real OpenAI calls
are made. Tests verify session creation, trace artifact layout, and fallback
behavior.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.services.session_service as session_svc
import gonghaebun.grading.factory as grading_factory

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

_VALID_LLM_OUTPUT = {
    "accuracy_score": 0.8,
    "mastery_after": "partial",
    "missing_elements": [],
    "errors": [],
    "misconception_flags": [],
    "evidence_alignment_score": 0.85,
    "needs_human_review": False,
    "short_feedback": "Good answer.",
}

_INVALID_LLM_OUTPUT = {
    "accuracy_score": 0.5,
    "mastery_after": "INVALID_VALUE",  # will fail validate_llm_output
    "missing_elements": [],
    "errors": [],
    "misconception_flags": [],
    "evidence_alignment_score": 0.5,
    "needs_human_review": False,
    "short_feedback": "OK.",
}


@pytest.fixture()
def session_env(tmp_path: Path, monkeypatch):
    """Set up minimal bank + STUDY.md + runs_dir in tmp_path."""
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
    monkeypatch.setattr(session_svc.config, "LLM_DISABLED", False)

    return {
        "bank_root": bank_root,
        "study_md": study_md,
        "runs_dir": runs_dir,
        "questions_path": "compactness/questions.accepted.json",
    }


def _fake_llm_grader(output_dict: dict):
    """Return a make_grader replacement that produces an LLMGrader with a fake client."""
    from gonghaebun.grading.llm_grader import LLMGrader
    mock_client = MagicMock()
    mock_client.complete_structured.return_value = output_dict
    mock_client._model = "fake-model"

    def _make(grader: str, model=None):
        if grader == "llm":
            return LLMGrader(mock_client, max_calls=20, timeout=30.0)
        # Fallback for other grader types (mock)
        from gonghaebun.grading.factory import make_grader as real_make
        return real_make(grader, model)

    return _make


# ---------------------------------------------------------------------------
# TestLLMGraderAPIPath
# ---------------------------------------------------------------------------


class TestLLMGraderAPIPath:
    def test_llm_grader_returns_201(self, session_env, monkeypatch):
        monkeypatch.setattr(grading_factory, "make_grader", _fake_llm_grader(_VALID_LLM_OUTPUT))
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Every open cover has a finite subcover.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201

    def test_llm_traces_dir_created(self, session_env, monkeypatch):
        monkeypatch.setattr(grading_factory, "make_grader", _fake_llm_grader(_VALID_LLM_OUTPUT))
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Every open cover has a finite subcover.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]
        traces_dir = session_env["runs_dir"] / session_id / "llm_traces"
        assert traces_dir.is_dir()

    def test_one_trace_file_per_question(self, session_env, monkeypatch):
        monkeypatch.setattr(grading_factory, "make_grader", _fake_llm_grader(_VALID_LLM_OUTPUT))
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Every open cover has a finite subcover.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]
        traces_dir = session_env["runs_dir"] / session_id / "llm_traces"
        files = list(traces_dir.iterdir())
        assert len(files) == 1  # one question → one file

    def test_trace_file_contains_attempts_key(self, session_env, monkeypatch):
        monkeypatch.setattr(grading_factory, "make_grader", _fake_llm_grader(_VALID_LLM_OUTPUT))
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Every open cover has a finite subcover.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        session_id = resp.json()["session_id"]
        traces_dir = session_env["runs_dir"] / session_id / "llm_traces"
        trace_file = next(traces_dir.iterdir())
        data = json.loads(trace_file.read_text("utf-8"))
        assert "attempts" in data
        assert isinstance(data["attempts"], list)

    def test_fallback_on_bad_schema_still_returns_201(self, session_env, monkeypatch):
        """LLM returning invalid schema → fallback (needs_human_review) → session still 201."""
        monkeypatch.setattr(grading_factory, "make_grader", _fake_llm_grader(_INVALID_LLM_OUTPUT))
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "answers": [
                {
                    "question_id": "q_doc_b000001_R01",
                    "learner_response": "Some answer.",
                }
            ],
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 201

    def test_llm_disabled_env_returns_400(self, session_env, monkeypatch):
        monkeypatch.setattr(session_svc.config, "LLM_DISABLED", True)
        payload = {
            "concept_id": "compactness",
            "questions_path": session_env["questions_path"],
            "grader": "llm",
            "default_answer": "Some answer",
        }
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400

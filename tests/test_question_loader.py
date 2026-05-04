"""Tests for study_loop/question_loader.py (MVP3 Step 4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gonghaebun.models.question_bank import Question
from gonghaebun.study_loop.question_loader import load_recall_questions

# Use the existing sample bank fixture
SAMPLE_BANK = Path(__file__).parent / "data" / "sample_source.md"


# ---------------------------------------------------------------------------
# Helpers — build a minimal questions.accepted.json on the fly
# ---------------------------------------------------------------------------

_SAMPLE_QUESTION = {
    "question_id": "q_doc_b000001_R01",
    "document_id": "doc",
    "source_block_id": "doc_b000001",
    "question_type": "definition_recall",
    "difficulty": "medium",
    "question": "State the definition.",
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


def write_questions(path: Path, questions: list[dict]) -> None:
    path.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# TestLoadRecallQuestions
# ---------------------------------------------------------------------------


class TestLoadRecallQuestions:
    def test_returns_list_of_questions(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION])
        result = load_recall_questions(p)
        assert all(isinstance(q, Question) for q in result)

    def test_loads_all_questions_by_default(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION] * 5)
        result = load_recall_questions(p)
        assert len(result) == 5

    def test_limit_caps_results(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        qs = []
        for i in range(7):
            q = dict(_SAMPLE_QUESTION)
            q["question_id"] = f"q_doc_b{i:06d}_R01"
            qs.append(q)
        write_questions(p, qs)
        result = load_recall_questions(p, limit=3)
        assert len(result) == 3

    def test_limit_greater_than_count_returns_all(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION] * 2)
        result = load_recall_questions(p, limit=100)
        assert len(result) == 2

    def test_empty_file_returns_empty_list(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [])
        result = load_recall_questions(p)
        assert result == []

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_recall_questions(tmp_path / "nonexistent.json")

    def test_accepts_string_path(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION])
        result = load_recall_questions(str(p))
        assert len(result) == 1

    def test_question_evidence_is_evidence_object(self, tmp_path):
        from gonghaebun.models.question_bank import Evidence

        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION])
        result = load_recall_questions(p)
        assert isinstance(result[0].evidence, Evidence)

    def test_limit_none_loads_all(self, tmp_path):
        p = tmp_path / "questions.accepted.json"
        write_questions(p, [_SAMPLE_QUESTION] * 4)
        result = load_recall_questions(p, limit=None)
        assert len(result) == 4

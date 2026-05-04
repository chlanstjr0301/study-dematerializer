"""Tests for MVP3 CLI subcommands: review-bank, recall-session, review-due.

Also includes regression tests that run the pre-existing study / build-bank
commands to verify they are not broken by the Step 7 changes.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gonghaebun.cli import main
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Evidence, Question

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_EVIDENCE = Evidence(
    source_text="A compact set has every open cover admitting a finite subcover.",
    source_file="test.md",
    start_line=1,
    end_line=3,
    text_hash="abc123",
)

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


def write_accepted_questions(path: Path, n: int = 1) -> None:
    qs = []
    for i in range(n):
        q = dict(_SAMPLE_QUESTION)
        q["question_id"] = f"q_doc_b{i:06d}_R01"
        qs.append(q)
    path.write_text(json.dumps(qs, ensure_ascii=False, indent=2), encoding="utf-8")


def write_generated_questions(path: Path) -> None:
    q = dict(_SAMPLE_QUESTION)
    q["status"] = "candidate"
    path.write_text(json.dumps([q], ensure_ascii=False, indent=2), encoding="utf-8")


def _make_grading_result() -> GradingResult:
    from gonghaebun.study_md.writer import compute_mastery_state
    return GradingResult(
        accuracy_score=0.75,
        mastery_suggestion=compute_mastery_state(0.75),
        raw_response="raw",
    )


# ---------------------------------------------------------------------------
# TestReviewBankCommand
# ---------------------------------------------------------------------------


class TestReviewBankCommand:
    def test_missing_questions_file_returns_2(self, tmp_path):
        rc = main([
            "review-bank",
            "--questions", str(tmp_path / "nonexistent.json"),
            "--output-dir", str(tmp_path / "out"),
        ])
        assert rc == 2

    def test_runs_review_cli_and_returns_0(self, tmp_path):
        q_path = tmp_path / "questions.generated.json"
        write_generated_questions(q_path)

        # run_review_cli is imported locally inside _cmd_review_bank, so patch at source
        with patch("gonghaebun.review.review_cli.run_review_cli", return_value=[]):
            rc = main([
                "review-bank",
                "--questions", str(q_path),
                "--output-dir", str(tmp_path / "out"),
            ])
        assert rc == 0

    def test_review_bank_eof_returns_0(self, tmp_path, monkeypatch):
        """EOF during review (piped input exhausted) should exit cleanly."""
        q_path = tmp_path / "questions.generated.json"
        write_generated_questions(q_path)
        out_dir = tmp_path / "out"

        # input() receives the prompt string as arg — lambda must accept it
        monkeypatch.setattr("builtins.input", lambda _="": (_ for _ in ()).throw(EOFError()))
        rc = main([
            "review-bank",
            "--questions", str(q_path),
            "--output-dir", str(out_dir),
        ])
        assert rc == 0


# ---------------------------------------------------------------------------
# TestRecallSessionCommand
# ---------------------------------------------------------------------------


class TestRecallSessionCommand:
    def _run_no_interactive_mock(self, tmp_path, extra_args=None):
        q_path = tmp_path / "questions.accepted.json"
        write_accepted_questions(q_path, n=2)
        study_md = tmp_path / "STUDY.md"
        runs_dir = tmp_path / "runs"
        argv = [
            "recall-session",
            "--questions", str(q_path),
            "--concept", "compactness",
            "--study-md", str(study_md),
            "--runs-dir", str(runs_dir),
            "--grader", "mock",
            "--no-interactive",
        ]
        if extra_args:
            argv += extra_args
        return main(argv)

    def test_returns_0_on_success(self, tmp_path):
        rc = self._run_no_interactive_mock(tmp_path)
        assert rc == 0

    def test_creates_study_md(self, tmp_path):
        self._run_no_interactive_mock(tmp_path)
        assert (tmp_path / "STUDY.md").exists()

    def test_creates_runs_dir(self, tmp_path):
        self._run_no_interactive_mock(tmp_path)
        assert (tmp_path / "runs").is_dir()

    def test_creates_session_json(self, tmp_path):
        self._run_no_interactive_mock(tmp_path)
        runs = list((tmp_path / "runs").iterdir())
        assert any((d / "session.json").exists() for d in runs)

    def test_missing_questions_returns_2(self, tmp_path):
        rc = main([
            "recall-session",
            "--questions", str(tmp_path / "missing.json"),
            "--concept", "compactness",
            "--grader", "mock",
            "--no-interactive",
        ])
        assert rc == 2

    def test_limit_flag_respected(self, tmp_path):
        q_path = tmp_path / "questions.accepted.json"
        write_accepted_questions(q_path, n=5)
        study_md = tmp_path / "STUDY.md"
        runs_dir = tmp_path / "runs"
        rc = main([
            "recall-session",
            "--questions", str(q_path),
            "--concept", "compactness",
            "--study-md", str(study_md),
            "--runs-dir", str(runs_dir),
            "--grader", "mock",
            "--no-interactive",
            "--limit", "2",
        ])
        assert rc == 0
        runs = list(runs_dir.iterdir())
        session_data = json.loads((runs[0] / "session.json").read_text("utf-8"))
        assert len(session_data["recall_attempts"]) == 2

    def test_no_interactive_llm_without_default_answer_prints_warning(
        self, tmp_path, capsys
    ):
        q_path = tmp_path / "questions.accepted.json"
        write_accepted_questions(q_path, n=1)
        # We don't have a real API key; patch OpenAIClient init
        with patch("gonghaebun.llm.openai_client.OpenAIClient.__init__", return_value=None):
            with patch("gonghaebun.grading.llm_grader.LLMGrader.grade") as mock_grade:
                mock_grade.return_value = _make_grading_result()
                main([
                    "recall-session",
                    "--questions", str(q_path),
                    "--concept", "compactness",
                    "--study-md", str(tmp_path / "STUDY.md"),
                    "--runs-dir", str(tmp_path / "runs"),
                    "--grader", "llm",
                    "--no-interactive",
                ])
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_self_grader_no_interactive_uses_default_score(self, tmp_path):
        q_path = tmp_path / "questions.accepted.json"
        write_accepted_questions(q_path, n=1)
        study_md = tmp_path / "STUDY.md"
        runs_dir = tmp_path / "runs"

        with patch("gonghaebun.grading.self_grader.SelfGrader.grade") as mock_grade:
            mock_grade.return_value = _make_grading_result()
            rc = main([
                "recall-session",
                "--questions", str(q_path),
                "--concept", "compactness",
                "--study-md", str(study_md),
                "--runs-dir", str(runs_dir),
                "--grader", "self",
                "--no-interactive",
                "--default-score", "3",
            ])
        assert rc == 0


# ---------------------------------------------------------------------------
# TestReviewDueCommand
# ---------------------------------------------------------------------------


def _write_study_md(path: Path, concepts: list[dict]) -> None:
    lines = ["# STUDY.md", ""]
    for c in concepts:
        lines += [
            f"## {c['concept_id']}",
            "",
            f"**domain**: {c.get('domain', 'real_analysis')}",
            f"**overall_mastery**: {c.get('overall_mastery', 'unknown')}",
            f"**next_review**: {c.get('next_review', '—')}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


class TestReviewDueCommand:
    def _setup_bank(self, tmp_path, concept_id: str = "compactness") -> tuple[Path, Path]:
        """Create a bank dir with a concept subdir and accepted questions."""
        bank_root = tmp_path / "bank"
        concept_dir = bank_root / concept_id
        concept_dir.mkdir(parents=True)
        q_path = concept_dir / "questions.accepted.json"
        write_accepted_questions(q_path, n=2)
        return bank_root, q_path

    def test_no_due_concepts_exits_0(self, tmp_path):
        study_md = tmp_path / "STUDY.md"
        _write_study_md(study_md, [
            {"concept_id": "compactness", "next_review": "2030-01-01"},
        ])
        rc = main([
            "review-due",
            "--bank-root", str(tmp_path / "bank"),
            "--study-md", str(study_md),
            "--runs-dir", str(tmp_path / "runs"),
        ])
        assert rc == 0

    def test_due_concept_creates_session(self, tmp_path):
        study_md = tmp_path / "STUDY.md"
        _write_study_md(study_md, [
            {"concept_id": "compactness", "next_review": "2000-01-01"},
        ])
        bank_root, _ = self._setup_bank(tmp_path, "compactness")
        runs_dir = tmp_path / "runs"

        rc = main([
            "review-due",
            "--bank-root", str(bank_root),
            "--study-md", str(study_md),
            "--runs-dir", str(runs_dir),
            "--grader", "mock",
            "--no-interactive",
        ])
        assert rc == 0
        assert runs_dir.is_dir()
        runs = list(runs_dir.iterdir())
        assert len(runs) >= 1
        assert any((d / "session.json").exists() for d in runs)

    def test_missing_bank_returns_2(self, tmp_path):
        study_md = tmp_path / "STUDY.md"
        _write_study_md(study_md, [
            {"concept_id": "compactness", "next_review": "2000-01-01"},
        ])
        rc = main([
            "review-due",
            "--bank-root", str(tmp_path / "bank"),  # no concept subdir
            "--study-md", str(study_md),
            "--runs-dir", str(tmp_path / "runs"),
            "--grader", "mock",
            "--no-interactive",
        ])
        assert rc == 2

    def test_questions_override_skips_bank_lookup(self, tmp_path):
        study_md = tmp_path / "STUDY.md"
        _write_study_md(study_md, [
            {"concept_id": "compactness", "next_review": "2000-01-01"},
        ])
        # Put questions somewhere flat (no concept subdir)
        q_path = tmp_path / "questions.accepted.json"
        write_accepted_questions(q_path, n=1)
        runs_dir = tmp_path / "runs"

        rc = main([
            "review-due",
            "--questions", str(q_path),  # override
            "--study-md", str(study_md),
            "--runs-dir", str(runs_dir),
            "--grader", "mock",
            "--no-interactive",
        ])
        assert rc == 0

    def test_empty_study_md_prints_no_due(self, tmp_path, capsys):
        study_md = tmp_path / "STUDY.md"
        study_md.write_text("# STUDY.md\n", encoding="utf-8")
        rc = main([
            "review-due",
            "--bank-root", str(tmp_path / "bank"),
            "--study-md", str(study_md),
            "--runs-dir", str(tmp_path / "runs"),
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "No concepts" in captured.out

    def test_bank_root_and_no_questions_requires_bank_root_flag(self, tmp_path):
        study_md = tmp_path / "STUDY.md"
        _write_study_md(study_md, [
            {"concept_id": "compactness", "next_review": "2000-01-01"},
        ])
        # Neither --bank-root nor --questions provided
        rc = main([
            "review-due",
            "--study-md", str(study_md),
            "--runs-dir", str(tmp_path / "runs"),
            "--grader", "mock",
            "--no-interactive",
        ])
        assert rc == 2


# ---------------------------------------------------------------------------
# Regression: existing commands still work
# ---------------------------------------------------------------------------


class TestRegressionExistingCommands:
    def test_build_bank_subcommand_still_recognised(self, tmp_path):
        """build-bank exits 2 (source not found) — not NameError or crash."""
        rc = main([
            "build-bank",
            "--source-local", str(tmp_path / "missing.md"),
            "--bank-dir", str(tmp_path / "bank"),
        ])
        assert rc == 2

    def test_study_subcommand_still_recognised(self, tmp_path):
        """study exits 2 (source not found) — not NameError or crash."""
        rc = main([
            "study", "compactness",
            "--source-local", str(tmp_path / "missing.md"),
            "--mock",
        ])
        assert rc == 2

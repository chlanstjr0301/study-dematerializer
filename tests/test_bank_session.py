"""Tests for bank_session.py and the CLI build-bank subcommand (MVP2 Step 7)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gonghaebun.bank_session import run_bank_session
from gonghaebun.cli import main
from gonghaebun.models.question_bank import Question, SourceBlock
from gonghaebun.pipeline.io import load_blocks, load_questions
from gonghaebun.pipeline.question_generator import generate_questions
from gonghaebun.pipeline.rule_engine import RULES, get_rules_for_blocks

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

SAMPLE_SOURCE = Path(__file__).parent / "data" / "sample_source.md"


# ---------------------------------------------------------------------------
# run_bank_session — output files
# ---------------------------------------------------------------------------


class TestRunBankSessionOutputFiles:
    def test_creates_blocks_json(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        assert (tmp_path / "blocks.generated.json").exists()

    def test_creates_questions_json(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        assert (tmp_path / "questions.generated.json").exists()

    def test_output_dir_created_automatically(self, tmp_path):
        out = tmp_path / "nested" / "bank"
        run_bank_session(SAMPLE_SOURCE, "sample", out)
        assert out.is_dir()
        assert (out / "blocks.generated.json").exists()

    def test_blocks_json_is_valid_list(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        data = json.loads((tmp_path / "blocks.generated.json").read_text("utf-8"))
        assert isinstance(data, list)

    def test_questions_json_is_valid_list(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        data = json.loads((tmp_path / "questions.generated.json").read_text("utf-8"))
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# run_bank_session — loaded data validity
# ---------------------------------------------------------------------------


class TestRunBankSessionLoadedData:
    def test_loaded_blocks_are_source_block_objects(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        blocks = load_blocks(tmp_path / "blocks.generated.json")
        assert all(isinstance(b, SourceBlock) for b in blocks)

    def test_loaded_questions_are_question_objects(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        questions = load_questions(tmp_path / "questions.generated.json")
        assert all(isinstance(q, Question) for q in questions)

    def test_all_loaded_questions_have_evidence(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        questions = load_questions(tmp_path / "questions.generated.json")
        from gonghaebun.models.question_bank import Evidence
        assert all(isinstance(q.evidence, Evidence) for q in questions)

    def test_all_loaded_questions_are_candidate(self, tmp_path):
        run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        questions = load_questions(tmp_path / "questions.generated.json")
        assert all(q.status == "candidate" for q in questions)


# ---------------------------------------------------------------------------
# run_bank_session — counts and document_id propagation
# ---------------------------------------------------------------------------


class TestRunBankSessionCounts:
    def test_question_count_equals_applicable_rules(self, tmp_path):
        blocks, questions = run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        rule_map = get_rules_for_blocks(blocks, RULES)
        expected = sum(len(rs) for rs in rule_map.values())
        assert len(questions) == expected

    def test_return_value_blocks_matches_file(self, tmp_path):
        blocks, _ = run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        loaded = load_blocks(tmp_path / "blocks.generated.json")
        assert len(blocks) == len(loaded)

    def test_return_value_questions_matches_file(self, tmp_path):
        _, questions = run_bank_session(SAMPLE_SOURCE, "sample", tmp_path)
        loaded = load_questions(tmp_path / "questions.generated.json")
        assert len(questions) == len(loaded)

    def test_document_id_propagated_to_blocks(self, tmp_path):
        blocks, _ = run_bank_session(SAMPLE_SOURCE, "my_doc", tmp_path)
        assert all(b.document_id == "my_doc" for b in blocks)

    def test_document_id_propagated_to_questions(self, tmp_path):
        _, questions = run_bank_session(SAMPLE_SOURCE, "my_doc", tmp_path)
        assert all(q.document_id == "my_doc" for q in questions)

    def test_block_ids_start_with_document_id(self, tmp_path):
        blocks, _ = run_bank_session(SAMPLE_SOURCE, "my_doc", tmp_path)
        assert all(b.block_id.startswith("my_doc") for b in blocks)


# ---------------------------------------------------------------------------
# run_bank_session — empty / short source
# ---------------------------------------------------------------------------


class TestRunBankSessionEmptySource:
    def test_empty_source_returns_empty_lists(self, tmp_path):
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")
        blocks, questions = run_bank_session(empty, "empty", tmp_path / "out")
        assert blocks == []
        assert questions == []

    def test_empty_source_writes_empty_json_arrays(self, tmp_path):
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")
        out = tmp_path / "out"
        run_bank_session(empty, "empty", out)
        assert json.loads((out / "blocks.generated.json").read_text("utf-8")) == []
        assert json.loads((out / "questions.generated.json").read_text("utf-8")) == []

    def test_all_short_source_produces_no_blocks(self, tmp_path):
        short = tmp_path / "short.md"
        short.write_text("Short.\n", encoding="utf-8")  # < 50 non-ws chars
        blocks, questions = run_bank_session(short, "short", tmp_path / "out")
        assert blocks == []
        assert questions == []


# ---------------------------------------------------------------------------
# CLI — build-bank subcommand
# ---------------------------------------------------------------------------


class TestCliBuildBank:
    def test_cli_returns_zero_on_success(self, tmp_path):
        out = tmp_path / "bank"
        code = main([
            "build-bank",
            "--source-local", str(SAMPLE_SOURCE),
            "--bank-dir", str(out),
        ])
        assert code == 0

    def test_cli_creates_output_files(self, tmp_path):
        out = tmp_path / "bank"
        main([
            "build-bank",
            "--source-local", str(SAMPLE_SOURCE),
            "--bank-dir", str(out),
        ])
        assert (out / "blocks.generated.json").exists()
        assert (out / "questions.generated.json").exists()

    def test_cli_infers_document_id_from_stem(self, tmp_path):
        out = tmp_path / "bank"
        main([
            "build-bank",
            "--source-local", str(SAMPLE_SOURCE),
            "--bank-dir", str(out),
        ])
        blocks = load_blocks(out / "blocks.generated.json")
        assert all(b.document_id == "sample_source" for b in blocks)

    def test_cli_uses_explicit_document_id(self, tmp_path):
        out = tmp_path / "bank"
        main([
            "build-bank",
            "--source-local", str(SAMPLE_SOURCE),
            "--document-id", "custom_doc",
            "--bank-dir", str(out),
        ])
        blocks = load_blocks(out / "blocks.generated.json")
        assert all(b.document_id == "custom_doc" for b in blocks)

    def test_cli_missing_source_returns_nonzero(self, tmp_path):
        code = main([
            "build-bank",
            "--source-local", str(tmp_path / "nonexistent.md"),
            "--bank-dir", str(tmp_path / "bank"),
        ])
        assert code != 0

    def test_cli_creates_nested_bank_dir(self, tmp_path):
        out = tmp_path / "a" / "b" / "c"
        main([
            "build-bank",
            "--source-local", str(SAMPLE_SOURCE),
            "--bank-dir", str(out),
        ])
        assert out.is_dir()

    def test_study_command_still_works(self, tmp_path):
        """Regression: existing study subcommand is unaffected."""
        # --mock is required; --no-interactive prevents stdin prompts
        code = main([
            "study", "compactness",
            "--source-local", str(SAMPLE_SOURCE),
            "--mock",
            "--no-interactive",
            "--runs-dir", str(tmp_path / "runs"),
            "--study-md", str(tmp_path / "STUDY.md"),
        ])
        assert code == 0


# ---------------------------------------------------------------------------
# No MVP1 imports check
# ---------------------------------------------------------------------------


class TestNoMVP1Imports:
    def test_recall_orchestrator_not_imported(self):
        import inspect

        import gonghaebun.bank_session as bs

        src = inspect.getsource(bs)
        assert "recall_orchestrator" not in src

    def test_mvp1_session_not_imported(self):
        import inspect

        import gonghaebun.bank_session as bs

        src = inspect.getsource(bs)
        assert "from gonghaebun.session" not in src

"""Tests for pipeline/io.py (MVP2 Step 5)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from gonghaebun.models.question_bank import (
    Evidence,
    Question,
    ReviewRecord,
    SourceBlock,
)
from gonghaebun.pipeline.io import (
    export_accepted,
    load_blocks,
    load_questions,
    load_review_records,
    save_blocks,
    save_questions,
    save_review_records,
)

# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

_TEXT = (
    "A subset K of a metric space X is compact if every open cover has a "
    "finite subcover. Standard topological definition used in real analysis."
)
_KOREAN_TITLE = "위상수학의 기초"  # "Fundamentals of Topology"


def make_block(
    block_id: str = "doc_b000001",
    block_type: str = "definition",
    section_title: str = "Compactness",
    text: str = _TEXT,
) -> SourceBlock:
    return SourceBlock(
        block_id=block_id,
        document_id="doc",
        source_file="doc.md",
        section_title=section_title,
        block_type=block_type,  # type: ignore[arg-type]
        start_line=5,
        end_line=7,
        text=text,
        text_hash="deadbeef",
    )


def make_evidence(text: str = _TEXT) -> Evidence:
    return Evidence(
        source_text=text,
        source_file="doc.md",
        start_line=5,
        end_line=7,
        text_hash="deadbeef",
    )


def make_question(
    question_id: str = "q_doc_b000001_R01",
    status: str = "candidate",
    section_title: str = "Compactness",
) -> Question:
    return Question(
        question_id=question_id,
        document_id="doc",
        source_block_id="doc_b000001",
        question_type="definition_recall",
        difficulty="medium",
        question=f"State the definition from section '{section_title}'.",
        expected_answer=_TEXT[:800],
        evidence=make_evidence(),
        rule_id="R01_definition_recall",
        status=status,  # type: ignore[arg-type]
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def make_review_record(review_id: str = "rev_q_doc_b000001_R01_0") -> ReviewRecord:
    return ReviewRecord(
        review_id=review_id,
        question_id="q_doc_b000001_R01",
        action="accept",
        before_question="State the definition from section 'Compactness'.",
        after_question=None,
        before_expected_answer=_TEXT[:100],
        after_expected_answer=None,
        reviewed_at="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# save_blocks / load_blocks
# ---------------------------------------------------------------------------


class TestBlocksRoundtrip:
    def test_roundtrip_single_block(self, tmp_path):
        block = make_block()
        path = tmp_path / "blocks.json"
        save_blocks(path, [block])
        loaded = load_blocks(path)
        assert len(loaded) == 1
        assert dataclasses.asdict(loaded[0]) == dataclasses.asdict(block)

    def test_roundtrip_multiple_blocks(self, tmp_path):
        blocks = [make_block("doc_b000001"), make_block("doc_b000002")]
        path = tmp_path / "blocks.json"
        save_blocks(path, blocks)
        loaded = load_blocks(path)
        assert len(loaded) == 2
        original_ids = {b.block_id for b in blocks}
        loaded_ids = {b.block_id for b in loaded}
        assert original_ids == loaded_ids

    def test_roundtrip_empty_list(self, tmp_path):
        path = tmp_path / "blocks.json"
        save_blocks(path, [])
        assert load_blocks(path) == []

    def test_loaded_objects_are_source_blocks(self, tmp_path):
        path = tmp_path / "blocks.json"
        save_blocks(path, [make_block()])
        loaded = load_blocks(path)
        assert all(isinstance(b, SourceBlock) for b in loaded)

    def test_all_fields_preserved(self, tmp_path):
        block = make_block()
        path = tmp_path / "blocks.json"
        save_blocks(path, [block])
        loaded = load_blocks(path)[0]
        assert loaded.block_id == block.block_id
        assert loaded.block_type == block.block_type
        assert loaded.section_title == block.section_title
        assert loaded.text == block.text
        assert loaded.text_hash == block.text_hash
        assert loaded.start_line == block.start_line
        assert loaded.end_line == block.end_line

    def test_load_raises_if_not_list(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        with pytest.raises(ValueError, match="blocks"):
            load_blocks(path)


# ---------------------------------------------------------------------------
# save_questions / load_questions
# ---------------------------------------------------------------------------


class TestQuestionsRoundtrip:
    def test_roundtrip_single_question(self, tmp_path):
        q = make_question()
        path = tmp_path / "questions.json"
        save_questions(path, [q])
        loaded = load_questions(path)
        assert len(loaded) == 1
        assert loaded[0].question_id == q.question_id

    def test_roundtrip_multiple_questions(self, tmp_path):
        questions = [make_question("q_a"), make_question("q_b")]
        path = tmp_path / "questions.json"
        save_questions(path, questions)
        loaded = load_questions(path)
        assert len(loaded) == 2
        loaded_ids = {q.question_id for q in loaded}
        assert {"q_a", "q_b"} == loaded_ids

    def test_roundtrip_empty_list(self, tmp_path):
        path = tmp_path / "questions.json"
        save_questions(path, [])
        assert load_questions(path) == []

    def test_evidence_restored_as_evidence_object(self, tmp_path):
        q = make_question()
        path = tmp_path / "questions.json"
        save_questions(path, [q])
        loaded = load_questions(path)[0]
        assert isinstance(loaded.evidence, Evidence)

    def test_evidence_fields_preserved(self, tmp_path):
        q = make_question()
        path = tmp_path / "questions.json"
        save_questions(path, [q])
        loaded = load_questions(path)[0]
        assert loaded.evidence.source_text == q.evidence.source_text
        assert loaded.evidence.source_file == q.evidence.source_file
        assert loaded.evidence.start_line == q.evidence.start_line
        assert loaded.evidence.end_line == q.evidence.end_line
        assert loaded.evidence.text_hash == q.evidence.text_hash

    def test_all_question_fields_preserved(self, tmp_path):
        q = make_question(status="accepted")
        path = tmp_path / "questions.json"
        save_questions(path, [q])
        loaded = load_questions(path)[0]
        assert loaded.status == "accepted"
        assert loaded.question_type == q.question_type
        assert loaded.difficulty == q.difficulty
        assert loaded.question == q.question
        assert loaded.expected_answer == q.expected_answer
        assert loaded.rule_id == q.rule_id
        assert loaded.created_at == q.created_at
        assert loaded.updated_at == q.updated_at

    def test_load_raises_if_not_list(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps("oops"), encoding="utf-8")
        with pytest.raises(ValueError, match="questions"):
            load_questions(path)


# ---------------------------------------------------------------------------
# save_review_records / load_review_records
# ---------------------------------------------------------------------------


class TestReviewRecordsRoundtrip:
    def test_roundtrip_single_record(self, tmp_path):
        record = make_review_record()
        path = tmp_path / "reviews.json"
        save_review_records(path, [record])
        loaded = load_review_records(path)
        assert len(loaded) == 1
        assert dataclasses.asdict(loaded[0]) == dataclasses.asdict(record)

    def test_roundtrip_multiple_records(self, tmp_path):
        records = [make_review_record("rev_a"), make_review_record("rev_b")]
        path = tmp_path / "reviews.json"
        save_review_records(path, records)
        loaded = load_review_records(path)
        assert len(loaded) == 2
        assert {r.review_id for r in loaded} == {"rev_a", "rev_b"}

    def test_roundtrip_empty_list(self, tmp_path):
        path = tmp_path / "reviews.json"
        save_review_records(path, [])
        assert load_review_records(path) == []

    def test_loaded_objects_are_review_records(self, tmp_path):
        path = tmp_path / "reviews.json"
        save_review_records(path, [make_review_record()])
        loaded = load_review_records(path)
        assert all(isinstance(r, ReviewRecord) for r in loaded)

    def test_nullable_fields_preserved(self, tmp_path):
        record = make_review_record()
        path = tmp_path / "reviews.json"
        save_review_records(path, [record])
        loaded = load_review_records(path)[0]
        assert loaded.after_question is None
        assert loaded.after_expected_answer is None

    def test_load_raises_if_not_list(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(42), encoding="utf-8")
        with pytest.raises(ValueError, match="review_records"):
            load_review_records(path)


# ---------------------------------------------------------------------------
# export_accepted
# ---------------------------------------------------------------------------


class TestExportAccepted:
    def test_writes_only_accepted_questions(self, tmp_path):
        questions = [
            make_question("q_a", status="accepted"),
            make_question("q_b", status="rejected"),
            make_question("q_c", status="candidate"),
            make_question("q_d", status="accepted"),
        ]
        out = tmp_path / "accepted.json"
        export_accepted(questions, out)
        loaded = load_questions(out)
        assert {q.question_id for q in loaded} == {"q_a", "q_d"}

    def test_returns_accepted_list(self, tmp_path):
        questions = [
            make_question("q_a", status="accepted"),
            make_question("q_b", status="rejected"),
        ]
        out = tmp_path / "accepted.json"
        result = export_accepted(questions, out)
        assert len(result) == 1
        assert result[0].question_id == "q_a"

    def test_no_accepted_writes_empty_list(self, tmp_path):
        questions = [make_question("q_a", status="rejected")]
        out = tmp_path / "accepted.json"
        result = export_accepted(questions, out)
        assert result == []
        loaded = load_questions(out)
        assert loaded == []

    def test_all_accepted_writes_all(self, tmp_path):
        questions = [
            make_question("q_a", status="accepted"),
            make_question("q_b", status="accepted"),
        ]
        out = tmp_path / "accepted.json"
        result = export_accepted(questions, out)
        assert len(result) == 2
        loaded = load_questions(out)
        assert len(loaded) == 2


# ---------------------------------------------------------------------------
# UTF-8 / Korean text
# ---------------------------------------------------------------------------


class TestEncoding:
    def test_korean_section_title_survives_block_roundtrip(self, tmp_path):
        block = make_block(section_title=_KOREAN_TITLE)
        path = tmp_path / "blocks.json"
        save_blocks(path, [block])
        raw = path.read_text(encoding="utf-8")
        assert _KOREAN_TITLE in raw  # ensure_ascii=False: not escaped
        loaded = load_blocks(path)
        assert loaded[0].section_title == _KOREAN_TITLE

    def test_korean_text_survives_question_roundtrip(self, tmp_path):
        korean_text = "위상수학에서 열린 덮개는 중요한 개념입니다. " * 5
        q = make_question()
        # Inject Korean into expected_answer via a fresh Question
        q2 = Question(
            **{**dataclasses.asdict(q), "expected_answer": korean_text},
        )
        path = tmp_path / "questions.json"
        save_questions(path, [q2])
        raw = path.read_text(encoding="utf-8")
        assert "위상수학" in raw
        loaded = load_questions(path)
        assert loaded[0].expected_answer == korean_text


# ---------------------------------------------------------------------------
# Parent directory creation
# ---------------------------------------------------------------------------


class TestParentDirectoryCreation:
    def test_save_blocks_creates_nested_dirs(self, tmp_path):
        path = tmp_path / "a" / "b" / "c" / "blocks.json"
        save_blocks(path, [make_block()])
        assert path.exists()

    def test_save_questions_creates_nested_dirs(self, tmp_path):
        path = tmp_path / "bank" / "questions.json"
        save_questions(path, [make_question()])
        assert path.exists()

    def test_save_review_records_creates_nested_dirs(self, tmp_path):
        path = tmp_path / "review" / "records.json"
        save_review_records(path, [make_review_record()])
        assert path.exists()

    def test_export_accepted_creates_nested_dirs(self, tmp_path):
        path = tmp_path / "export" / "accepted" / "out.json"
        export_accepted([make_question("q_a", status="accepted")], path)
        assert path.exists()


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    def test_blocks_sorted_by_block_id(self, tmp_path):
        blocks = [
            make_block("doc_b000003"),
            make_block("doc_b000001"),
            make_block("doc_b000002"),
        ]
        path = tmp_path / "blocks.json"
        save_blocks(path, blocks)
        loaded = load_blocks(path)
        ids = [b.block_id for b in loaded]
        assert ids == sorted(ids)

    def test_questions_sorted_by_question_id(self, tmp_path):
        questions = [make_question("q_z"), make_question("q_a"), make_question("q_m")]
        path = tmp_path / "questions.json"
        save_questions(path, questions)
        loaded = load_questions(path)
        ids = [q.question_id for q in loaded]
        assert ids == sorted(ids)

    def test_review_records_sorted_by_review_id(self, tmp_path):
        records = [
            make_review_record("rev_z"),
            make_review_record("rev_a"),
            make_review_record("rev_m"),
        ]
        path = tmp_path / "reviews.json"
        save_review_records(path, records)
        loaded = load_review_records(path)
        ids = [r.review_id for r in loaded]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Input list mutation guard
# ---------------------------------------------------------------------------


class TestNoMutation:
    def test_save_blocks_does_not_mutate_input(self, tmp_path):
        blocks = [make_block("doc_b000003"), make_block("doc_b000001")]
        original_order = [b.block_id for b in blocks]
        save_blocks(tmp_path / "blocks.json", blocks)
        assert [b.block_id for b in blocks] == original_order

    def test_save_questions_does_not_mutate_input(self, tmp_path):
        questions = [make_question("q_z"), make_question("q_a")]
        original_order = [q.question_id for q in questions]
        save_questions(tmp_path / "questions.json", questions)
        assert [q.question_id for q in questions] == original_order

    def test_save_review_records_does_not_mutate_input(self, tmp_path):
        records = [make_review_record("rev_z"), make_review_record("rev_a")]
        original_order = [r.review_id for r in records]
        save_review_records(tmp_path / "reviews.json", records)
        assert [r.review_id for r in records] == original_order

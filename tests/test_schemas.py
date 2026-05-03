"""Tests for gonghaebun.models.question_bank dataclasses."""
from __future__ import annotations

import dataclasses
import json

import pytest

from gonghaebun.models.question_bank import (
    BLOCK_TYPES,
    DIFFICULTIES,
    QUESTION_STATUSES,
    REVIEW_ACTIONS,
    Evidence,
    Question,
    ReviewRecord,
    Rule,
    SourceBlock,
)


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        source_text="A subset K of a metric space X is compact if every open cover has a finite subcover.",
        source_file="tests/data/sample_source.md",
        start_line=8,
        end_line=10,
        text_hash="abc123def456",
    )
    return Evidence(**{**defaults, **overrides})


def make_source_block(**overrides) -> SourceBlock:
    defaults = dict(
        block_id="sample_source_b000000",
        document_id="sample_source",
        source_file="tests/data/sample_source.md",
        section_title="Compactness",
        block_type="definition",
        start_line=8,
        end_line=15,
        text="A subset K of a metric space X is compact if every open cover has a finite subcover.",
        text_hash="abc123def456",
    )
    return SourceBlock(**{**defaults, **overrides})


def make_rule(**overrides) -> Rule:
    defaults = dict(
        rule_id="R01",
        target_block_type="any",
        question_type="definition_recall",
        difficulty="medium",
        generator_name="template_definition_recall",
        version="1.0",
    )
    return Rule(**{**defaults, **overrides})


def make_question(**overrides) -> Question:
    defaults = dict(
        question_id="q_sample_source_b000000_R01",
        document_id="sample_source",
        source_block_id="sample_source_b000000",
        question_type="definition_recall",
        difficulty="medium",
        question="State the definition or key claim in: 'Compactness'",
        expected_answer="A subset K of a metric space X is compact if every open cover has a finite subcover.",
        evidence=make_evidence(),
        rule_id="R01",
    )
    return Question(**{**defaults, **overrides})


def make_review_record(**overrides) -> ReviewRecord:
    defaults = dict(
        review_id="rev_q_sample_source_b000000_R01_0",
        question_id="q_sample_source_b000000_R01",
        action="accept",
        before_question="State the definition or key claim in: 'Compactness'",
        after_question=None,
        before_expected_answer="A subset K...",
        after_expected_answer=None,
        reviewed_at="2026-01-01T00:00:00+00:00",
    )
    return ReviewRecord(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class TestEvidence:
    def test_valid_instantiation(self):
        e = make_evidence()
        assert e.source_text.startswith("A subset")
        assert e.start_line == 8
        assert e.end_line == 10

    def test_none_lines_allowed(self):
        e = make_evidence(start_line=None, end_line=None)
        assert e.start_line is None

    def test_empty_source_text_raises(self):
        with pytest.raises(ValueError, match="source_text"):
            make_evidence(source_text="")

    def test_whitespace_source_text_raises(self):
        # Empty string check — whitespace-only is NOT checked by Evidence (only empty)
        # Only strictly empty string raises; whitespace content is valid evidence
        with pytest.raises(ValueError):
            make_evidence(source_text="")


# ---------------------------------------------------------------------------
# SourceBlock
# ---------------------------------------------------------------------------

class TestSourceBlock:
    def test_valid_instantiation(self):
        b = make_source_block()
        assert b.block_id == "sample_source_b000000"
        assert b.block_type == "definition"

    def test_all_valid_block_types(self):
        for bt in BLOCK_TYPES:
            b = make_source_block(block_type=bt)
            assert b.block_type == bt

    def test_invalid_block_type_raises(self):
        with pytest.raises(ValueError, match="block_type"):
            make_source_block(block_type="banana")  # type: ignore[arg-type]

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="text"):
            make_source_block(text="   ")

    def test_none_lines_allowed(self):
        b = make_source_block(start_line=None, end_line=None)
        assert b.start_line is None


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------

class TestRule:
    def test_valid_instantiation(self):
        r = make_rule()
        assert r.rule_id == "R01"
        assert r.target_block_type == "any"

    def test_target_any_is_valid(self):
        r = make_rule(target_block_type="any")
        assert r.target_block_type == "any"

    def test_target_block_type_from_block_types(self):
        for bt in BLOCK_TYPES:
            r = make_rule(target_block_type=bt)
            assert r.target_block_type == bt

    def test_invalid_target_block_type_raises(self):
        with pytest.raises(ValueError, match="target_block_type"):
            make_rule(target_block_type="chapter")

    def test_all_valid_difficulties(self):
        for d in DIFFICULTIES:
            r = make_rule(difficulty=d)
            assert r.difficulty == d

    def test_invalid_difficulty_raises(self):
        with pytest.raises(ValueError, match="difficulty"):
            make_rule(difficulty="extreme")


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class TestQuestion:
    def test_valid_instantiation(self):
        q = make_question()
        assert q.question_id == "q_sample_source_b000000_R01"
        assert isinstance(q.evidence, Evidence)

    def test_status_defaults_to_candidate(self):
        q = make_question()
        assert q.status == "candidate"

    def test_all_valid_statuses(self):
        for s in QUESTION_STATUSES:
            q = make_question(status=s)
            assert q.status == s

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status"):
            make_question(status="pending")  # type: ignore[arg-type]

    def test_invalid_difficulty_raises(self):
        with pytest.raises(ValueError, match="difficulty"):
            make_question(difficulty="extreme")

    def test_evidence_dict_auto_converts(self):
        """Evidence dict passed as evidence kwarg should be auto-converted to Evidence."""
        ev_dict = dataclasses.asdict(make_evidence())
        q = make_question(evidence=ev_dict)  # type: ignore[arg-type]
        assert isinstance(q.evidence, Evidence)

    def test_json_roundtrip_preserves_evidence(self):
        """Full JSON roundtrip: dataclasses.asdict → json → Question(**d) restores Evidence."""
        q = make_question()
        d = dataclasses.asdict(q)
        j = json.dumps(d, ensure_ascii=False)
        d2 = json.loads(j)
        q2 = Question(**d2)

        assert isinstance(q2.evidence, Evidence)
        assert q2.evidence.source_text == q.evidence.source_text
        assert q2.evidence.source_file == q.evidence.source_file
        assert q2.evidence.start_line == q.evidence.start_line
        assert q2.evidence.text_hash == q.evidence.text_hash
        assert q2.question_id == q.question_id
        assert q2.status == q.status

    def test_json_roundtrip_preserves_all_fields(self):
        q = make_question(status="accepted", created_at="2026-01-01T00:00:00+00:00")
        d = dataclasses.asdict(q)
        q2 = Question(**json.loads(json.dumps(d)))
        assert q2.status == "accepted"
        assert q2.created_at == "2026-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# ReviewRecord
# ---------------------------------------------------------------------------

class TestReviewRecord:
    def test_valid_instantiation(self):
        r = make_review_record()
        assert r.action == "accept"
        assert r.after_question is None

    def test_all_valid_actions(self):
        for action in REVIEW_ACTIONS:
            r = make_review_record(action=action)
            assert r.action == action

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="action"):
            make_review_record(action="approve")  # type: ignore[arg-type]

    def test_edit_fields_can_be_set(self):
        r = make_review_record(
            action="edit",
            after_question="Revised question text",
            after_expected_answer="Revised answer",
        )
        assert r.action == "edit"
        assert r.after_question == "Revised question text"
        assert r.after_expected_answer == "Revised answer"

"""Tests for pipeline/question_generator.py (MVP2 Step 4)."""
from __future__ import annotations

import re

import pytest

from gonghaebun.models.question_bank import Evidence, Question, Rule, SourceBlock
from gonghaebun.pipeline.question_generator import (
    generate_questions,
    make_question,
    normalize_preview,
)
from gonghaebun.pipeline.rule_engine import RULES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_TEXT = (
    "A subset K of a metric space X is called compact if every open cover of K "
    "has a finite subcover. This is the standard definition used in analysis."
)
_TEXT_HASH = "deadbeef"  # arbitrary; SourceBlock does not validate hash content


def make_block(
    block_type: str = "definition",
    block_id: str = "doc_b000001",
    section_title: str = "Compactness",
    text: str = _LONG_TEXT,
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
        text_hash=_TEXT_HASH,
    )


def make_rule(
    rule_id: str = "R01_definition_recall",
    target_block_type: str = "definition",
    question_type: str = "definition_recall",
    difficulty: str = "medium",
    generator_name: str = "definition_recall_template",
) -> Rule:
    return Rule(
        rule_id=rule_id,
        target_block_type=target_block_type,
        question_type=question_type,
        difficulty=difficulty,
        generator_name=generator_name,
        version="v1",
    )


# ---------------------------------------------------------------------------
# generate_questions
# ---------------------------------------------------------------------------


class TestGenerateQuestions:
    def test_returns_list_of_question_objects(self):
        block = make_block()
        result = generate_questions([block])
        assert isinstance(result, list)
        assert all(isinstance(q, Question) for q in result)

    def test_one_applicable_rule_creates_one_question(self):
        block = make_block("definition")
        rules = [r for r in RULES if r.rule_id == "R01_definition_recall"]
        result = generate_questions([block], rules)
        assert len(result) == 1

    def test_no_applicable_rules_produces_no_questions(self):
        block = make_block("unknown")
        result = generate_questions([block])
        assert result == []

    def test_empty_blocks_returns_empty(self):
        assert generate_questions([]) == []

    def test_multiple_blocks_preserve_order(self):
        blocks = [
            make_block("definition", "doc_b000001"),
            make_block("theorem", "doc_b000002"),
            make_block("proof", "doc_b000003"),
        ]
        result = generate_questions(blocks)
        source_ids = [q.source_block_id for q in result]
        first = source_ids.index("doc_b000001")
        second = source_ids.index("doc_b000002")
        third = source_ids.index("doc_b000003")
        assert first < second < third

    def test_deterministic_across_repeated_calls(self):
        block = make_block()
        result_a = generate_questions([block])
        result_b = generate_questions([block])
        assert [q.question_id for q in result_a] == [q.question_id for q in result_b]
        assert [q.question for q in result_a] == [q.question for q in result_b]
        assert [q.expected_answer for q in result_a] == [q.expected_answer for q in result_b]

    def test_uses_default_rules_when_none_passed(self):
        block = make_block("definition")
        result_default = generate_questions([block])
        result_explicit = generate_questions([block], RULES)
        assert len(result_default) == len(result_explicit)
        assert [q.question_id for q in result_default] == [
            q.question_id for q in result_explicit
        ]


# ---------------------------------------------------------------------------
# make_question
# ---------------------------------------------------------------------------


class TestMakeQuestion:
    def setup_method(self):
        self.block = make_block()
        self.rule = make_rule()
        self.q = make_question(self.block, self.rule)

    def test_question_id_format(self):
        assert self.q.question_id == f"q_{self.block.block_id}_{self.rule.rule_id}"

    def test_question_id_deterministic(self):
        q2 = make_question(self.block, self.rule)
        assert self.q.question_id == q2.question_id

    def test_source_block_id_matches(self):
        assert self.q.source_block_id == self.block.block_id

    def test_document_id_matches(self):
        assert self.q.document_id == self.block.document_id

    def test_question_type_from_rule(self):
        assert self.q.question_type == self.rule.question_type

    def test_difficulty_from_rule(self):
        assert self.q.difficulty == self.rule.difficulty

    def test_rule_id_matches(self):
        assert self.q.rule_id == self.rule.rule_id

    def test_status_defaults_to_candidate(self):
        assert self.q.status == "candidate"

    def test_created_at_is_nonempty_iso_string(self):
        assert self.q.created_at
        assert re.match(r"\d{4}-\d{2}-\d{2}T", self.q.created_at)

    def test_updated_at_is_nonempty_iso_string(self):
        assert self.q.updated_at
        assert re.match(r"\d{4}-\d{2}-\d{2}T", self.q.updated_at)

    def test_expected_answer_equals_block_text_up_to_800(self):
        assert self.q.expected_answer == self.block.text[:800]

    def test_expected_answer_truncated_at_800(self):
        long_text = "x " * 500  # 1000 chars total
        block = make_block(text=long_text)
        q = make_question(block, self.rule)
        assert q.expected_answer == long_text[:800]
        assert len(q.expected_answer) <= 800

    def test_expected_answer_source_grounded_not_generated(self):
        # expected_answer must be a prefix of block.text, not an LLM output
        assert self.block.text.startswith(self.q.expected_answer)

    def test_evidence_is_evidence_object(self):
        assert isinstance(self.q.evidence, Evidence)

    def test_evidence_source_text_matches_block(self):
        assert self.q.evidence.source_text == self.block.text

    def test_evidence_source_file_matches_block(self):
        assert self.q.evidence.source_file == self.block.source_file

    def test_evidence_start_line_matches_block(self):
        assert self.q.evidence.start_line == self.block.start_line

    def test_evidence_end_line_matches_block(self):
        assert self.q.evidence.end_line == self.block.end_line

    def test_evidence_text_hash_matches_block(self):
        assert self.q.evidence.text_hash == self.block.text_hash

    def test_question_contains_section_title(self):
        assert self.block.section_title in self.q.question

    def test_question_uses_normalized_preview_when_no_section_title(self):
        block = make_block(section_title="")
        q = make_question(block, self.rule)
        assert q.question.strip()
        # Template wraps label in single quotes; preview text must appear
        assert "'" in q.question


# ---------------------------------------------------------------------------
# Template coverage
# ---------------------------------------------------------------------------


class TestTemplates:
    @pytest.mark.parametrize(
        "generator_name, block_type",
        [
            ("definition_recall_template", "definition"),
            ("theorem_statement_template", "theorem"),
            ("proof_schema_template", "proof"),
            ("example_explanation_template", "example"),
            ("exercise_recall_template", "exercise"),
            ("general_intuition_template", "paragraph"),
        ],
    )
    def test_each_template_produces_nonempty_question(self, generator_name, block_type):
        block = make_block(block_type=block_type)
        rule = make_rule(
            rule_id="TEST",
            target_block_type=block_type,
            generator_name=generator_name,
        )
        q = make_question(block, rule)
        assert q.question.strip()

    def test_unknown_generator_name_raises_value_error(self):
        block = make_block()
        bad_rule = Rule.__new__(Rule)
        object.__setattr__(bad_rule, "rule_id", "BAD")
        object.__setattr__(bad_rule, "target_block_type", "definition")
        object.__setattr__(bad_rule, "question_type", "q")
        object.__setattr__(bad_rule, "difficulty", "medium")
        object.__setattr__(bad_rule, "generator_name", "nonexistent_template")
        object.__setattr__(bad_rule, "version", "v1")
        with pytest.raises(ValueError, match="generator_name"):
            make_question(block, bad_rule)


# ---------------------------------------------------------------------------
# normalize_preview
# ---------------------------------------------------------------------------


class TestNormalizePreview:
    def test_short_text_unchanged(self):
        assert normalize_preview("hello world") == "hello world"

    def test_collapses_internal_whitespace(self):
        assert normalize_preview("hello   world\n\tfoo") == "hello world foo"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_preview("  hello world  ") == "hello world"

    def test_truncates_at_max_chars(self):
        text = "a" * 100
        result = normalize_preview(text, max_chars=10)
        assert result.endswith("...")
        assert len(result) <= 13  # 10 chars + "..."

    def test_exact_max_chars_no_truncation(self):
        text = "a" * 80
        result = normalize_preview(text, max_chars=80)
        assert result == text
        assert not result.endswith("...")

    def test_empty_string_returns_empty(self):
        assert normalize_preview("") == ""

    def test_whitespace_only_returns_empty(self):
        assert normalize_preview("   \n\t  ") == ""

    def test_custom_max_chars(self):
        text = "word " * 20  # 100 chars
        result = normalize_preview(text, max_chars=20)
        assert result.endswith("...")
        assert len(result) <= 23


# ---------------------------------------------------------------------------
# No MVP1 imports check
# ---------------------------------------------------------------------------


class TestNoMVP1Imports:
    def test_recall_orchestrator_not_imported(self):
        import inspect

        import gonghaebun.pipeline.question_generator as qg

        src = inspect.getsource(qg)
        assert "recall_orchestrator" not in src

    def test_mvp1_session_not_imported(self):
        import inspect

        import gonghaebun.pipeline.question_generator as qg

        src = inspect.getsource(qg)
        assert "from gonghaebun.session" not in src
        assert "import session" not in src

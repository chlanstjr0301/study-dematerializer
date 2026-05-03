"""Tests for pipeline/rule_engine.py (MVP2 Step 3)."""
from __future__ import annotations

import pytest

from gonghaebun.models.question_bank import Rule, SourceBlock
from gonghaebun.pipeline.rule_engine import (
    RULES,
    get_applicable_rules,
    get_rules_for_blocks,
    validate_rules,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_TEXT = "a " * 60  # 60 non-ws chars, passes the 50-char filter


def make_block(block_type: str, block_id: str = "doc_b000001") -> SourceBlock:
    return SourceBlock(
        block_id=block_id,
        document_id="doc",
        source_file="doc.md",
        section_title="Section",
        block_type=block_type,  # type: ignore[arg-type]
        start_line=1,
        end_line=1,
        text=_LONG_TEXT,
        text_hash="abc123",
    )


# ---------------------------------------------------------------------------
# RULES constant
# ---------------------------------------------------------------------------


class TestRulesConstant:
    def test_rules_is_nonempty(self):
        assert len(RULES) > 0

    def test_all_rules_are_rule_objects(self):
        assert all(isinstance(r, Rule) for r in RULES)

    def test_all_default_rule_ids_present(self):
        ids = {r.rule_id for r in RULES}
        expected = {
            "R01_definition_recall",
            "R02_theorem_statement",
            "R03_proof_schema",
            "R04_example_explanation",
            "R05_exercise_recall",
            "R06_general_intuition",
        }
        assert expected.issubset(ids)

    def test_rule_attributes(self):
        r01 = next(r for r in RULES if r.rule_id == "R01_definition_recall")
        assert r01.target_block_type == "definition"
        assert r01.question_type == "definition_recall"
        assert r01.difficulty == "medium"
        assert r01.generator_name == "definition_recall_template"
        assert r01.version == "v1"

    def test_r03_is_hard(self):
        r03 = next(r for r in RULES if r.rule_id == "R03_proof_schema")
        assert r03.difficulty == "hard"

    def test_r04_is_easy(self):
        r04 = next(r for r in RULES if r.rule_id == "R04_example_explanation")
        assert r04.difficulty == "easy"


# ---------------------------------------------------------------------------
# validate_rules
# ---------------------------------------------------------------------------


class TestValidateRules:
    def test_default_rules_are_valid(self):
        validate_rules(RULES)  # must not raise

    def test_empty_list_is_valid(self):
        validate_rules([])  # must not raise

    def test_duplicate_rule_id_raises(self):
        rules = list(RULES) + [RULES[0]]
        with pytest.raises(ValueError, match="Duplicate rule_id"):
            validate_rules(rules)

    def test_invalid_target_block_type_raises(self):
        # Bypass Rule.__post_init__ so we can pass an invalid rule to validate_rules
        bad = Rule.__new__(Rule)
        object.__setattr__(bad, "rule_id", "BAD")
        object.__setattr__(bad, "target_block_type", "chapter")
        object.__setattr__(bad, "question_type", "q")
        object.__setattr__(bad, "difficulty", "easy")
        object.__setattr__(bad, "generator_name", "gen")
        object.__setattr__(bad, "version", "v1")
        with pytest.raises(ValueError, match="target_block_type"):
            validate_rules([bad])

    def test_empty_generator_name_raises(self):
        bad = Rule.__new__(Rule)
        object.__setattr__(bad, "rule_id", "X01")
        object.__setattr__(bad, "target_block_type", "definition")
        object.__setattr__(bad, "question_type", "q")
        object.__setattr__(bad, "difficulty", "easy")
        object.__setattr__(bad, "generator_name", "  ")
        object.__setattr__(bad, "version", "v1")
        with pytest.raises(ValueError, match="generator_name"):
            validate_rules([bad])

    def test_empty_question_type_raises(self):
        bad = Rule.__new__(Rule)
        object.__setattr__(bad, "rule_id", "X02")
        object.__setattr__(bad, "target_block_type", "definition")
        object.__setattr__(bad, "question_type", "")
        object.__setattr__(bad, "difficulty", "easy")
        object.__setattr__(bad, "generator_name", "gen")
        object.__setattr__(bad, "version", "v1")
        with pytest.raises(ValueError, match="question_type"):
            validate_rules([bad])


# ---------------------------------------------------------------------------
# get_applicable_rules
# ---------------------------------------------------------------------------


class TestGetApplicableRules:
    @pytest.mark.parametrize(
        "block_type, expected_rule_id",
        [
            ("definition", "R01_definition_recall"),
            ("theorem", "R02_theorem_statement"),
            ("proof", "R03_proof_schema"),
            ("example", "R04_example_explanation"),
            ("exercise", "R05_exercise_recall"),
            ("paragraph", "R06_general_intuition"),
        ],
    )
    def test_each_block_type_returns_correct_rule(self, block_type, expected_rule_id):
        block = make_block(block_type)
        rules = get_applicable_rules(block)
        ids = [r.rule_id for r in rules]
        assert expected_rule_id in ids

    def test_unknown_block_type_returns_no_rule(self):
        block = make_block("unknown")
        rules = get_applicable_rules(block)
        assert rules == []

    def test_uses_default_rules_when_none_passed(self):
        block = make_block("definition")
        result = get_applicable_rules(block)
        expected = get_applicable_rules(block, RULES)
        assert result == expected

    def test_custom_rules_override_default(self):
        custom = [
            Rule(
                rule_id="C01",
                target_block_type="definition",
                question_type="custom_q",
                difficulty="easy",
                generator_name="custom_gen",
                version="v1",
            )
        ]
        block = make_block("definition")
        result = get_applicable_rules(block, custom)
        assert len(result) == 1
        assert result[0].rule_id == "C01"

    def test_ordering_is_deterministic(self):
        block = make_block("definition")
        result_a = get_applicable_rules(block)
        result_b = get_applicable_rules(block)
        assert [r.rule_id for r in result_a] == [r.rule_id for r in result_b]

    def test_no_rules_match_non_matching_type(self):
        # A list with only a theorem rule should return nothing for definition
        theorem_only = [r for r in RULES if r.rule_id == "R02_theorem_statement"]
        block = make_block("definition")
        assert get_applicable_rules(block, theorem_only) == []


# ---------------------------------------------------------------------------
# get_rules_for_blocks
# ---------------------------------------------------------------------------


class TestGetRulesForBlocks:
    def test_returns_dict_keyed_by_block_id(self):
        blocks = [make_block("definition", "doc_b000001"), make_block("theorem", "doc_b000002")]
        result = get_rules_for_blocks(blocks)
        assert set(result.keys()) == {"doc_b000001", "doc_b000002"}

    def test_each_block_maps_to_correct_rules(self):
        blocks = [make_block("definition", "doc_b000001"), make_block("theorem", "doc_b000002")]
        result = get_rules_for_blocks(blocks)
        def_ids = [r.rule_id for r in result["doc_b000001"]]
        thm_ids = [r.rule_id for r in result["doc_b000002"]]
        assert "R01_definition_recall" in def_ids
        assert "R02_theorem_statement" in thm_ids

    def test_empty_blocks_returns_empty_dict(self):
        assert get_rules_for_blocks([]) == {}

    def test_unknown_block_maps_to_empty_list(self):
        block = make_block("unknown", "doc_b000001")
        result = get_rules_for_blocks([block])
        assert result["doc_b000001"] == []

    def test_block_order_preserved(self):
        blocks = [
            make_block("definition", "doc_b000001"),
            make_block("theorem", "doc_b000002"),
            make_block("proof", "doc_b000003"),
        ]
        result = get_rules_for_blocks(blocks)
        assert list(result.keys()) == ["doc_b000001", "doc_b000002", "doc_b000003"]

    def test_uses_default_rules_when_none_passed(self):
        blocks = [make_block("definition", "doc_b000001")]
        result_default = get_rules_for_blocks(blocks)
        result_explicit = get_rules_for_blocks(blocks, RULES)
        assert [r.rule_id for r in result_default["doc_b000001"]] == [
            r.rule_id for r in result_explicit["doc_b000001"]
        ]

    def test_custom_rules_applied_per_block(self):
        custom = [
            Rule(
                rule_id="C01",
                target_block_type="proof",
                question_type="custom_proof",
                difficulty="hard",
                generator_name="custom_gen",
                version="v1",
            )
        ]
        blocks = [make_block("proof", "doc_b000001"), make_block("definition", "doc_b000002")]
        result = get_rules_for_blocks(blocks, custom)
        assert len(result["doc_b000001"]) == 1
        assert result["doc_b000001"][0].rule_id == "C01"
        assert result["doc_b000002"] == []

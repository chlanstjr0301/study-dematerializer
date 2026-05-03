"""
Stage B (MVP2): Rule Engine.

Defines the hardcoded RULES list and helpers for mapping SourceBlocks to
applicable Rules. Fully deterministic — no LLM calls.
"""
from __future__ import annotations

from gonghaebun.models.question_bank import (
    BLOCK_TYPES,
    DIFFICULTIES,
    Rule,
    SourceBlock,
)

# ---------------------------------------------------------------------------
# Default rules
# ---------------------------------------------------------------------------

RULES: list[Rule] = [
    Rule(
        rule_id="R01_definition_recall",
        target_block_type="definition",
        question_type="definition_recall",
        difficulty="medium",
        generator_name="definition_recall_template",
        version="v1",
    ),
    Rule(
        rule_id="R02_theorem_statement",
        target_block_type="theorem",
        question_type="theorem_statement_recall",
        difficulty="medium",
        generator_name="theorem_statement_template",
        version="v1",
    ),
    Rule(
        rule_id="R03_proof_schema",
        target_block_type="proof",
        question_type="proof_schema_recall",
        difficulty="hard",
        generator_name="proof_schema_template",
        version="v1",
    ),
    Rule(
        rule_id="R04_example_explanation",
        target_block_type="example",
        question_type="example_explanation",
        difficulty="easy",
        generator_name="example_explanation_template",
        version="v1",
    ),
    Rule(
        rule_id="R05_exercise_recall",
        target_block_type="exercise",
        question_type="exercise_recall",
        difficulty="medium",
        generator_name="exercise_recall_template",
        version="v1",
    ),
    Rule(
        rule_id="R06_general_intuition",
        target_block_type="paragraph",
        question_type="intuition_recall",
        difficulty="easy",
        generator_name="general_intuition_template",
        version="v1",
    ),
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_applicable_rules(
    block: SourceBlock,
    rules: list[Rule] | None = None,
) -> list[Rule]:
    """
    Return rules whose target_block_type matches block.block_type.

    Preserves the order of rules in the list. If rules is None, uses RULES.
    """
    if rules is None:
        rules = RULES
    return [r for r in rules if r.target_block_type == block.block_type]


def get_rules_for_blocks(
    blocks: list[SourceBlock],
    rules: list[Rule] | None = None,
) -> dict[str, list[Rule]]:
    """
    Return a mapping from block_id to the list of applicable rules.

    Preserves block order and rule order.
    """
    if rules is None:
        rules = RULES
    return {block.block_id: get_applicable_rules(block, rules) for block in blocks}


def validate_rules(rules: list[Rule]) -> None:
    """
    Raise ValueError if any rule in the list is malformed or the list has
    duplicate rule_ids.

    Checks:
    - duplicate rule_id
    - target_block_type not in BLOCK_TYPES | {"any"}
    - difficulty not in DIFFICULTIES
    - generator_name is empty
    - question_type is empty
    """
    seen_ids: set[str] = set()
    valid_targets = BLOCK_TYPES | {"any"}

    for rule in rules:
        if rule.rule_id in seen_ids:
            raise ValueError(f"Duplicate rule_id: {rule.rule_id!r}")
        seen_ids.add(rule.rule_id)

        if rule.target_block_type not in valid_targets:
            raise ValueError(
                f"Rule {rule.rule_id!r}: invalid target_block_type "
                f"{rule.target_block_type!r}. Valid: {sorted(valid_targets)}"
            )
        if rule.difficulty not in DIFFICULTIES:
            raise ValueError(
                f"Rule {rule.rule_id!r}: invalid difficulty "
                f"{rule.difficulty!r}. Valid: {sorted(DIFFICULTIES)}"
            )
        if not rule.generator_name.strip():
            raise ValueError(f"Rule {rule.rule_id!r}: generator_name must not be empty")
        if not rule.question_type.strip():
            raise ValueError(f"Rule {rule.rule_id!r}: question_type must not be empty")

"""
Stage C (MVP2): Deterministic Question Generator.

Generates Question objects from SourceBlock × Rule pairs using hardcoded
string templates. Fully deterministic — no LLM calls.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from gonghaebun.models.question_bank import Evidence, Question, Rule, SourceBlock
from gonghaebun.pipeline.rule_engine import RULES, get_applicable_rules

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXPECTED_ANSWER_MAX: int = 800

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "definition_recall_template": (
        "State the definition or key concept from section '{label}'."
    ),
    "theorem_statement_template": (
        "State the theorem, proposition, lemma, or corollary from section '{label}'."
    ),
    "proof_schema_template": (
        "Outline the proof structure used in section '{label}'."
    ),
    "example_explanation_template": (
        "Explain what the example in section '{label}' is illustrating."
    ),
    "exercise_recall_template": (
        "Restate the exercise or problem from section '{label}' and identify what it asks you to show."
    ),
    "general_intuition_template": (
        "Explain the main idea of the following passage from section '{label}'."
    ),
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_questions(
    blocks: list[SourceBlock],
    rules: list[Rule] | None = None,
) -> list[Question]:
    """
    Generate Question objects from a list of SourceBlocks.

    For each block, get_applicable_rules() is called and one Question is
    produced per applicable Rule. Preserves block order and rule order.
    If rules is None, the default RULES from rule_engine are used.
    """
    if rules is None:
        rules = RULES
    questions: list[Question] = []
    for block in blocks:
        for rule in get_applicable_rules(block, rules):
            questions.append(make_question(block, rule))
    return questions


def make_question(block: SourceBlock, rule: Rule) -> Question:
    """Generate a single Question from a SourceBlock and a Rule."""
    now = datetime.now(timezone.utc).isoformat()
    label = block.section_title if block.section_title else normalize_preview(block.text)
    question_text = _expand_template(rule.generator_name, label)
    return Question(
        question_id=f"q_{block.block_id}_{rule.rule_id}",
        document_id=block.document_id,
        source_block_id=block.block_id,
        question_type=rule.question_type,
        difficulty=rule.difficulty,
        question=question_text,
        expected_answer=block.text[:_EXPECTED_ANSWER_MAX],
        evidence=Evidence(
            source_text=block.text,
            source_file=block.source_file,
            start_line=block.start_line,
            end_line=block.end_line,
            text_hash=block.text_hash,
        ),
        rule_id=rule.rule_id,
        status="candidate",
        created_at=now,
        updated_at=now,
    )


def normalize_preview(text: str, max_chars: int = 80) -> str:
    """
    Collapse internal whitespace and truncate to max_chars.

    Appends "..." if the collapsed text exceeds max_chars.
    Used as a fallback label when block.section_title is empty.
    """
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars].rstrip() + "..."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _expand_template(generator_name: str, label: str) -> str:
    """
    Expand a named template with the given label.

    Raises ValueError for unknown generator names — these indicate a rule
    configuration error, not a runtime failure.
    """
    template = _TEMPLATES.get(generator_name)
    if template is None:
        raise ValueError(
            f"Unknown generator_name: {generator_name!r}. "
            f"Valid names: {sorted(_TEMPLATES)}"
        )
    return template.format(label=label)

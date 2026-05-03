"""
MVP2 Build-Bank orchestrator.

Runs the full question-bank pipeline in sequence:
  Step A  block_parser.py   → list[SourceBlock]
  Step B  rule_engine.py    → validate RULES
  Step C  question_generator.py → list[Question]
  Step D  io.py             → blocks.generated.json, questions.generated.json

Fully deterministic. No LLM calls.
"""
from __future__ import annotations

from pathlib import Path

from gonghaebun.models.question_bank import Question, SourceBlock
from gonghaebun.pipeline.block_parser import parse_blocks
from gonghaebun.pipeline.io import save_blocks, save_questions
from gonghaebun.pipeline.question_generator import generate_questions
from gonghaebun.pipeline.rule_engine import RULES, validate_rules


def run_bank_session(
    source_path: Path,
    document_id: str,
    output_dir: Path,
) -> tuple[list[SourceBlock], list[Question]]:
    """
    Run the full MVP2 question-bank pipeline.

    Steps:
      1. Validate the default RULES list.
      2. Parse source_path into SourceBlock objects.
      3. Generate Question objects from blocks × RULES.
      4. Save blocks.generated.json and questions.generated.json to output_dir.
      5. Return (blocks, questions).

    output_dir is created automatically if it does not exist.
    If no blocks are parsed (empty or all-short source), both JSON files are
    written as empty arrays. The caller may choose to warn the user.
    """
    # Step B first — fail fast on misconfigured rules before touching disk
    validate_rules(RULES)

    # Step A: parse blocks
    blocks = parse_blocks(Path(source_path), document_id)

    # Step C: generate questions
    questions = generate_questions(blocks, RULES)

    # Step D: persist outputs
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_blocks(output_dir / "blocks.generated.json", blocks)
    save_questions(output_dir / "questions.generated.json", questions)

    return blocks, questions

"""
Service: bank build, question retrieval, review, and export.
"""
from __future__ import annotations

import dataclasses

import apps.api.config as config
from apps.api.services.bank_service import safe_resolve_under


def build_bank(concept_id: str, source_relative_path: str, document_id: str) -> dict:
    from gonghaebun.bank_session import run_bank_session
    from apps.api.services.path_utils import validate_slug

    # Validate slugs before any path operations
    concept_id  = validate_slug(concept_id,  field_name="concept_id")
    document_id = validate_slug(document_id, field_name="document_id")

    # source_relative_path must be under sources/ — reject anything else
    if not source_relative_path.startswith("sources/"):
        raise ValueError(
            f"source_relative_path must start with 'sources/'. Got: {source_relative_path!r}"
        )
    source_path = safe_resolve_under(config.DATA_ROOT, source_relative_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_relative_path!r}")

    output_dir = config.BANK_ROOT / concept_id
    blocks, questions = run_bank_session(source_path, document_id, output_dir)
    return {
        "concept_id":     concept_id,
        "document_id":    document_id,
        "block_count":    len(blocks),
        "question_count": len(questions),
        "bank_dir":       f"banks/{concept_id}",
    }


def get_generated_questions(concept_id: str) -> list[dict]:
    from gonghaebun.pipeline.io import load_questions
    from apps.api.services.path_utils import validate_slug

    concept_id = validate_slug(concept_id, field_name="concept_id")
    path = config.BANK_ROOT / concept_id / "questions.generated.json"
    if not path.exists():
        raise FileNotFoundError(f"No generated bank for {concept_id!r}")
    return [dataclasses.asdict(q) for q in load_questions(path)]


def get_accepted_questions(concept_id: str) -> list[dict]:
    from gonghaebun.pipeline.io import load_questions
    from apps.api.services.path_utils import validate_slug

    concept_id = validate_slug(concept_id, field_name="concept_id")
    path = config.BANK_ROOT / concept_id / "questions.accepted.json"
    if not path.exists():
        raise FileNotFoundError(f"No accepted bank for {concept_id!r}")
    return [dataclasses.asdict(q) for q in load_questions(path)]


def review_bank(concept_id: str, actions: list[dict]) -> dict:
    from gonghaebun.pipeline.io import load_questions, save_questions, save_review_records
    from gonghaebun.review.review_cli import review_questions
    from apps.api.services.path_utils import validate_slug

    concept_id = validate_slug(concept_id, field_name="concept_id")
    bank_dir = config.BANK_ROOT / concept_id
    reviewed_path  = bank_dir / "questions.reviewed.json"
    generated_path = bank_dir / "questions.generated.json"
    source_path = reviewed_path if reviewed_path.exists() else generated_path
    if not source_path.exists():
        raise FileNotFoundError(f"No questions for {concept_id!r}. Build bank first.")

    questions = load_questions(source_path)
    # Map API field names → review_questions() expected keys.
    # review_questions() expects: question_id, action, edited_question, edited_expected_answer
    mapped = [
        {
            "question_id":            a["question_id"],
            "action":                 a["action"],
            "edited_question":        a.get("updated_question"),
            "edited_expected_answer": a.get("updated_expected_answer"),
        }
        for a in actions
    ]
    questions, records = review_questions(questions, mapped)
    save_questions(bank_dir / "questions.reviewed.json", questions)
    save_review_records(bank_dir / "review_records.json", records)

    counts: dict[str, int] = {"total": len(records), "accepted": 0, "rejected": 0, "edited": 0, "skipped": 0}
    for r in records:
        if r.action == "accept":
            counts["accepted"] += 1
        elif r.action == "reject":
            counts["rejected"] += 1
        elif r.action == "edit":
            counts["edited"] += 1
        elif r.action == "skip":
            counts["skipped"] += 1
    return counts


def export_accepted_questions(concept_id: str) -> dict:
    from gonghaebun.pipeline.io import export_accepted, load_questions
    from apps.api.services.path_utils import validate_slug

    concept_id = validate_slug(concept_id, field_name="concept_id")
    reviewed_path = config.BANK_ROOT / concept_id / "questions.reviewed.json"
    if not reviewed_path.exists():
        raise FileNotFoundError(
            f"No reviewed questions for {concept_id!r}. Run review first."
        )
    questions = load_questions(reviewed_path)
    accepted = export_accepted(
        questions, config.BANK_ROOT / concept_id / "questions.accepted.json"
    )
    return {"accepted_count": len(accepted)}

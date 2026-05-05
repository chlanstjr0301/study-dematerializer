"""
Service: STUDY.md — due concepts and raw content.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from gonghaebun.study_loop.review_due import get_due_concepts
from gonghaebun.study_md.parser import parse_study_md

import apps.api.config as config


def _build_due_item(concept_id: str, record, today: date) -> dict:
    """Build the enriched due-review dict for a single concept."""
    next_review = record.next_review if record else None

    if next_review is None:
        overdue = True
    else:
        try:
            overdue = date.fromisoformat(next_review) < today
        except ValueError:
            overdue = True

    overall_mastery = record.overall_mastery if record else "unknown"

    # Non-solid reps sorted: unknown first, then partial; alphabetical within each level
    weak_reps = sorted(
        [r for r in (record.representations if record else []) if r.mastery != "solid"],
        key=lambda r: (0 if r.mastery == "unknown" else 1, r.type),
    )
    target_reps = [r.type for r in weak_reps]
    weak_count = len(target_reps)

    if weak_count == 0:
        suggested_mode = "full_recall"
        reason = "All representations solid — periodic review"
    else:
        suggested_mode = "weak_only"
        unknown_n = sum(1 for r in weak_reps if r.mastery == "unknown")
        partial_n = weak_count - unknown_n
        parts = []
        if unknown_n:
            parts.append(f"{unknown_n} unknown")
        if partial_n:
            parts.append(f"{partial_n} partial")
        reason = f"{', '.join(parts)} representation(s) need practice"

    return {
        "concept_id": concept_id,
        "next_review": next_review,
        "overdue": overdue,
        "overall_mastery": overall_mastery,
        "weak_rep_count": weak_count,
        "target_representations": target_reps,
        "suggested_mode": suggested_mode,
        "reason": reason,
    }


def get_due(study_md_path: Path | None = None) -> list[dict]:
    """
    Return concepts due for review with scheduler enrichment.

    Each item: {concept_id, next_review, overdue, overall_mastery, weak_rep_count,
    target_representations, suggested_mode, reason}.
    Returns [] if STUDY.md does not exist.
    """
    path = study_md_path or config.STUDY_MD
    if not path.exists():
        return []

    today = date.today()
    due_ids = get_due_concepts(path, today)
    records = parse_study_md(path)

    return [
        _build_due_item(concept_id, records.get(concept_id), today)
        for concept_id in due_ids
    ]


def read_study_md(study_md_path: Path | None = None) -> str:
    """Return STUDY.md content as a string. Returns '' if file does not exist."""
    path = study_md_path or config.STUDY_MD
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _due_status(next_review: str | None, today: date) -> str:
    if next_review is None:
        return "not_scheduled"
    try:
        d = date.fromisoformat(next_review)
    except ValueError:
        return "not_scheduled"
    if d < today:
        return "overdue"
    if d == today:
        return "due_today"
    return "upcoming"


def _weak_sort_key(item: dict) -> tuple:
    mastery_rank = 0 if item["mastery"] == "unknown" else 1
    due_rank_map = {"overdue": 0, "due_today": 1, "upcoming": 2, "not_scheduled": 3}
    due_rank = due_rank_map.get(item["due_status"], 3)
    return (mastery_rank, due_rank, item["concept_id"])


def get_validation_report(study_md_path: Path | None = None) -> dict:
    """
    Run canonical-state validation on STUDY.md and return a structured report dict.

    Returns valid=True with empty lists if STUDY.md is absent.
    """
    from gonghaebun.study_md.validate import validate_study_md_full

    path = study_md_path or config.STUDY_MD
    report = validate_study_md_full(path)

    def _v(v) -> dict:
        return {
            "code": v.code,
            "concept_id": v.concept_id,
            "field": v.field,
            "message": v.message,
        }

    return {
        "valid": report.valid,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "errors": [_v(v) for v in report.errors],
        "warnings": [_v(v) for v in report.warnings],
    }


def get_weak_representations(
    study_md_path: Path | None = None,
    today: date | None = None,
) -> list[dict]:
    """
    Return all weak (concept_id, rep_type) pairs from STUDY.md, sorted by urgency.

    Weak = mastery != 'solid'.
    Sort: unknown before partial; overdue before upcoming within same mastery level.
    Returns [] if STUDY.md is absent or all reps are solid.
    """
    path = study_md_path or config.STUDY_MD
    if not path.exists():
        return []

    _today = today or date.today()
    records = parse_study_md(path)
    items = []
    for concept_id, record in records.items():
        for rep in record.representations:
            if rep.mastery == "solid":
                continue
            items.append({
                "concept_id": concept_id,
                "rep_type": rep.type,
                "mastery": rep.mastery,
                "last_reviewed": rep.last_reviewed,
                "next_review": record.next_review,
                "due_status": _due_status(record.next_review, _today),
            })
    return sorted(items, key=_weak_sort_key)

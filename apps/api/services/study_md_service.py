"""
Service: STUDY.md — due concepts and raw content.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from gonghaebun.study_loop.review_due import get_due_concepts
from gonghaebun.study_md.parser import parse_study_md

import apps.api.config as config


def get_due(study_md_path: Path | None = None) -> list[dict]:
    """
    Return concepts due for review.

    Each item: {concept_id, next_review (ISO str or None), overdue (bool)}.
    Returns [] if STUDY.md does not exist.
    """
    path = study_md_path or config.STUDY_MD
    if not path.exists():
        return []

    today = date.today()
    due_ids = get_due_concepts(path, today)

    records = parse_study_md(path)
    result = []
    for concept_id in due_ids:
        record = records.get(concept_id)
        next_review = record.next_review if record else None
        if next_review is None:
            overdue = True
        else:
            try:
                overdue = date.fromisoformat(next_review) < today
            except ValueError:
                overdue = True
        result.append({
            "concept_id": concept_id,
            "next_review": next_review,
            "overdue": overdue,
        })
    return result


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

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

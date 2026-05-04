"""
review_due.py — find concepts due for review and locate their question banks.

Functions:
  get_due_concepts(study_md_path, today) → list[str]
  find_question_bank(bank_root, concept_id) → Path
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from gonghaebun.study_md.parser import parse_study_md


def get_due_concepts(
    study_md_path: Path,
    today: date | None = None,
) -> list[str]:
    """
    Return concept IDs whose next_review date is on or before today.

    Parameters
    ----------
    study_md_path : Path
        Path to STUDY.md (may not exist — returns [] in that case).
    today : date | None
        Reference date; defaults to date.today().

    Returns
    -------
    list of concept_id strings, in the order they appear in STUDY.md.
    Concepts with no next_review date are treated as due immediately.
    """
    if today is None:
        today = date.today()

    records = parse_study_md(study_md_path)
    due: list[str] = []
    for concept_id, record in records.items():
        if record.next_review is None:
            due.append(concept_id)
        else:
            try:
                review_date = date.fromisoformat(record.next_review)
            except ValueError:
                # Malformed date — treat as due
                due.append(concept_id)
                continue
            if review_date <= today:
                due.append(concept_id)
    return due


def find_question_bank(bank_root: Path, concept_id: str) -> Path:
    """
    Locate the accepted question bank for a concept.

    Enforces the layout:
        {bank_root}/{concept_id}/questions.accepted.json

    Raises
    ------
    FileNotFoundError
        If the file does not exist.  The error message names the exact
        expected path so the user knows what to create.
    """
    expected = bank_root / concept_id / "questions.accepted.json"
    if not expected.exists():
        raise FileNotFoundError(
            f"No question bank found for concept '{concept_id}'. "
            f"Expected: {expected}"
        )
    return expected

"""
Service: question bank — list banks and load questions.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from gonghaebun.pipeline.io import load_questions

import apps.api.config as config


def safe_resolve_under(root: Path, relative_path: str) -> Path:
    """
    Resolve relative_path under root.

    Raises ValueError if the resolved path escapes root (path traversal guard).
    """
    resolved = (root / relative_path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(
            f"Path {relative_path!r} resolves outside of bank root. "
            "Path traversal is not allowed."
        )
    return resolved


def list_banks(bank_root: Path | None = None) -> list[dict]:
    """
    Scan bank_root for questions.accepted.json files.

    Returns [{concept_id, question_count}] sorted by concept_id.
    """
    root = bank_root or config.BANK_ROOT
    if not root.exists():
        return []

    results = []
    for path in sorted(root.glob("**/questions.accepted.json")):
        concept_id = path.parent.name
        try:
            questions = load_questions(path)
        except Exception:
            continue
        results.append({"concept_id": concept_id, "question_count": len(questions)})
    return results


def load_bank(concept_id: str, bank_root: Path | None = None) -> list[dict]:
    """
    Load questions for concept_id from bank_root/{concept_id}/questions.accepted.json.

    Returns list of question dicts.
    Raises FileNotFoundError if the bank does not exist.
    """
    root = bank_root or config.BANK_ROOT
    path = root / concept_id / "questions.accepted.json"
    if not path.exists():
        raise FileNotFoundError(f"No question bank found for concept {concept_id!r} at {path}")
    questions = load_questions(path)
    return [dataclasses.asdict(q) for q in questions]

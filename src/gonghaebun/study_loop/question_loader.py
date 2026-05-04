"""
Load MVP2 accepted questions for a recall session.

Thin wrapper over pipeline/io.load_questions() with an optional question limit.
"""
from __future__ import annotations

from pathlib import Path

from gonghaebun.models.question_bank import Question
from gonghaebun.pipeline.io import load_questions


def load_recall_questions(
    questions_path: str | Path,
    limit: int | None = None,
) -> list[Question]:
    """
    Load accepted questions from a questions.accepted.json file.

    All questions in a .accepted.json file have status="accepted" (guaranteed
    by export_accepted). This function does not re-filter by status.

    Parameters
    ----------
    questions_path : path to the questions.accepted.json file
    limit          : if set, return only the first `limit` questions
                     (ordered by question_id, i.e. the sort order from io.py)

    Returns
    -------
    list[Question] — may be empty if the file is empty

    Raises
    ------
    FileNotFoundError : if questions_path does not exist
    ValueError        : if the file content is not a JSON list
    """
    path = Path(questions_path)
    if not path.exists():
        raise FileNotFoundError(f"Questions file not found: {path}")

    questions = load_questions(path)

    if limit is not None:
        questions = questions[:limit]

    return questions

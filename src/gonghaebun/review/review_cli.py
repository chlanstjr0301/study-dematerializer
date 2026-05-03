"""
MVP2 Review CLI: interactive question review loop.

Non-interactive core (apply_review_action, review_questions) is fully
testable without stdin. run_review_cli wraps it with stdin/stdout prompts.
No LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.models.question_bank import Question, ReviewRecord
from gonghaebun.pipeline.io import (
    export_accepted,
    load_questions,
    save_questions,
    save_review_records,
)

# ---------------------------------------------------------------------------
# Action normalization tables
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, str] = {
    "a": "accept",
    "accept": "accept",
    "r": "reject",
    "reject": "reject",
    "s": "skip",
    "skip": "skip",
    "e": "edit",
    "edit": "edit",
}

_STATUS_MAP: dict[str, str] = {
    "accept": "accepted",
    "reject": "rejected",
    "skip": "skipped",
    "edit": "edited",
}

# ---------------------------------------------------------------------------
# Non-interactive core (testable without stdin)
# ---------------------------------------------------------------------------


def apply_review_action(
    question: Question,
    action: str,
    review_index: int,
    edited_question: str | None = None,
    edited_expected_answer: str | None = None,
    reviewed_at: str | None = None,
) -> ReviewRecord:
    """
    Apply a single review action to a Question. Mutates question in-place.

    Supported action values: "a"/"accept", "r"/"reject", "s"/"skip", "e"/"edit".
    On "edit", optional edited_question and edited_expected_answer overwrite
    the corresponding fields when provided and non-empty.

    Returns a ReviewRecord capturing the before/after state.
    Raises ValueError for unknown action strings.
    """
    normalized = _ACTION_MAP.get(action.strip().lower())
    if normalized is None:
        raise ValueError(
            f"Unknown review action: {action!r}. "
            f"Valid: {sorted(set(_ACTION_MAP.values()))}"
        )

    # Capture state BEFORE mutation
    before_question = question.question
    before_expected_answer = question.expected_answer

    # Apply mutation
    after_question: str | None = None
    after_expected_answer: str | None = None

    if normalized == "edit":
        if edited_question:
            after_question = edited_question
            question.question = edited_question
        if edited_expected_answer:
            after_expected_answer = edited_expected_answer
            question.expected_answer = edited_expected_answer

    question.status = _STATUS_MAP[normalized]  # type: ignore[assignment]

    return ReviewRecord(
        review_id=f"rev_{question.question_id}_{review_index:06d}",
        question_id=question.question_id,
        action=normalized,  # type: ignore[arg-type]
        before_question=before_question,
        after_question=after_question,
        before_expected_answer=before_expected_answer,
        after_expected_answer=after_expected_answer,
        reviewed_at=reviewed_at or datetime.now(timezone.utc).isoformat(),
    )


def review_questions(
    questions: list[Question],
    actions: list[dict],
) -> tuple[list[Question], list[ReviewRecord]]:
    """
    Apply a batch of review actions. Non-interactive and testable.

    Each action dict must contain:
      - question_id  (str)
      - action       (str; "a"/"accept", "r"/"reject", "s"/"skip", "e"/"edit")
      Optional:
      - edited_question        (str)
      - edited_expected_answer (str)
      - reviewed_at            (ISO 8601 str; defaults to now() if absent)

    Raises ValueError if a question_id is not found in questions.
    Returns (questions in original order, list of ReviewRecords).
    """
    question_map: dict[str, Question] = {q.question_id: q for q in questions}
    records: list[ReviewRecord] = []

    for review_index, action_dict in enumerate(actions):
        qid = action_dict["question_id"]
        if qid not in question_map:
            raise ValueError(
                f"Unknown question_id: {qid!r}. "
                f"Available ids: {sorted(question_map)}"
            )
        record = apply_review_action(
            question=question_map[qid],
            action=action_dict["action"],
            review_index=review_index,
            edited_question=action_dict.get("edited_question"),
            edited_expected_answer=action_dict.get("edited_expected_answer"),
            reviewed_at=action_dict.get("reviewed_at"),
        )
        records.append(record)

    return questions, records


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------


def run_review_cli(
    questions_path: Path,
    output_dir: Path,
) -> list[ReviewRecord]:
    """
    Interactive review loop.

    Loads questions from questions_path, prompts the user for each candidate,
    then saves results to output_dir:
      questions.reviewed.json
      questions.accepted.json
      review_records.json

    EOFError (piped input exhausted) is treated as quit.
    Returns the list of ReviewRecords created during this session.
    """
    questions = load_questions(questions_path)
    records: list[ReviewRecord] = []
    review_index = 0

    candidates = [q for q in questions if q.status == "candidate"]

    should_quit = False
    for question in candidates:
        if should_quit:
            break
        _print_question(question)
        # Inner retry loop: re-prompt on unrecognised input
        while True:
            try:
                raw = input("\n[a]ccept / [r]eject / [e]dit / [s]kip / [q]uit: ").strip().lower()
            except EOFError:
                should_quit = True
                break

            if raw in ("q", "quit"):
                should_quit = True
                break

            if raw in ("e", "edit"):
                try:
                    new_q = input("  Updated question text  (blank = keep): ").strip()
                    new_a = input("  Updated expected_answer (blank = keep): ").strip()
                except EOFError:
                    should_quit = True
                    break
                record = apply_review_action(
                    question=question,
                    action="edit",
                    review_index=review_index,
                    edited_question=new_q or None,
                    edited_expected_answer=new_a or None,
                )
                records.append(record)
                review_index += 1
                break
            else:
                try:
                    record = apply_review_action(
                        question=question,
                        action=raw,
                        review_index=review_index,
                    )
                    records.append(record)
                    review_index += 1
                    break
                except ValueError:
                    print(f"  Unknown action: {raw!r}. Valid: a / r / e / s / q")

    _save_output(questions, records, Path(output_dir))
    return records


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _save_output(
    questions: list[Question],
    records: list[ReviewRecord],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    save_questions(output_dir / "questions.reviewed.json", questions)
    export_accepted(questions, output_dir / "questions.accepted.json")
    save_review_records(output_dir / "review_records.json", records)


def _print_question(question: Question) -> None:
    ev = question.evidence
    print("\n" + "─" * 60)
    print(f"  ID       : {question.question_id}")
    print(f"  Type     : {question.question_type}  [{question.difficulty}]")
    print(f"  Question : {question.question}")
    print(f"  Answer   : {question.expected_answer[:500]}")
    print(f"  Source   : {ev.source_file}  lines {ev.start_line}–{ev.end_line}")
    print(f"  Evidence : {ev.source_text[:500]}")

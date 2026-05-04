"""
White Recall session loop.

Presents each question to the learner WITHOUT showing the source text,
collects a free-text answer, grades it via the supplied AnswerGrader,
and returns the list of AttemptResults.

Interactive mode follows the run_review_cli EOFError pattern from review_cli.py.
"""
from __future__ import annotations

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Question
from gonghaebun.study_loop.mastery import AttemptResult


def run_white_recall_session(
    questions: list[Question],
    grader: AnswerGrader,
    *,
    no_interactive: bool = False,
    default_answer: str = "",
) -> list[AttemptResult]:
    """
    Run an interactive (or batch) White Recall session.

    For each question:
      1. Print the question text (no source material shown).
      2. Collect the learner's answer (multi-line; blank line = done).
         If no_interactive=True, use default_answer immediately.
      3. Grade via grader.grade().
      4. Print grading feedback.
      5. On EOFError → break and return partial results.

    Parameters
    ----------
    questions      : list of Question objects to present
    grader         : any AnswerGrader (SelfGrader, LLMGrader, …)
    no_interactive : if True skip all prompts; use default_answer
    default_answer : response to use when no_interactive=True

    Returns
    -------
    list[AttemptResult] — may be shorter than questions on EOFError / empty list
    """
    results: list[AttemptResult] = []

    for question in questions:
        _print_question(question)

        if no_interactive:
            learner_response = default_answer
        else:
            learner_response = _collect_answer()
            if learner_response is None:  # EOFError during collection
                break

        grading = grader.grade(
            question=question.question,
            expected_answer=question.expected_answer,
            evidence_text=question.evidence.source_text,
            learner_response=learner_response,
        )

        if not no_interactive:
            _print_feedback(grading)

        results.append(AttemptResult(
            question=question,
            learner_response=learner_response,
            grading=grading,
        ))

    return results


def run_white_recall_batch(
    questions: list[Question],
    responses: list[tuple[str, GradingResult]],
) -> list[AttemptResult]:
    """
    Non-interactive batch path for tests.

    Pairs each question with a pre-built (learner_response, GradingResult).
    Raises ValueError if len(questions) != len(responses).
    """
    if len(questions) != len(responses):
        raise ValueError(
            f"questions ({len(questions)}) and responses ({len(responses)}) "
            "must have the same length"
        )
    return [
        AttemptResult(
            question=q,
            learner_response=resp,
            grading=grading,
        )
        for q, (resp, grading) in zip(questions, responses)
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _print_question(question: Question) -> None:
    print("\n" + "═" * 60)
    print(f"  Question  : {question.question}")
    print(f"  Type      : {question.question_type}  [{question.difficulty}]")
    print(f"  Section   : {question.evidence.source_file}  "
          f"lines {question.evidence.start_line}–{question.evidence.end_line}")
    print("─" * 60)
    print("  Answer WITHOUT looking at notes or materials.")
    print("  (Blank line to finish.)")


def _collect_answer() -> str | None:
    """
    Collect a multi-line answer from stdin.

    Returns the answer string, or None on EOFError.
    An empty line terminates input.
    """
    lines: list[str] = []
    try:
        while True:
            try:
                line = input()
            except EOFError:
                return None
            if line == "":
                break
            lines.append(line)
    except KeyboardInterrupt:
        return None
    return "\n".join(lines)


def _print_feedback(grading: GradingResult) -> None:
    print()
    print(f"  Accuracy  : {int(grading.accuracy_score * 100)}%  "
          f"({grading.mastery_suggestion})")
    print(f"  Feedback  : {grading.feedback}")
    if grading.missing_elements:
        print("  Missing   : " + "; ".join(grading.missing_elements[:3]))
    if grading.errors:
        print("  Errors    : " + "; ".join(grading.errors[:3]))
    if grading.needs_human_review:
        print("  [!] Marked for human review.")

"""
SelfGrader — learner-provided self-assessment grader.

The learner rates their own answer on a 0–3 scale after seeing the expected
answer and source evidence. No API key or LLM required.
"""
from __future__ import annotations

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.study_md.writer import compute_mastery_state

# Maps self-score (0–3) to accuracy_score (0.0–1.0).
# Defined here for reuse; also exposed from study_loop/mastery.py.
SELF_SCORE_TO_ACCURACY: dict[int, float] = {
    0: 0.0,
    1: 0.33,
    2: 0.67,
    3: 1.0,
}

_VALID_SCORES = frozenset(SELF_SCORE_TO_ACCURACY)


def self_score_to_grading_result(score: int) -> GradingResult:
    """
    Convert a self-score (0–3) to a GradingResult.

    Raises ValueError if score is not in {0, 1, 2, 3}.
    """
    if score not in _VALID_SCORES:
        raise ValueError(
            f"self_score must be 0, 1, 2, or 3; got {score!r}"
        )
    accuracy = SELF_SCORE_TO_ACCURACY[score]
    mastery = compute_mastery_state(accuracy)
    return GradingResult(
        accuracy_score=accuracy,
        missing_elements=[],
        errors=[],
        feedback=f"Self-assessed score: {score}/3.",
        mastery_suggestion=mastery,
        confidence=1.0,
        needs_human_review=False,
        evidence_alignment="supported",
        raw_response=f"self:{score}",
    )


class SelfGrader(AnswerGrader):
    """
    Grader that shows the expected answer and evidence to the learner,
    then prompts them to rate their own response on a 0–3 scale.

    Parameters
    ----------
    default_score : int | None
        When set, skip the interactive prompt and use this score directly.
        Useful for --no-interactive batch mode.
    """

    def __init__(self, default_score: int | None = None) -> None:
        if default_score is not None and default_score not in _VALID_SCORES:
            raise ValueError(
                f"default_score must be 0–3; got {default_score!r}"
            )
        self._default_score = default_score

    def grade(
        self,
        question: str,
        expected_answer: str,
        evidence_text: str,
        learner_response: str,
    ) -> GradingResult:
        """
        Show expected answer + evidence, prompt for self-score.

        If default_score was set at construction, skip the prompt.
        """
        if self._default_score is not None:
            return self._grade_with_score(self._default_score)

        # Interactive: show reference material, prompt for score
        print("\n" + "─" * 60)
        print("  Expected answer (source-grounded):")
        print(f"  {expected_answer[:500]}")
        print()
        print("  Source evidence:")
        print(f"  {evidence_text[:300]}")
        print("─" * 60)

        score = self._prompt_score()
        return self._grade_with_score(score)

    def _grade_with_score(self, score: int) -> GradingResult:
        return self_score_to_grading_result(score)

    @staticmethod
    def _prompt_score() -> int:
        """Prompt for a 0–3 score, re-prompting on invalid input."""
        while True:
            try:
                raw = input("  Self-score [0=blank, 1=poor, 2=ok, 3=solid]: ").strip()
            except EOFError:
                return 0
            try:
                score = int(raw)
                if score in _VALID_SCORES:
                    return score
                print(f"  Enter 0, 1, 2, or 3 (got {raw!r}).")
            except ValueError:
                print(f"  Enter a number 0–3 (got {raw!r}).")

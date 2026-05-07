"""
Mastery mapping utilities for MVP3.

- SELF_SCORE_TO_ACCURACY  : int 0-3 → float accuracy
- QUESTION_TYPE_TO_REP    : MVP2 question_type → representation_type
- AttemptResult           : (question, learner_response, grading)
- self_score_to_accuracy()
- question_type_to_rep()
- aggregate_by_rep()       : average accuracy scores grouped by rep_type
"""
from __future__ import annotations

from dataclasses import dataclass

from gonghaebun.grading.schemas import GradingResult
from gonghaebun.llm.errors import LLMError  # noqa: F401 (re-exported for convenience)
from gonghaebun.models.question_bank import Question

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SELF_SCORE_TO_ACCURACY: dict[int, float] = {
    0: 0.0,
    1: 0.33,
    2: 0.67,
    3: 1.0,
}

# Representations that contribute to overall mastery calculation (weakest-link).
# intuitive and visual are useful for learning but do not gate mastery.
MASTERY_SCORED_REPS: frozenset[str] = frozenset({"formal", "counterexample", "proof_schema"})

QUESTION_TYPE_TO_REP: dict[str, str] = {
    "definition_recall":   "formal",
    "theorem_recall":      "formal",
    "proof_schema_recall": "proof_schema",
    "example_explanation": "counterexample",
    "exercise_recall":     "formal",
    "intuition_recall":    "intuitive",
}

_VALID_SCORES = frozenset(SELF_SCORE_TO_ACCURACY)

# ---------------------------------------------------------------------------
# AttemptResult
# ---------------------------------------------------------------------------


@dataclass
class AttemptResult:
    """
    A single learner answer attempt with its grading result.

    question        : the Question object that was presented
    learner_response: the learner's free-text answer
    grading         : GradingResult from any AnswerGrader
    """

    question: Question
    learner_response: str
    grading: GradingResult


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def self_score_to_accuracy(score: int) -> float:
    """
    Convert a self-score (0–3) to a float accuracy (0.0–1.0).

    Raises ValueError if score is not in {0, 1, 2, 3}.
    """
    if score not in _VALID_SCORES:
        raise ValueError(
            f"self_score must be 0, 1, 2, or 3; got {score!r}"
        )
    return SELF_SCORE_TO_ACCURACY[score]


def question_type_to_rep(question_type: str) -> str:
    """
    Map an MVP2 question_type to a representation_type.

    Returns "formal" as a fallback for unmapped types.
    """
    return QUESTION_TYPE_TO_REP.get(question_type, "formal")


def aggregate_by_rep(attempt_results: list[AttemptResult]) -> dict[str, float]:
    """
    Group attempt results by representation_type and average their accuracy scores.

    Returns a dict {rep_type: mean_accuracy}.
    Empty list → empty dict.
    """
    groups: dict[str, list[float]] = {}
    for ar in attempt_results:
        rep = question_type_to_rep(ar.question.question_type)
        groups.setdefault(rep, []).append(ar.grading.accuracy_score)

    return {rep: sum(scores) / len(scores) for rep, scores in groups.items()}

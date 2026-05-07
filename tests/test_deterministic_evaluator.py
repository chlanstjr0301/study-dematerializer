"""
Tests for DeterministicEvaluator core logic.

Step 4: term coverage, misconception detection, scoring, normalization,
needs_human_review triggers, feedback generation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gonghaebun.grading.deterministic_evaluator import (
    DeterministicEvaluator,
    _check_terms,
    _compute_score,
    _detect_misconceptions,
    _generate_feedback,
    _needs_human_review,
    _normalize,
)
from gonghaebun.models.evaluation_output import EvaluationOutput
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.rubric import ConceptRubric, MisconceptionCheck, TermCheck

# ---------------------------------------------------------------------------
# Fixtures: load real compactness card + rubric
# ---------------------------------------------------------------------------

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"


@pytest.fixture
def card() -> GroundTruthCard:
    path = CARDS_DIR / "real_analysis" / "compactness.card.json"
    return GroundTruthCard.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def rubric() -> ConceptRubric:
    path = CARDS_DIR / "real_analysis" / "compactness.rubric.json"
    return ConceptRubric.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def evaluator(card: GroundTruthCard, rubric: ConceptRubric) -> DeterministicEvaluator:
    return DeterministicEvaluator(card, rubric)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercases_english(self) -> None:
        assert "open cover" in _normalize("Open Cover")

    def test_strips_korean_particle_eul(self) -> None:
        # "compact을" → particle stripped
        result = _normalize("compact을 설명하세요")
        assert "compact" in result

    def test_strips_korean_particle_neun(self) -> None:
        result = _normalize("집합은 compact이다")
        assert "집합" in result

    def test_preserves_math_symbols(self) -> None:
        result = _normalize("K ⊂ ∪ G_alpha")
        assert "⊂" in result
        assert "∪" in result

    def test_normalizes_whitespace(self) -> None:
        result = _normalize("open   cover   finite")
        assert result == "open cover finite"

    def test_empty_string(self) -> None:
        assert _normalize("") == ""

    def test_mixed_korean_english(self) -> None:
        result = _normalize("모든 열린 덮개에 대해 finite subcover가 존재")
        assert "finite subcover" in result


# ---------------------------------------------------------------------------
# _check_terms
# ---------------------------------------------------------------------------


class TestCheckTerms:
    def test_full_coverage(self) -> None:
        terms = [
            TermCheck(term="open cover", weight=2.0),
            TermCheck(term="finite subcover", weight=2.0),
        ]
        coverage, missing = _check_terms("open cover and finite subcover", terms)
        assert coverage == 1.0
        assert missing == []

    def test_partial_coverage(self) -> None:
        terms = [
            TermCheck(term="open cover", weight=2.0),
            TermCheck(term="finite subcover", weight=2.0),
        ]
        coverage, missing = _check_terms("open cover only", terms)
        assert coverage == 0.5
        assert missing == ["finite subcover"]

    def test_zero_coverage(self) -> None:
        terms = [TermCheck(term="open cover", weight=1.0)]
        coverage, missing = _check_terms("nothing relevant", terms)
        assert coverage == 0.0
        assert "open cover" in missing

    def test_alias_match(self) -> None:
        terms = [
            TermCheck(term="open cover", weight=1.0, aliases=["열린 덮개"]),
        ]
        coverage, _ = _check_terms("열린 덮개를 사용하여", terms)
        assert coverage == 1.0

    def test_weighted_coverage(self) -> None:
        terms = [
            TermCheck(term="a", weight=3.0),
            TermCheck(term="b", weight=1.0),
        ]
        coverage, _ = _check_terms("a is here", terms)
        assert coverage == 0.75

    def test_empty_terms_list(self) -> None:
        coverage, missing = _check_terms("anything", [])
        assert coverage == 0.0
        assert missing == []

    def test_case_insensitive(self) -> None:
        terms = [TermCheck(term="Heine-Borel", weight=1.0)]
        coverage, _ = _check_terms("heine-borel theorem", terms)
        assert coverage == 1.0


# ---------------------------------------------------------------------------
# _detect_misconceptions
# ---------------------------------------------------------------------------


class TestDetectMisconceptions:
    def test_no_misconceptions(self, card: GroundTruthCard) -> None:
        checks = [
            MisconceptionCheck(
                misconception_id="bounded_implies_compact",
                trigger_patterns=["bounded.*compact"],
                severity="critical",
            ),
        ]
        penalty, ids, claims = _detect_misconceptions(
            "open cover has finite subcover", checks, card,
        )
        assert penalty == 0.0
        assert ids == []

    def test_detects_critical_misconception(self, card: GroundTruthCard) -> None:
        checks = [
            MisconceptionCheck(
                misconception_id="bounded_implies_compact",
                trigger_patterns=["bounded.*compact"],
                severity="critical",
            ),
        ]
        penalty, ids, _ = _detect_misconceptions(
            "bounded sets are compact", checks, card,
        )
        assert penalty == 0.15
        assert "bounded_implies_compact" in ids

    def test_penalty_capped_at_050(self, card: GroundTruthCard) -> None:
        checks = [
            MisconceptionCheck(
                misconception_id=f"mc_{i}",
                trigger_patterns=[f"pattern{i}"],
                severity="critical",
            )
            for i in range(10)
        ]
        text = " ".join(f"pattern{i}" for i in range(10))
        penalty, ids, _ = _detect_misconceptions(text, checks, card)
        assert penalty == 0.50
        assert len(ids) == 10

    def test_one_match_per_misconception(self, card: GroundTruthCard) -> None:
        checks = [
            MisconceptionCheck(
                misconception_id="bounded_implies_compact",
                trigger_patterns=["bounded.*compact", "유계.*compact"],
                severity="critical",
            ),
        ]
        penalty, ids, _ = _detect_misconceptions(
            "bounded implies compact and 유계 compact", checks, card,
        )
        # Should match once, not twice
        assert penalty == 0.15
        assert len(ids) == 1


# ---------------------------------------------------------------------------
# _compute_score
# ---------------------------------------------------------------------------


class TestComputeScore:
    def test_full_coverage_no_penalty(self) -> None:
        assert _compute_score(1.0, 0.0) == 1.0

    def test_full_coverage_with_penalty(self) -> None:
        assert _compute_score(1.0, 0.15) == 0.85

    def test_half_coverage_no_penalty(self) -> None:
        assert _compute_score(0.5, 0.0) == 0.5

    def test_zero_coverage(self) -> None:
        assert _compute_score(0.0, 0.15) == 0.0

    def test_clamped_to_zero(self) -> None:
        assert _compute_score(0.1, 0.95) >= 0.0


# ---------------------------------------------------------------------------
# _needs_human_review
# ---------------------------------------------------------------------------


class TestNeedsHumanReview:
    def test_ambiguous_coverage_no_misconceptions(self) -> None:
        assert _needs_human_review(0.50, [], False, 100) is True

    def test_coverage_040_triggers(self) -> None:
        assert _needs_human_review(0.40, [], False, 100) is True

    def test_coverage_060_triggers(self) -> None:
        assert _needs_human_review(0.60, [], False, 100) is True

    def test_ambiguous_with_misconceptions_no_trigger(self) -> None:
        # Misconceptions present → not ambiguous condition 1
        assert _needs_human_review(0.50, ["mc1"], False, 100) is False

    def test_short_response_triggers(self) -> None:
        assert _needs_human_review(0.80, [], False, 15) is True

    def test_empty_response_no_trigger(self) -> None:
        # Empty (len=0) is handled upstream, not by review
        assert _needs_human_review(0.0, [], False, 0) is False

    def test_long_response_triggers(self) -> None:
        assert _needs_human_review(0.80, [], False, 2500) is True

    def test_high_coverage_critical_misconception(self) -> None:
        assert _needs_human_review(0.80, ["mc1"], True, 100) is True

    def test_clear_pass_no_review(self) -> None:
        assert _needs_human_review(0.90, [], False, 100) is False

    def test_clear_fail_no_review(self) -> None:
        assert _needs_human_review(0.20, [], False, 100) is False


# ---------------------------------------------------------------------------
# _generate_feedback
# ---------------------------------------------------------------------------


class TestGenerateFeedback:
    def test_passed_feedback(self) -> None:
        fb = _generate_feedback(True, [], [])
        assert "잘 설명했습니다" in fb

    def test_missing_terms_feedback(self) -> None:
        fb = _generate_feedback(False, ["open cover", "finite subcover"], [])
        assert "누락" in fb
        assert "open cover" in fb

    def test_misconception_feedback(self) -> None:
        fb = _generate_feedback(False, [], ["bounded_implies_compact"])
        assert "오개념" in fb

    def test_combined_feedback(self) -> None:
        fb = _generate_feedback(False, ["open cover"], ["bounded_implies_compact"])
        assert "누락" in fb
        assert "오개념" in fb


# ---------------------------------------------------------------------------
# DeterministicEvaluator integration
# ---------------------------------------------------------------------------


class TestEvaluatorEmpty:
    """Empty / whitespace answers."""

    def test_empty_self_explain(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation("formal", "")
        assert result.score == 0.0
        assert result.mastery == "unknown"
        assert result.passed is False

    def test_whitespace_self_explain(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation("formal", "   \t\n  ")
        assert result.score == 0.0

    def test_empty_mapping(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping("formal_to_counterexample", "")
        assert result.score == 0.0
        assert result.mapping_failures == ["formal_to_counterexample"]

    def test_empty_recall(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_recall("")
        assert result.score == 0.0

    def test_empty_quiz(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_misconception_quiz([])
        assert result.score == 0.0


class TestEvaluatorOutputType:
    """All methods return EvaluationOutput."""

    def test_self_explain_returns_eval_output(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation("formal", "open cover finite subcover")
        assert isinstance(result, EvaluationOutput)

    def test_mapping_returns_eval_output(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping("formal_to_counterexample", "test")
        assert isinstance(result, EvaluationOutput)

    def test_recall_returns_eval_output(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_recall("test")
        assert isinstance(result, EvaluationOutput)

    def test_quiz_returns_eval_output(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_misconception_quiz([
            {"misconception_id": "bounded_implies_compact", "learner_answer": False},
        ])
        assert isinstance(result, EvaluationOutput)


class TestEvaluatorMisconceptionQuiz:
    """Misconception quiz is purely deterministic."""

    def test_all_correct(self, evaluator: DeterministicEvaluator) -> None:
        results = [
            {"misconception_id": "bounded_implies_compact", "learner_answer": False},
            {"misconception_id": "heine_borel_in_R", "learner_answer": True},
            {"misconception_id": "open_cover_definition_correct", "learner_answer": True},
        ]
        output = evaluator.evaluate_misconception_quiz(results)
        assert output.score == 1.0
        assert output.passed is True
        assert output.misconception_tags == []
        assert output.needs_human_review is False

    def test_all_wrong(self, evaluator: DeterministicEvaluator) -> None:
        results = [
            {"misconception_id": "bounded_implies_compact", "learner_answer": True},
            {"misconception_id": "heine_borel_in_R", "learner_answer": False},
            {"misconception_id": "open_cover_definition_correct", "learner_answer": False},
        ]
        output = evaluator.evaluate_misconception_quiz(results)
        assert output.score == 0.0
        assert output.passed is False
        assert len(output.misconception_tags) == 3

    def test_partial_correct(self, evaluator: DeterministicEvaluator) -> None:
        results = [
            {"misconception_id": "bounded_implies_compact", "learner_answer": False},  # correct
            {"misconception_id": "heine_borel_in_R", "learner_answer": False},  # wrong
        ]
        output = evaluator.evaluate_misconception_quiz(results)
        assert output.score == 0.5
        assert "heine_borel_in_R" in output.misconception_tags
        assert "bounded_implies_compact" not in output.misconception_tags

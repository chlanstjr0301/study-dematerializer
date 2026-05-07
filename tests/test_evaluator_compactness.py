"""
Compactness-specific evaluator tests.

Step 4: correct formal, partial, misconception, mapping tasks, recall,
needs_human_review for ambiguous cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gonghaebun.grading.deterministic_evaluator import DeterministicEvaluator
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.rubric import ConceptRubric

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
# Self-explanation: formal definition
# ---------------------------------------------------------------------------


class TestSelfExplainFormal:
    def test_correct_formal_korean(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "거리 공간에서 모든 열린 덮개에 대해 유한 부분덮개가 존재하면 "
            "그 집합은 compact이다.",
        )
        assert result.score >= 0.80
        assert result.mastery == "solid"
        assert result.passed is True
        assert len(result.misconception_tags) == 0

    def test_correct_formal_english(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "A subset of a metric space is compact if every open cover "
            "has a finite subcover.",
        )
        assert result.score >= 0.80
        assert result.passed is True

    def test_partial_formal_missing_terms(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "compact means finite subcover exists for a metric space.",
        )
        # Missing "open cover" and "every"
        assert result.score < 0.80
        assert "open cover" in result.missing_elements

    def test_formal_with_misconception(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "Every bounded set is compact because it has a finite subcover "
            "for every open cover in a metric space.",
        )
        # Has the terms but also has misconception
        assert "bounded_implies_compact" in result.misconception_tags


# ---------------------------------------------------------------------------
# Self-explanation: counterexample
# ---------------------------------------------------------------------------


class TestSelfExplainCounterexample:
    def test_correct_counterexample(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "counterexample",
            "(0,1)은 compact하지 않다. 열린 덮개 {(1/n, 1) : n=2,3,...}을 생각하면 "
            "유한 부분덮개가 존재하지 않는다.",
        )
        assert result.score >= 0.70
        assert result.passed is True

    def test_counterexample_without_open_cover(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "counterexample",
            "(0,1) is not compact because it is not closed.",
        )
        # Missing open cover argument → misconception trigger + missing terms
        assert result.passed is False


# ---------------------------------------------------------------------------
# Self-explanation: proof schema
# ---------------------------------------------------------------------------


class TestSelfExplainProofSchema:
    def test_correct_proof_schema(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "proof_schema",
            "Heine-Borel 정리: R^n에서 집합이 compact일 필요충분조건은 "
            "closed and bounded인 것이다. 증명은 open cover를 잡고 "
            "finite subcover가 존재함을 nested intervals (bisection)으로 보인다.",
        )
        assert result.score >= 0.70
        assert result.passed is True


# ---------------------------------------------------------------------------
# Mapping tasks
# ---------------------------------------------------------------------------


class TestMappingFormalToCounterexample:
    def test_correct_mapping(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping(
            "formal_to_counterexample",
            "(0,1)에 대해 open cover {(1/n, 1)}을 잡으면 finite subcover가 없다. "
            "따라서 no finite subcover이므로 compact하지 않다.",
        )
        assert result.passed is True
        assert result.mapping_failures == []

    def test_mapping_failure_no_cover(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping(
            "formal_to_counterexample",
            "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
        )
        assert result.passed is False
        assert "formal_to_counterexample" in result.mapping_failures
        # Should detect missing_open_cover_argument misconception
        assert any(
            mid in result.misconception_tags
            for mid in ["missing_open_cover_argument"]
        )

    def test_mapping_with_heine_borel_misuse(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping(
            "formal_to_counterexample",
            "(0,1) is not compact. By Heine-Borel in any metric space, "
            "it must be closed and bounded.",
        )
        assert result.passed is False


class TestMappingCounterexampleToFormal:
    def test_correct_mapping(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping(
            "counterexample_to_formal",
            "(0,1)이 compact하지 않다는 사실에서, compact 집합은 "
            "every open cover에 대해 finite subcover가 존재해야 한다. "
            "R^n에서는 closed and bounded.",
        )
        assert result.score >= 0.70
        assert result.passed is True


class TestMappingFormalCEToProofSchema:
    def test_correct_mapping(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_mapping(
            "formal_counterexample_to_proof_schema",
            "Heine-Borel 정리: closed and bounded이면 compact. "
            "증명에서 open cover를 잡고 nested intervals로 finite subcover를 구성.",
        )
        assert result.score >= 0.70
        assert result.passed is True


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------


class TestRecall:
    def test_good_recall(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_recall(
            "compact 집합은 모든 open cover에 대해 finite subcover가 존재하는 집합이다. "
            "Heine-Borel에 의해 R^n에서 closed and bounded이면 compact이다.",
        )
        assert result.score >= 0.50
        assert result.passed is True

    def test_poor_recall(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_recall("compact는 중요한 개념이다.")
        assert result.score < 0.50
        assert result.passed is False

    def test_recall_lower_threshold(self, evaluator: DeterministicEvaluator) -> None:
        # Recall threshold is 0.50, lower than self-explain (0.70)
        result = evaluator.evaluate_recall(
            "compact open cover finite subcover",
        )
        # These terms should give partial coverage; threshold is 0.50
        assert result.passed is True or result.score >= 0.40


# ---------------------------------------------------------------------------
# needs_human_review edge cases
# ---------------------------------------------------------------------------


class TestNeedsHumanReviewCompactness:
    def test_ambiguous_vague_response(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "open cover가 있으면 finite subcover가 있다는 것이 compact의 뜻이다.",
        )
        # Matches "open cover" (w=2) + "finite subcover" (w=2) but misses
        # "every" (w=1) + "metric space" (w=1) → coverage = 4/6 ≈ 0.67.
        # However with no misconceptions and score in passing range,
        # this is not ambiguous. Use a response that lands in 0.40–0.60:
        result2 = evaluator.evaluate_self_explanation(
            "formal",
            "compact는 every open cover와 관련된 개념이다.",
        )
        # Matches "open cover" (w=2) + "every" (w=1) = 3/6 = 0.50 coverage
        # No misconceptions → ambiguous band → needs_human_review
        assert result2.needs_human_review is True

    def test_short_response_triggers_review(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "compact = 유한",  # < 20 chars
        )
        assert result.needs_human_review is True

    def test_long_response_triggers_review(self, evaluator: DeterministicEvaluator) -> None:
        # 2500+ chars
        filler = "이것은 매우 긴 답변입니다. " * 200
        long_response = (
            f"open cover에 대해 finite subcover가 존재하면 compact이다. "
            f"every metric space에서 {filler}"
        )
        result = evaluator.evaluate_self_explanation("formal", long_response)
        assert result.needs_human_review is True

    def test_clear_pass_no_review(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "A subset of a metric space is compact if every open cover "
            "has a finite subcover.",
        )
        assert result.needs_human_review is False


# ---------------------------------------------------------------------------
# Korean alias matching
# ---------------------------------------------------------------------------


class TestKoreanAliasMatching:
    def test_korean_aliases_in_formal(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "거리 공간의 부분집합이 옹골이란, 모든 열린 덮개가 유한 부분덮개를 가지는 것이다.",
        )
        # "열린 덮개" → "open cover", "유한 부분덮개" → "finite subcover",
        # "모든" → "every", "거리 공간" → "metric space"
        assert result.score >= 0.80
        assert result.passed is True

    def test_mixed_language(self, evaluator: DeterministicEvaluator) -> None:
        result = evaluator.evaluate_self_explanation(
            "formal",
            "모든 open cover에 대해 finite subcover가 존재하면 "
            "metric space의 부분집합은 compact이다.",
        )
        assert result.score >= 0.80

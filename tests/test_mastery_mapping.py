"""Tests for study_loop/mastery.py (MVP3 Step 4)."""
from __future__ import annotations

import pytest

from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Evidence, Question
from gonghaebun.study_loop.mastery import (
    QUESTION_TYPE_TO_REP,
    SELF_SCORE_TO_ACCURACY,
    AttemptResult,
    aggregate_by_rep,
    question_type_to_rep,
    self_score_to_accuracy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EVIDENCE = Evidence(
    source_text="A compact set has every open cover admitting a finite subcover.",
    source_file="test.md",
    start_line=1,
    end_line=3,
    text_hash="abc123",
)

_LONG_TEXT = "A subset K of a metric space X is compact if every open cover has a finite subcover."


def make_question(question_type: str = "definition_recall") -> Question:
    return Question(
        question_id=f"q_doc_b000001_{question_type}",
        document_id="doc",
        source_block_id="doc_b000001",
        question_type=question_type,
        difficulty="medium",
        question="State the definition of compactness.",
        expected_answer=_LONG_TEXT,
        evidence=_EVIDENCE,
        rule_id="R01_definition_recall",
    )


def make_grading(accuracy: float) -> GradingResult:
    from gonghaebun.study_md.writer import compute_mastery_state
    mastery = compute_mastery_state(accuracy)
    return GradingResult(
        accuracy_score=accuracy,
        mastery_suggestion=mastery,
    )


def make_attempt(question_type: str, accuracy: float) -> AttemptResult:
    return AttemptResult(
        question=make_question(question_type),
        learner_response="my answer",
        grading=make_grading(accuracy),
    )


# ---------------------------------------------------------------------------
# TestSelfScoreToAccuracy
# ---------------------------------------------------------------------------


class TestSelfScoreToAccuracy:
    def test_score_0_returns_0_0(self):
        assert self_score_to_accuracy(0) == 0.0

    def test_score_1_returns_0_33(self):
        assert self_score_to_accuracy(1) == pytest.approx(0.33)

    def test_score_2_returns_0_67(self):
        assert self_score_to_accuracy(2) == pytest.approx(0.67)

    def test_score_3_returns_1_0(self):
        assert self_score_to_accuracy(3) == 1.0

    def test_score_negative_raises(self):
        with pytest.raises(ValueError):
            self_score_to_accuracy(-1)

    def test_score_4_raises(self):
        with pytest.raises(ValueError):
            self_score_to_accuracy(4)

    def test_string_score_raises(self):
        with pytest.raises((ValueError, TypeError)):
            self_score_to_accuracy("2")  # type: ignore[arg-type]

    def test_constant_map_has_four_entries(self):
        assert len(SELF_SCORE_TO_ACCURACY) == 4


# ---------------------------------------------------------------------------
# TestQuestionTypeToRep
# ---------------------------------------------------------------------------


class TestQuestionTypeToRep:
    def test_definition_recall_maps_to_formal(self):
        assert question_type_to_rep("definition_recall") == "formal"

    def test_theorem_recall_maps_to_formal(self):
        assert question_type_to_rep("theorem_recall") == "formal"

    def test_proof_schema_recall_maps_to_proof_schema(self):
        assert question_type_to_rep("proof_schema_recall") == "proof_schema"

    def test_example_explanation_maps_to_counterexample(self):
        assert question_type_to_rep("example_explanation") == "counterexample"

    def test_exercise_recall_maps_to_formal(self):
        assert question_type_to_rep("exercise_recall") == "formal"

    def test_intuition_recall_maps_to_intuitive(self):
        assert question_type_to_rep("intuition_recall") == "intuitive"

    def test_unknown_type_falls_back_to_formal(self):
        assert question_type_to_rep("totally_unknown_type") == "formal"

    def test_constant_map_has_six_entries(self):
        assert len(QUESTION_TYPE_TO_REP) == 6


# ---------------------------------------------------------------------------
# TestAggregateByRep
# ---------------------------------------------------------------------------


class TestAggregateByRep:
    def test_empty_list_returns_empty_dict(self):
        assert aggregate_by_rep([]) == {}

    def test_single_attempt_returns_single_entry(self):
        result = aggregate_by_rep([make_attempt("intuition_recall", 0.8)])
        assert "intuitive" in result
        assert result["intuitive"] == pytest.approx(0.8)

    def test_multiple_same_rep_type_averaged(self):
        attempts = [
            make_attempt("definition_recall", 0.6),  # formal
            make_attempt("theorem_recall", 1.0),     # formal
        ]
        result = aggregate_by_rep(attempts)
        assert "formal" in result
        assert result["formal"] == pytest.approx(0.8)

    def test_multiple_different_rep_types_grouped_separately(self):
        attempts = [
            make_attempt("definition_recall", 0.5),    # formal
            make_attempt("intuition_recall", 1.0),     # intuitive
            make_attempt("proof_schema_recall", 0.0),  # proof_schema
        ]
        result = aggregate_by_rep(attempts)
        assert result["formal"] == pytest.approx(0.5)
        assert result["intuitive"] == pytest.approx(1.0)
        assert result["proof_schema"] == pytest.approx(0.0)

    def test_result_accuracy_within_0_to_1(self):
        attempts = [make_attempt("definition_recall", 0.75)]
        result = aggregate_by_rep(attempts)
        for v in result.values():
            assert 0.0 <= v <= 1.0

    def test_three_attempts_same_type_averaged(self):
        attempts = [
            make_attempt("definition_recall", 0.3),
            make_attempt("definition_recall", 0.6),
            make_attempt("definition_recall", 0.9),
        ]
        result = aggregate_by_rep(attempts)
        assert result["formal"] == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# TestAttemptResult
# ---------------------------------------------------------------------------


class TestAttemptResult:
    def test_instantiation_with_valid_fields(self):
        ar = make_attempt("definition_recall", 0.8)
        assert isinstance(ar, AttemptResult)

    def test_question_field_is_question_object(self):
        ar = make_attempt("intuition_recall", 0.5)
        assert isinstance(ar.question, Question)

    def test_grading_field_is_grading_result(self):
        ar = make_attempt("definition_recall", 0.9)
        assert isinstance(ar.grading, GradingResult)

    def test_learner_response_stored(self):
        ar = make_attempt("definition_recall", 0.5)
        assert ar.learner_response == "my answer"

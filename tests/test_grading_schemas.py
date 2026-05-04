"""Tests for grading/schemas.py, grading/answer_grader.py,
grading/prompt_builder.py, and grading/self_grader.py (MVP3 Step 2)."""
from __future__ import annotations

import pytest

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.prompt_builder import build_grading_prompt
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.grading.self_grader import SelfGrader, self_score_to_grading_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_GRADING = dict(
    accuracy_score=0.8,
    missing_elements=["formal definition"],
    errors=[],
    feedback="Good.",
    mastery_suggestion="partial",
    confidence=0.9,
    needs_human_review=False,
    evidence_alignment="supported",
    raw_response="llm raw",
)


# ---------------------------------------------------------------------------
# TestGradingResult
# ---------------------------------------------------------------------------


class TestGradingResult:
    def test_valid_instantiation(self):
        gr = GradingResult(**SAMPLE_GRADING)
        assert gr.accuracy_score == 0.8

    def test_defaults_applied(self):
        gr = GradingResult(accuracy_score=0.5)
        assert gr.missing_elements == []
        assert gr.errors == []
        assert gr.feedback == ""
        assert gr.mastery_suggestion == "unknown"
        assert gr.confidence == 1.0
        assert gr.needs_human_review is False
        assert gr.evidence_alignment == "supported"
        assert gr.raw_response == ""

    def test_accuracy_score_below_zero_raises(self):
        with pytest.raises(ValueError, match="accuracy_score"):
            GradingResult(accuracy_score=-0.1)

    def test_accuracy_score_above_one_raises(self):
        with pytest.raises(ValueError, match="accuracy_score"):
            GradingResult(accuracy_score=1.1)

    def test_accuracy_score_exactly_zero_ok(self):
        GradingResult(accuracy_score=0.0)

    def test_accuracy_score_exactly_one_ok(self):
        GradingResult(accuracy_score=1.0)

    def test_invalid_mastery_suggestion_raises(self):
        with pytest.raises(ValueError, match="mastery_suggestion"):
            GradingResult(accuracy_score=0.5, mastery_suggestion="excellent")

    def test_invalid_evidence_alignment_raises(self):
        with pytest.raises(ValueError, match="evidence_alignment"):
            GradingResult(accuracy_score=0.5, evidence_alignment="maybe")

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            GradingResult(accuracy_score=0.5, confidence=1.5)

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            GradingResult(accuracy_score=0.5, confidence=-0.1)

    def test_all_mastery_values_valid(self):
        for m in ("unknown", "partial", "solid"):
            GradingResult(accuracy_score=0.5, mastery_suggestion=m)

    def test_all_alignment_values_valid(self):
        for a in ("supported", "partially_supported", "unsupported"):
            GradingResult(accuracy_score=0.5, evidence_alignment=a)


# ---------------------------------------------------------------------------
# TestAnswerGraderABC
# ---------------------------------------------------------------------------


class TestAnswerGraderABC:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            AnswerGrader()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_grade(self):
        class NoGrade(AnswerGrader):
            pass

        with pytest.raises(TypeError):
            NoGrade()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        class StubGrader(AnswerGrader):
            def grade(self, question, expected_answer, evidence_text, learner_response):
                return GradingResult(accuracy_score=1.0)

        grader = StubGrader()
        result = grader.grade("q", "ea", "ev", "lr")
        assert isinstance(result, GradingResult)


# ---------------------------------------------------------------------------
# TestPromptBuilder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_returns_tuple_of_two_strings(self):
        system, user = build_grading_prompt("q", "ea", "ev", "lr")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_prompt_not_empty(self):
        system, _ = build_grading_prompt("q", "ea", "ev", "lr")
        assert len(system) > 50

    def test_user_prompt_contains_question(self):
        _, user = build_grading_prompt("What is compactness?", "ea", "ev", "lr")
        assert "What is compactness?" in user

    def test_user_prompt_contains_expected_answer(self):
        _, user = build_grading_prompt("q", "expected answer text", "ev", "lr")
        assert "expected answer text" in user

    def test_user_prompt_contains_evidence(self):
        _, user = build_grading_prompt("q", "ea", "evidence text here", "lr")
        assert "evidence text here" in user

    def test_user_prompt_contains_learner_response(self):
        _, user = build_grading_prompt("q", "ea", "ev", "learner wrote this")
        assert "learner wrote this" in user

    def test_user_prompt_contains_fixture_key(self):
        # MockLLMClient uses this key to find the fixture
        _, user = build_grading_prompt("q", "ea", "ev", "lr")
        assert "__fixture__:grading/answer_grader" in user


# ---------------------------------------------------------------------------
# TestSelfScoreToGradingResult
# ---------------------------------------------------------------------------


class TestSelfScoreToGradingResult:
    def test_score_0_accuracy_0(self):
        gr = self_score_to_grading_result(0)
        assert gr.accuracy_score == 0.0

    def test_score_1_accuracy_033(self):
        gr = self_score_to_grading_result(1)
        assert gr.accuracy_score == pytest.approx(0.33)

    def test_score_2_accuracy_067(self):
        gr = self_score_to_grading_result(2)
        assert gr.accuracy_score == pytest.approx(0.67)

    def test_score_3_accuracy_1(self):
        gr = self_score_to_grading_result(3)
        assert gr.accuracy_score == 1.0

    def test_invalid_score_raises(self):
        with pytest.raises(ValueError):
            self_score_to_grading_result(4)

    def test_negative_score_raises(self):
        with pytest.raises(ValueError):
            self_score_to_grading_result(-1)

    def test_score_0_mastery_unknown(self):
        gr = self_score_to_grading_result(0)
        assert gr.mastery_suggestion == "unknown"

    def test_score_2_mastery_partial(self):
        gr = self_score_to_grading_result(2)
        assert gr.mastery_suggestion == "partial"

    def test_score_3_mastery_solid(self):
        gr = self_score_to_grading_result(3)
        assert gr.mastery_suggestion == "solid"

    def test_raw_response_includes_score(self):
        gr = self_score_to_grading_result(2)
        assert "2" in gr.raw_response

    def test_needs_human_review_false(self):
        gr = self_score_to_grading_result(1)
        assert gr.needs_human_review is False

    def test_confidence_is_one(self):
        gr = self_score_to_grading_result(3)
        assert gr.confidence == 1.0


# ---------------------------------------------------------------------------
# TestSelfGrader
# ---------------------------------------------------------------------------


class TestSelfGrader:
    def test_default_score_skips_prompt(self):
        grader = SelfGrader(default_score=2)
        result = grader.grade("q", "ea", "ev", "lr")
        assert isinstance(result, GradingResult)
        assert result.accuracy_score == pytest.approx(0.67)

    def test_invalid_default_score_raises_at_init(self):
        with pytest.raises(ValueError):
            SelfGrader(default_score=5)

    def test_interactive_prompt(self, monkeypatch):
        inputs = iter(["2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        grader = SelfGrader()
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.accuracy_score == pytest.approx(0.67)

    def test_interactive_invalid_then_valid(self, monkeypatch):
        inputs = iter(["abc", "5", "3"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        grader = SelfGrader()
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.accuracy_score == 1.0

    def test_eof_returns_score_zero(self, monkeypatch):
        def raise_eof(_):
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        grader = SelfGrader()
        result = grader.grade("q", "ea", "ev", "lr")
        assert result.accuracy_score == 0.0

    def test_is_answer_grader_subclass(self):
        assert issubclass(SelfGrader, AnswerGrader)

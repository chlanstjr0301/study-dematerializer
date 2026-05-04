"""Tests for study_loop/white_recall.py (MVP3 Step 4)."""
from __future__ import annotations

import pytest

from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Evidence, Question
from gonghaebun.study_loop.mastery import AttemptResult
from gonghaebun.study_loop.white_recall import run_white_recall_batch, run_white_recall_session

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

_LONG_TEXT = "A compact set is one where every open cover has a finite subcover."


def make_question(question_id: str = "q_doc_b000001_R01") -> Question:
    return Question(
        question_id=question_id,
        document_id="doc",
        source_block_id="doc_b000001",
        question_type="definition_recall",
        difficulty="medium",
        question="State the definition of compactness.",
        expected_answer=_LONG_TEXT,
        evidence=_EVIDENCE,
        rule_id="R01_definition_recall",
    )


def make_grading(accuracy: float = 0.75) -> GradingResult:
    from gonghaebun.study_md.writer import compute_mastery_state
    return GradingResult(
        accuracy_score=accuracy,
        mastery_suggestion=compute_mastery_state(accuracy),
    )


class StubGrader:
    """Always returns a fixed GradingResult."""

    def __init__(self, accuracy: float = 0.75):
        self._accuracy = accuracy

    def grade(self, question, expected_answer, evidence_text, learner_response):
        return make_grading(self._accuracy)


# ---------------------------------------------------------------------------
# TestRunWhiteRecallBatch
# ---------------------------------------------------------------------------


class TestRunWhiteRecallBatch:
    def test_returns_list_of_attempt_results(self):
        q = make_question()
        gr = make_grading()
        results = run_white_recall_batch([q], [("my answer", gr)])
        assert all(isinstance(r, AttemptResult) for r in results)

    def test_pairs_questions_with_responses(self):
        q1 = make_question("q1")
        q2 = make_question("q2")
        gr1 = make_grading(0.5)
        gr2 = make_grading(1.0)
        results = run_white_recall_batch([q1, q2], [("ans1", gr1), ("ans2", gr2)])
        assert results[0].question.question_id == "q1"
        assert results[0].learner_response == "ans1"
        assert results[1].question.question_id == "q2"
        assert results[1].learner_response == "ans2"

    def test_mismatched_lengths_raises_value_error(self):
        q = make_question()
        gr = make_grading()
        with pytest.raises(ValueError, match="same length"):
            run_white_recall_batch([q, q], [("ans", gr)])

    def test_empty_lists_returns_empty(self):
        result = run_white_recall_batch([], [])
        assert result == []

    def test_grading_stored_in_attempt(self):
        q = make_question()
        gr = make_grading(0.9)
        results = run_white_recall_batch([q], [("answer", gr)])
        assert results[0].grading.accuracy_score == 0.9


# ---------------------------------------------------------------------------
# TestRunWhiteRecallSessionNoInteractive
# ---------------------------------------------------------------------------


class TestRunWhiteRecallSessionNoInteractive:
    def test_no_interactive_returns_attempt_per_question(self):
        questions = [make_question("q1"), make_question("q2")]
        grader = StubGrader()
        results = run_white_recall_session(
            questions, grader, no_interactive=True
        )
        assert len(results) == 2

    def test_no_interactive_uses_default_answer(self):
        questions = [make_question()]
        grader = StubGrader()
        results = run_white_recall_session(
            questions, grader, no_interactive=True, default_answer="my default"
        )
        assert results[0].learner_response == "my default"

    def test_no_interactive_empty_default_answer(self):
        questions = [make_question()]
        grader = StubGrader()
        results = run_white_recall_session(
            questions, grader, no_interactive=True
        )
        assert results[0].learner_response == ""

    def test_grader_called_for_each_question(self):
        from unittest.mock import MagicMock

        questions = [make_question("q1"), make_question("q2"), make_question("q3")]
        grader = MagicMock()
        grader.grade.return_value = make_grading()
        run_white_recall_session(questions, grader, no_interactive=True)
        assert grader.grade.call_count == 3

    def test_empty_question_list_returns_empty(self):
        results = run_white_recall_session([], StubGrader(), no_interactive=True)
        assert results == []


# ---------------------------------------------------------------------------
# TestRunWhiteRecallSessionInteractive
# ---------------------------------------------------------------------------


class TestRunWhiteRecallSessionInteractive:
    def test_interactive_collects_answer_and_grades(self, monkeypatch):
        inputs = iter(["my answer", ""])  # answer + blank line to finish
        monkeypatch.setattr("builtins.input", lambda: next(inputs))

        questions = [make_question()]
        grader = StubGrader()
        results = run_white_recall_session(questions, grader)
        assert len(results) == 1
        assert results[0].learner_response == "my answer"

    def test_interactive_multiline_answer(self, monkeypatch):
        inputs = iter(["line one", "line two", ""])
        monkeypatch.setattr("builtins.input", lambda: next(inputs))

        questions = [make_question()]
        grader = StubGrader()
        results = run_white_recall_session(questions, grader)
        assert "line one" in results[0].learner_response
        assert "line two" in results[0].learner_response

    def test_eof_during_answer_returns_partial(self, monkeypatch):
        call_count = [0]

        def raise_eof():
            call_count[0] += 1
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        questions = [make_question("q1"), make_question("q2")]
        grader = StubGrader()
        results = run_white_recall_session(questions, grader)
        # Should return partial (0 results since first input raises EOF)
        assert len(results) == 0

    def test_interactive_grader_receives_correct_args(self, monkeypatch):
        from unittest.mock import MagicMock

        inputs = iter(["learner wrote this", ""])
        monkeypatch.setattr("builtins.input", lambda: next(inputs))

        question = make_question()
        mock_grader = MagicMock()
        mock_grader.grade.return_value = make_grading()

        run_white_recall_session([question], mock_grader)

        call_kwargs = mock_grader.grade.call_args.kwargs
        assert call_kwargs["question"] == question.question
        assert call_kwargs["learner_response"] == "learner wrote this"
        assert call_kwargs["evidence_text"] == question.evidence.source_text

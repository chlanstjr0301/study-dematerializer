"""
Tests for Batch C: Korean feedback structure and prompt requirements.

Verifies:
1. LLM grading prompt requires Korean feedback structure.
2. Self-explanation evaluator prompt requires Korean sections.
3. Deterministic evaluator produces Korean structured feedback.
4. Invalid/gibberish feedback remains Korean.
5. Grading response schemas remain compatible.
"""
from __future__ import annotations

import pytest


class TestAnswerGraderPromptKorean:
    """LLM answer grader prompt must instruct Korean structured feedback."""

    def test_prompt_file_contains_korean_instruction(self):
        """Read prompt file directly (avoids stale site-packages)."""
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src" / "gonghaebun" / "prompts" / "answer_grader.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "Korean" in prompt

    def test_prompt_file_requires_korean_feedback_sections(self):
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src" / "gonghaebun" / "prompts" / "answer_grader.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "잘한 부분" in prompt
        assert "빠진 부분" in prompt
        assert "고쳐 쓰면 좋은 답안" in prompt
        assert "다음 확인 질문" in prompt

    def test_prompt_file_requires_korean_in_output_fields(self):
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src" / "gonghaebun" / "prompts" / "answer_grader.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "string in Korean" in prompt or "Korean string" in prompt


class TestSelfExplanationPromptKorean:
    """Self-explanation evaluator prompt must require Korean output."""

    def test_prompt_file_requires_korean(self):
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src" / "gonghaebun" / "prompts" / "stage5_self_explanation_evaluator.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "Korean" in prompt

    def test_prompt_file_has_feedback_sections(self):
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src" / "gonghaebun" / "prompts" / "stage5_self_explanation_evaluator.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "잘한 부분" in prompt
        assert "빠진 부분" in prompt
        assert "고쳐 쓰면 좋은 답안" in prompt
        assert "다음 확인 질문" in prompt


class TestDeterministicFeedbackFunctionKorean:
    """_generate_feedback (local source) must produce Korean structured output."""

    @pytest.fixture(autouse=True)
    def _load_local_module(self):
        """Import _generate_feedback from local source, not stale site-packages."""
        import importlib.util
        from pathlib import Path

        src = Path(__file__).parent.parent / "src" / "gonghaebun" / "grading" / "deterministic_evaluator.py"
        spec = importlib.util.spec_from_file_location("local_det_eval", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self._generate_feedback = mod._generate_feedback

    def test_passing_feedback_is_korean(self):
        feedback = self._generate_feedback(passed=True, missing_terms=[], misconception_ids=[])
        assert "잘한 부분" in feedback

    def test_failing_feedback_is_korean_structured(self):
        feedback = self._generate_feedback(
            passed=False,
            missing_terms=["open cover", "finite subcover"],
            misconception_ids=[],
        )
        assert "잘한 부분" in feedback
        assert "빠진 부분" in feedback
        assert "다음 확인 질문" in feedback

    def test_feedback_contains_missing_terms_in_korean(self):
        feedback = self._generate_feedback(
            passed=False,
            missing_terms=["open cover", "finite subcover"],
            misconception_ids=[],
        )
        assert "누락" in feedback

    def test_misconception_feedback_is_korean(self):
        feedback = self._generate_feedback(
            passed=False,
            missing_terms=[],
            misconception_ids=["closed_bounded_always"],
        )
        assert "오개념" in feedback

    def test_no_missing_no_misconceptions_still_korean(self):
        feedback = self._generate_feedback(
            passed=False,
            missing_terms=[],
            misconception_ids=[],
        )
        assert "잘한 부분" in feedback


class TestGibberishFeedbackRemainsKorean:
    """Batch A gibberish guard must still produce Korean feedback."""

    def test_invalid_answer_feedback_is_korean(self):
        from apps.api.services.study_session_service import _INVALID_ANSWER_FEEDBACK

        assert "답변" in _INVALID_ANSWER_FEEDBACK
        assert "수학적" in _INVALID_ANSWER_FEEDBACK


class TestGradingSchemaCompatibility:
    """Grading schemas must remain backward-compatible."""

    def test_grading_result_schema_unchanged(self):
        from gonghaebun.grading.schemas import GradingResult

        # Must still have these fields
        r = GradingResult(
            accuracy_score=0.8,
            needs_human_review=False,
            feedback="test",
            mastery_suggestion="solid",
            raw_response="{}",
        )
        assert r.accuracy_score == 0.8
        assert r.feedback == "test"

    def test_evaluation_output_schema_unchanged(self):
        from gonghaebun.models.evaluation_output import EvaluationOutput

        e = EvaluationOutput(
            score=0.7,
            mastery="partial",
            passed=True,
            missing_elements=["term1"],
            incorrect_claims=[],
            misconception_tags=[],
            mapping_failures=[],
            needs_human_review=False,
            feedback="Korean feedback here",
            next_recall_trigger="",
        )
        assert e.score == 0.7
        assert e.feedback == "Korean feedback here"

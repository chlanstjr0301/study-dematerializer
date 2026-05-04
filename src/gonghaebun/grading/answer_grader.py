"""
AnswerGrader — abstract base class for all grading backends.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from gonghaebun.grading.schemas import GradingResult


class AnswerGrader(ABC):
    """
    Interface for grading a learner's free-text response to a question.

    All graders must implement grade().
    """

    @abstractmethod
    def grade(
        self,
        question: str,
        expected_answer: str,
        evidence_text: str,
        learner_response: str,
    ) -> GradingResult:
        """
        Evaluate the learner_response and return a GradingResult.

        Parameters
        ----------
        question        : the question that was posed to the learner
        expected_answer : source-grounded reference answer (from SourceBlock.text)
        evidence_text   : raw source text the question was derived from
        learner_response: the learner's free-text answer
        """

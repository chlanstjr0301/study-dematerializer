"""
LLMGrader — grades learner answers via an LLMClient.

Builds a structured prompt, calls llm.complete(), parses the JSON response,
and retries once on malformed output before raising LLMResponseError.
The raw LLM response is stored verbatim in GradingResult.raw_response.
"""
from __future__ import annotations

import json

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.prompt_builder import build_grading_prompt
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMResponseError


class LLMGrader(AnswerGrader):
    """
    Grader backed by any LLMClient (including MockLLMClient for tests).

    Retries once if the initial LLM response cannot be parsed as valid JSON
    or if the resulting GradingResult fails validation. On second failure,
    raises LLMResponseError.

    Parameters
    ----------
    llm : LLMClient
        Any implementation of LLMClient (MockLLMClient, OpenAIClient, …).
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def grade(
        self,
        question: str,
        expected_answer: str,
        evidence_text: str,
        learner_response: str,
    ) -> GradingResult:
        """
        Grade the learner_response and return a GradingResult.

        Attempts up to 2 LLM calls. Raises LLMResponseError if both fail.
        """
        system, user = build_grading_prompt(
            question=question,
            expected_answer=expected_answer,
            evidence_text=evidence_text,
            learner_response=learner_response,
        )

        last_error: Exception | None = None
        last_raw: str = ""

        for attempt in range(2):
            try:
                raw = self._llm.complete(system, user)
                last_raw = raw
                data = json.loads(raw)
                data.pop("raw_response", None)  # override with actual LLM output
                result = GradingResult(raw_response=raw, **data)
                return result
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                last_error = exc
                # Continue to retry on attempt 0; raise on attempt 1
                if attempt == 1:
                    raise LLMResponseError(
                        f"LLM returned unparseable grading response after 2 attempts. "
                        f"Last raw response: {last_raw!r}"
                    ) from last_error

        # Unreachable, but satisfies type checkers
        raise LLMResponseError("LLMGrader: unexpected exit from retry loop")

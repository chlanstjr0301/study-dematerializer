"""
LLMGrader — grades learner answers via an LLMClient.

Uses provider-level structured output (complete_structured) for schema
enforcement, with a local validate_llm_output() as a second safety layer.
Falls back gracefully (needs_human_review=True) instead of raising on failure.

Tracing: one LLMTraceRecord is appended to self.traces per question graded
(up to 2 LLMAttemptRecords per question when a retry occurs).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.llm_output_schema import (
    LLM_GRADING_OUTPUT_SCHEMA,
    llm_output_to_grading_result,
    validate_llm_output,
)
from gonghaebun.grading.prompt_builder import build_grading_prompt
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.grading.trace_models import LLMAttemptRecord, LLMTraceRecord
from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMError

_FALLBACK_RESULT = GradingResult(
    accuracy_score=0.0,
    needs_human_review=True,
    feedback="LLM grading failed; human review required.",
    mastery_suggestion="unknown",
    raw_response="",
)


class LLMGrader(AnswerGrader):
    """
    Grader backed by any LLMClient (including MockLLMClient for tests).

    Uses complete_structured() for provider-level JSON schema enforcement.
    Retries once if the response fails local schema validation.
    Falls back to a human-review result on provider error, timeout, or
    second validation failure — never raises to the caller.

    Parameters
    ----------
    llm        : Any LLMClient (MockLLMClient, OpenAIClient, …).
    max_calls  : Hard cap on total LLM API calls across the session.
                 Questions beyond the cap receive the fallback result.
    timeout    : Per-call timeout in seconds.
    """

    def __init__(
        self,
        llm: LLMClient,
        max_calls: int = 20,
        timeout: float = 30.0,
    ) -> None:
        self._llm = llm
        self._max_calls = max_calls
        self._timeout = timeout
        self._call_count: int = 0
        self._concept_id: str = ""
        self._representation_type: str = ""
        self._current_question_id: str = ""
        self.traces: list[LLMTraceRecord] = []

    def _set_context(
        self,
        concept_id: str,
        representation_type: str,
        question_id: str = "",
    ) -> None:
        """Set per-question context for prompt enrichment and trace attribution."""
        self._concept_id = concept_id
        self._representation_type = representation_type
        self._current_question_id = question_id

    def grade(
        self,
        question: str,
        expected_answer: str,
        evidence_text: str,
        learner_response: str,
    ) -> GradingResult:
        """
        Grade the learner_response and return a GradingResult.

        Falls back to needs_human_review=True if:
        - max_calls is already exhausted
        - the LLM provider raises an error or times out
        - both validation attempts fail

        A LLMTraceRecord is appended to self.traces for every question
        that reaches the LLM (not for immediate max_calls fallbacks).
        """
        if self._call_count >= self._max_calls:
            return GradingResult(
                accuracy_score=0.0,
                needs_human_review=True,
                feedback="LLM grading skipped; call limit reached.",
                mastery_suggestion="unknown",
                raw_response="",
            )

        system, user = build_grading_prompt(
            question=question,
            expected_answer=expected_answer,
            evidence_text=evidence_text,
            learner_response=learner_response,
            concept_id=self._concept_id,
            representation_type=self._representation_type,
        )

        prompt_hash = (
            "sha256:"
            + hashlib.sha256((system + user).encode("utf-8")).hexdigest()
        )

        attempt_records: list[LLMAttemptRecord] = []
        result: GradingResult | None = None

        for call_index in range(2):
            if self._call_count >= self._max_calls:
                attempt_records.append(LLMAttemptRecord(
                    call_index=call_index,
                    prompt_hash=prompt_hash,
                    parsed_ok=False,
                    fallback=True,
                    duration_ms=None,
                    structured_output_used=True,
                    llm_output=None,
                    error_message="max_calls limit reached mid-retry",
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                result = GradingResult(
                    accuracy_score=0.0,
                    needs_human_review=True,
                    feedback="LLM grading failed; human review required.",
                    mastery_suggestion="unknown",
                    raw_response="",
                )
                break

            t0 = time.monotonic()
            data: dict | None = None
            error_message: str | None = None
            provider_failed = False

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._llm.complete_structured,
                        system,
                        user,
                        LLM_GRADING_OUTPUT_SCHEMA,
                    )
                    data = future.result(timeout=self._timeout)
                self._call_count += 1
                duration_ms = (time.monotonic() - t0) * 1000
            except FuturesTimeoutError:
                self._call_count += 1
                duration_ms = (time.monotonic() - t0) * 1000
                error_message = "TimeoutError: LLM call exceeded timeout"
                provider_failed = True
            except LLMError as exc:
                self._call_count += 1
                duration_ms = (time.monotonic() - t0) * 1000
                error_message = str(exc)
                provider_failed = True
            except Exception as exc:  # catch-all for unexpected provider errors
                self._call_count += 1
                duration_ms = (time.monotonic() - t0) * 1000
                error_message = f"{type(exc).__name__}: {exc}"
                provider_failed = True

            if provider_failed:
                attempt_records.append(LLMAttemptRecord(
                    call_index=call_index,
                    prompt_hash=prompt_hash,
                    parsed_ok=False,
                    fallback=True,
                    duration_ms=duration_ms,
                    structured_output_used=True,
                    llm_output=None,
                    error_message=error_message,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                result = GradingResult(
                    accuracy_score=0.0,
                    needs_human_review=True,
                    feedback="LLM grading failed; human review required.",
                    mastery_suggestion="unknown",
                    raw_response="",
                )
                break

            # Local validation (second safety layer after provider schema enforcement)
            try:
                assert data is not None
                out = validate_llm_output(data)
                raw_response = json.dumps(data)
                attempt_records.append(LLMAttemptRecord(
                    call_index=call_index,
                    prompt_hash=prompt_hash,
                    parsed_ok=True,
                    fallback=False,
                    duration_ms=duration_ms,
                    structured_output_used=True,
                    llm_output=dataclasses.asdict(out),
                    error_message=None,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                result = llm_output_to_grading_result(out, raw_response)
                break
            except (ValueError, AssertionError) as exc:
                is_final = call_index == 1
                attempt_records.append(LLMAttemptRecord(
                    call_index=call_index,
                    prompt_hash=prompt_hash,
                    parsed_ok=False,
                    fallback=is_final,
                    duration_ms=duration_ms,
                    structured_output_used=True,
                    llm_output=None,
                    error_message=str(exc),
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))
                if is_final:
                    result = GradingResult(
                        accuracy_score=0.0,
                        needs_human_review=True,
                        feedback="LLM grading failed; human review required.",
                        mastery_suggestion="unknown",
                        raw_response="",
                    )
                # else: continue to retry (loop increments call_index)

        self.traces.append(LLMTraceRecord(
            question_id=self._current_question_id,
            concept_id=self._concept_id,
            representation_type=self._representation_type,
            model=getattr(self._llm, "_model", "mock"),
            attempts=attempt_records,
        ))

        assert result is not None
        return result

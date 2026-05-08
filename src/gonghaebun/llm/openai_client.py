"""
OpenAI provider adapter.

Uses the OpenAI Responses API (responses.create / response.output_text)
as the primary completion path.

Requires: pip install openai
Requires: OPENAI_API_KEY environment variable (or explicit api_key argument).
"""
from __future__ import annotations

import json
import logging
import os
import time

from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMAPIKeyError, LLMError, LLMResponseError
from gonghaebun.llm.prompt_utils import strip_fixture_marker

logger = logging.getLogger("gonghaebun.llm.openai")

_RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)
_MAX_RETRIES = 2
_BACKOFF_SECONDS = (1, 3)


class OpenAIClient(LLMClient):
    """
    LLMClient backed by the OpenAI Responses API.

    Args:
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model:   Model ID (default: "gpt-5.5").
        timeout: Per-call timeout in seconds. Falls back to
                 GONGHAEBUN_LLM_TIMEOUT_SECONDS env var (default: 30).

    Raises:
        LLMAPIKeyError: if api_key is None or empty after env-var lookup.
        ImportError:    if the `openai` package is not installed.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5.5",
        timeout: float | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise LLMAPIKeyError(
                "OPENAI_API_KEY is required. "
                "Pass api_key= or set the OPENAI_API_KEY environment variable."
            )

        try:
            import openai  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "The 'openai' package is required for OpenAIClient. "
                "Install it with: pip install openai"
            ) from exc

        self._model = model
        self._api_key = resolved_key
        self._timeout = timeout or float(
            os.getenv("GONGHAEBUN_LLM_TIMEOUT_SECONDS", "30")
        )
        self._client = openai.OpenAI(
            api_key=resolved_key,
            timeout=self._timeout,
            max_retries=0,  # We handle retries in _call_with_retry()
        )

    def complete(self, system: str, user: str) -> str:
        """
        Return a plain-text completion using the OpenAI Responses API.

        Strips __fixture__ markers before sending to API.
        Retries on transient errors (429/5xx) up to 2 times with backoff.
        """
        clean_user = strip_fixture_marker(user)
        return self._call_with_retry(
            lambda: self._do_complete(system, clean_user),
            method_name="complete",
        )

    def complete_json(self, system: str, user: str) -> dict:
        """
        Return a parsed JSON dict from the LLM response.

        Raises:
            LLMResponseError: if the response cannot be parsed as JSON.
            LLMError:         if the OpenAI API returns an error.
        """
        raw = self.complete(system, user)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"OpenAI response is not valid JSON: {raw!r}"
            ) from exc

    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict:
        """
        Call the OpenAI Responses API with provider-level JSON schema enforcement.

        Strips __fixture__ markers before sending to API.
        Retries on transient errors (429/5xx) up to 2 times with backoff.

        Fallback chain:
        1. Structured output (json_schema enforcement)
        2. Plain JSON instruction (if structured fails with non-retryable error)
        """
        clean_user = strip_fixture_marker(user)
        schema_name = json_schema.get("title", "structured_output")

        logger.info(
            "complete_structured_enter model=%s schema_name=%s user_len=%d",
            self._model, schema_name, len(clean_user),
        )

        def _call_structured():
            import openai  # noqa: PLC0415
            try:
                response = self._client.responses.create(
                    model=self._model,
                    instructions=system,
                    input=clean_user,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "grading_output",
                            "schema": json_schema,
                            "strict": True,
                        }
                    },
                )
                return response.output_text
            except openai.APIError as exc:
                logger.warning(
                    "complete_structured_api_error model=%s status=%s type=%s",
                    self._model,
                    getattr(exc, "status_code", "unknown"),
                    type(exc).__name__,
                )
                raise LLMError(f"OpenAI API error: {exc}") from exc

        # --- Attempt 1: strict structured output ---
        try:
            raw = self._call_with_retry(_call_structured, method_name="complete_structured")
            parsed = json.loads(raw)
            logger.info("complete_structured_ok model=%s method=structured", self._model)
            return parsed
        except (LLMError, json.JSONDecodeError) as structured_exc:
            logger.warning(
                "complete_structured_failed model=%s error_class=%s error=%s",
                self._model, type(structured_exc).__name__, str(structured_exc)[:200],
            )

        # --- Attempt 2: plain JSON instruction fallback ---
        logger.warning(
            "complete_structured_plain_json_fallback model=%s", self._model,
        )
        try:
            json_instruction = (
                system
                + "\n\nIMPORTANT: Respond ONLY with a valid JSON object. "
                "No markdown, no code fences, no extra text."
            )
            raw_plain = self._call_with_retry(
                lambda: self._do_complete(json_instruction, clean_user),
                method_name="complete_structured_plain_fallback",
            )
            # Strip markdown code fences if present
            text = raw_plain.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]  # remove first line
                if text.endswith("```"):
                    text = text[:-3].strip()
            parsed = json.loads(text)
            logger.warning(
                "complete_structured_plain_json_ok model=%s", self._model,
            )
            return parsed
        except (LLMError, json.JSONDecodeError, ValueError) as plain_exc:
            logger.warning(
                "complete_structured_plain_json_failed model=%s error_class=%s error=%s",
                self._model, type(plain_exc).__name__, str(plain_exc)[:200],
            )
            # Re-raise the original structured error for caller to handle
            raise LLMResponseError(
                f"Both structured and plain JSON calls failed. "
                f"Structured: {structured_exc!r}; Plain: {plain_exc!r}"
            ) from plain_exc

    # --- Private helpers ---

    def _do_complete(self, system: str, user: str) -> str:
        import openai  # noqa: PLC0415
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=system,
                input=user,
            )
            return response.output_text
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

    def _call_with_retry(self, fn, *, method_name: str = "complete"):
        """Retry fn() on transient LLMError up to _MAX_RETRIES times."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            t0 = time.monotonic()
            try:
                result = fn()
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "llm_call_ok model=%s method=%s attempt=%d elapsed_ms=%.0f",
                    self._model, method_name, attempt + 1, elapsed_ms,
                )
                return result
            except LLMError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.warning(
                    "llm_call_fail model=%s method=%s attempt=%d elapsed_ms=%.0f error_class=%s",
                    self._model, method_name, attempt + 1, elapsed_ms,
                    type(exc).__name__,
                )
                last_exc = exc
                if attempt < _MAX_RETRIES and self._is_retryable(exc):
                    logger.info(
                        "llm_retry backoff_s=%s", _BACKOFF_SECONDS[attempt]
                    )
                    time.sleep(_BACKOFF_SECONDS[attempt])
                    continue
                raise
        raise last_exc  # pragma: no cover — unreachable

    @staticmethod
    def _is_retryable(exc: LLMError) -> bool:
        """Check if the underlying error is retryable based on exception type."""
        cause = exc.__cause__
        if cause is None:
            # Fall back to string matching for backwards compatibility
            msg = str(exc)
            return any(str(code) in msg for code in _RETRYABLE_STATUS_CODES)
        try:
            import openai as _openai  # noqa: PLC0415

            # Guard against fake/minimal openai modules in tests
            timeout_cls = getattr(_openai, "APITimeoutError", None)
            if timeout_cls and isinstance(cause, timeout_cls):
                return False  # Timeout: don't retry (already waited full timeout)
            rate_cls = getattr(_openai, "RateLimitError", None)
            if rate_cls and isinstance(cause, rate_cls):
                return True
            server_cls = getattr(_openai, "InternalServerError", None)
            if server_cls and isinstance(cause, server_cls):
                return True
            conn_cls = getattr(_openai, "APIConnectionError", None)
            if conn_cls and isinstance(cause, conn_cls):
                return True
        except ImportError:
            pass
        # Unknown cause type: fall back to string matching
        msg = str(exc)
        return any(str(code) in msg for code in _RETRYABLE_STATUS_CODES)

"""
OpenAI provider adapter.

Uses the OpenAI Responses API (responses.create / response.output_text)
as the primary completion path.

Requires: pip install openai
Requires: OPENAI_API_KEY environment variable (or explicit api_key argument).
"""
from __future__ import annotations

import json
import os

from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMAPIKeyError, LLMError, LLMResponseError


class OpenAIClient(LLMClient):
    """
    LLMClient backed by the OpenAI Responses API.

    Args:
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model:   Model ID (default: "gpt-4o-mini").

    Raises:
        LLMAPIKeyError: if api_key is None or empty after env-var lookup.
        ImportError:    if the `openai` package is not installed.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
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
        self._client = openai.OpenAI(api_key=resolved_key)

    def complete(self, system: str, user: str) -> str:
        """
        Return a plain-text completion using the OpenAI Responses API.

        Raises:
            LLMError: if the OpenAI API returns an error.
        """
        try:
            import openai  # noqa: PLC0415
            response = self._client.responses.create(
                model=self._model,
                instructions=system,
                input=user,
            )
            return response.output_text
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

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

        Uses the text.format json_schema option to guarantee the response
        matches the provided schema. Returns the parsed dict.

        Raises:
            LLMResponseError: if the response cannot be parsed as JSON
                              (should not occur with schema enforcement, but
                              included as a safety net).
            LLMError:         if the OpenAI API returns an error.
        """
        try:
            import openai  # noqa: PLC0415
            response = self._client.responses.create(
                model=self._model,
                instructions=system,
                input=user,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "grading_output",
                        "schema": json_schema,
                        "strict": True,
                    }
                },
            )
            raw = response.output_text
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"OpenAI structured response is not valid JSON: {raw!r}"
            ) from exc

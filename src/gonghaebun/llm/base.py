"""
Abstract LLM client interface.

MVP 1 ships MockLLMClient only.
TODO: Add real providers here (e.g. AnthropicClient, OpenAIClient)
      once MVP 1 is validated. Each provider must implement complete()
      and complete_json().
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Base interface for all LLM backends."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return a plain-text completion."""

    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict:
        """Return a parsed JSON dict. Raises ValueError on parse failure."""

    @abstractmethod
    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict:
        """
        Call the LLM with provider-level JSON schema enforcement.

        Returns the parsed dict guaranteed to match json_schema.
        Raises LLMResponseError if the response cannot be parsed as JSON.
        Raises LLMError on provider-level failures.
        """

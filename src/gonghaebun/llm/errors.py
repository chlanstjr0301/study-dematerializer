"""
LLM-specific exception hierarchy.

LLMError
  ├── LLMAPIKeyError   — missing or empty API key
  └── LLMResponseError — malformed / unparseable response from the LLM
"""
from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM-related errors."""


class LLMAPIKeyError(LLMError):
    """Raised when a required API key is missing or empty."""


class LLMResponseError(LLMError):
    """Raised when the LLM returns a response that cannot be parsed."""

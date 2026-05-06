"""
LLM client factory.

Environment-variable-driven provider selection:
  GONGHAEBUN_LLM_DISABLED=1 (default) → always MockLLMClient
  GONGHAEBUN_LLM_PROVIDER=mock|openai  → selects implementation
  GONGHAEBUN_LLM_MODEL=gpt-5.5         → model for openai provider
  OPENAI_API_KEY                        → required when provider=openai

Silent fallback is forbidden: missing API key raises LLMAPIKeyError.
"""
from __future__ import annotations

import os

from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMAPIKeyError

DEFAULT_MODEL = "gpt-5.5"


def get_llm_client(
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> LLMClient:
    """
    Environment-variable-based LLM client factory.

    Safety: LLM_DISABLED=1 → always MockLLMClient (absolute override).
    provider=openai + key missing → LLMAPIKeyError (no silent fallback).
    """
    from gonghaebun.llm.mock import MockLLMClient

    # Safety override: disabled → unconditionally mock
    disabled = os.getenv("GONGHAEBUN_LLM_DISABLED", "1") == "1"
    if disabled:
        return MockLLMClient()

    resolved_provider = provider or os.getenv("GONGHAEBUN_LLM_PROVIDER", "mock")

    if resolved_provider == "mock":
        return MockLLMClient()

    if resolved_provider == "openai":
        from gonghaebun.llm.openai_client import OpenAIClient

        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise LLMAPIKeyError(
                "GONGHAEBUN_LLM_PROVIDER=openai이지만 OPENAI_API_KEY가 설정되지 않았습니다. "
                "OPENAI_API_KEY 환경변수를 설정하거나, GONGHAEBUN_LLM_PROVIDER=mock으로 변경하세요."
            )
        resolved_model = model or os.getenv("GONGHAEBUN_LLM_MODEL", DEFAULT_MODEL)
        return OpenAIClient(api_key=resolved_key, model=resolved_model)

    raise ValueError(
        f"알 수 없는 LLM provider: {resolved_provider}. 'mock' 또는 'openai'만 지원합니다."
    )

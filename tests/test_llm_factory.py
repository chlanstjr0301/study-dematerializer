"""Tests for the LLM client factory (MVP6-0A)."""
from __future__ import annotations

import pytest

from gonghaebun.llm.factory import DEFAULT_MODEL, get_llm_client
from gonghaebun.llm.prompt_utils import strip_fixture_marker
from gonghaebun.llm.errors import LLMAPIKeyError
from gonghaebun.llm.mock import MockLLMClient


# ---------------------------------------------------------------------------
# strip_fixture_marker
# ---------------------------------------------------------------------------


class TestStripFixtureMarker:
    def test_removes_marker_at_end(self):
        text = "some prompt text\n\n__fixture__:compactness/self_explanation_eval"
        result = strip_fixture_marker(text)
        assert result == "some prompt text"
        assert "__fixture__" not in result

    def test_removes_marker_with_trailing_whitespace(self):
        text = "prompt  __fixture__:x/y  "
        result = strip_fixture_marker(text)
        assert "__fixture__" not in result

    def test_no_op_without_marker(self):
        text = "clean prompt text"
        assert strip_fixture_marker(text) == text

    def test_no_op_empty_string(self):
        assert strip_fixture_marker("") == ""

    def test_preserves_fixture_in_middle(self):
        # Only strips at end of string
        text = "__fixture__:x/y\nsome more text"
        assert strip_fixture_marker(text) == text


# ---------------------------------------------------------------------------
# get_llm_client — disabled mode
# ---------------------------------------------------------------------------


class TestFactoryDisabled:
    def test_disabled_always_returns_mock(self, monkeypatch):
        """LLM_DISABLED=1 → MockLLMClient regardless of provider."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        client = get_llm_client()
        assert isinstance(client, MockLLMClient)

    def test_disabled_default_returns_mock(self, monkeypatch):
        """Default (no env set) → LLM_DISABLED=1 → MockLLMClient."""
        monkeypatch.delenv("GONGHAEBUN_LLM_DISABLED", raising=False)
        monkeypatch.delenv("GONGHAEBUN_LLM_PROVIDER", raising=False)
        client = get_llm_client()
        assert isinstance(client, MockLLMClient)


# ---------------------------------------------------------------------------
# get_llm_client — mock provider
# ---------------------------------------------------------------------------


class TestFactoryMock:
    def test_provider_mock_returns_mock(self, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "mock")
        client = get_llm_client()
        assert isinstance(client, MockLLMClient)

    def test_default_provider_is_mock(self, monkeypatch):
        """LLM_DISABLED=0, provider unset → defaults to 'mock'."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.delenv("GONGHAEBUN_LLM_PROVIDER", raising=False)
        client = get_llm_client()
        assert isinstance(client, MockLLMClient)


# ---------------------------------------------------------------------------
# get_llm_client — openai provider
# ---------------------------------------------------------------------------


class TestFactoryOpenAI:
    def test_provider_openai_with_key(self, monkeypatch):
        """provider=openai + key → OpenAIClient instance created."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
        monkeypatch.setenv("GONGHAEBUN_LLM_MODEL", "gpt-5.5")

        # Mock the openai module to avoid needing it installed
        import sys
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "openai", mock_openai)

        from gonghaebun.llm.openai_client import OpenAIClient
        client = get_llm_client()
        assert isinstance(client, OpenAIClient)
        assert client._model == "gpt-5.5"
        assert client._api_key == "sk-test-key-123"

    def test_provider_openai_no_key_raises(self, monkeypatch):
        """provider=openai + no key → LLMAPIKeyError (no silent fallback)."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(LLMAPIKeyError, match="OPENAI_API_KEY"):
            get_llm_client()

    def test_model_from_env(self, monkeypatch):
        """GONGHAEBUN_LLM_MODEL is passed to OpenAIClient."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xyz")
        monkeypatch.setenv("GONGHAEBUN_LLM_MODEL", "gpt-5.5")

        import sys
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "openai", mock_openai)

        client = get_llm_client()
        assert client._model == "gpt-5.5"

    def test_model_default(self, monkeypatch):
        """Without GONGHAEBUN_LLM_MODEL → uses DEFAULT_MODEL."""
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xyz")
        monkeypatch.delenv("GONGHAEBUN_LLM_MODEL", raising=False)

        import sys
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "openai", mock_openai)

        client = get_llm_client()
        assert client._model == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# get_llm_client — unknown provider
# ---------------------------------------------------------------------------


class TestFactoryUnknown:
    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "0")
        monkeypatch.setenv("GONGHAEBUN_LLM_PROVIDER", "anthropic")

        with pytest.raises(ValueError, match="알 수 없는 LLM provider"):
            get_llm_client()


# ---------------------------------------------------------------------------
# OpenAIClient strips fixture markers
# ---------------------------------------------------------------------------


class TestOpenAIClientStripMarker:
    def test_complete_strips_marker(self, monkeypatch):
        """OpenAIClient.complete() strips __fixture__ marker before API call."""
        import sys
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "response text"
        mock_openai.OpenAI.return_value.responses.create.return_value = mock_response
        mock_openai.APIError = Exception
        monkeypatch.setitem(sys.modules, "openai", mock_openai)

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from gonghaebun.llm.openai_client import OpenAIClient
        client = OpenAIClient(api_key="sk-test", model="gpt-5.5")

        result = client.complete("system", "prompt text\n__fixture__:x/y")
        assert result == "response text"

        # Verify the API was called with clean prompt (no marker)
        call_kwargs = mock_openai.OpenAI.return_value.responses.create.call_args[1]
        assert "__fixture__" not in call_kwargs["input"]
        assert call_kwargs["input"] == "prompt text"

    def test_complete_structured_strips_marker(self, monkeypatch):
        """OpenAIClient.complete_structured() strips __fixture__ marker."""
        import sys
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = '{"score": 0.8}'
        mock_openai.OpenAI.return_value.responses.create.return_value = mock_response
        mock_openai.APIError = Exception
        monkeypatch.setitem(sys.modules, "openai", mock_openai)

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from gonghaebun.llm.openai_client import OpenAIClient
        client = OpenAIClient(api_key="sk-test", model="gpt-5.5")

        schema = {"type": "object", "properties": {"score": {"type": "number"}}}
        result = client.complete_structured("system", "prompt\n__fixture__:a/b", schema)
        assert result == {"score": 0.8}

        call_kwargs = mock_openai.OpenAI.return_value.responses.create.call_args[1]
        assert "__fixture__" not in call_kwargs["input"]

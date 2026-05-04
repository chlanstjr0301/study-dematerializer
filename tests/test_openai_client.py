"""Tests for llm/errors.py and llm/openai_client.py (MVP3 Step 1)."""
from __future__ import annotations

import json
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from gonghaebun.llm.errors import LLMAPIKeyError, LLMError, LLMResponseError


# ---------------------------------------------------------------------------
# Helpers — build a fake openai module so we never need the real package
# ---------------------------------------------------------------------------

def _make_fake_openai(output_text: str = "hello") -> ModuleType:
    """Return a minimal fake `openai` module."""
    fake = ModuleType("openai")

    # Fake response object
    fake_response = MagicMock()
    fake_response.output_text = output_text

    # Fake responses.create
    fake_responses = MagicMock()
    fake_responses.create.return_value = fake_response

    # Fake client instance
    fake_client_instance = MagicMock()
    fake_client_instance.responses = fake_responses

    # Fake OpenAI class
    fake_openai_cls = MagicMock(return_value=fake_client_instance)
    fake.OpenAI = fake_openai_cls

    # Fake APIError
    class FakeAPIError(Exception):
        pass

    fake.APIError = FakeAPIError

    return fake


def _install_fake_openai(output_text: str = "hello") -> ModuleType:
    """Install fake openai into sys.modules and return it."""
    fake = _make_fake_openai(output_text)
    sys.modules["openai"] = fake
    return fake


def _remove_fake_openai() -> None:
    sys.modules.pop("openai", None)


# ---------------------------------------------------------------------------
# TestLLMErrors
# ---------------------------------------------------------------------------


class TestLLMErrors:
    def test_llm_error_is_exception(self):
        assert issubclass(LLMError, Exception)

    def test_llm_api_key_error_is_llm_error(self):
        assert issubclass(LLMAPIKeyError, LLMError)

    def test_llm_response_error_is_llm_error(self):
        assert issubclass(LLMResponseError, LLMError)

    def test_llm_api_key_error_message(self):
        exc = LLMAPIKeyError("missing key")
        assert "missing key" in str(exc)

    def test_llm_response_error_message(self):
        exc = LLMResponseError("bad json")
        assert "bad json" in str(exc)


# ---------------------------------------------------------------------------
# TestOpenAIClientInit
# ---------------------------------------------------------------------------


class TestOpenAIClientInit:
    def setup_method(self):
        _install_fake_openai()

    def teardown_method(self):
        _remove_fake_openai()

    def test_raises_api_key_error_when_key_is_none(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from gonghaebun.llm.openai_client import OpenAIClient

        with pytest.raises(LLMAPIKeyError):
            OpenAIClient(api_key=None)

    def test_raises_api_key_error_when_env_is_empty_string(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        from gonghaebun.llm.openai_client import OpenAIClient

        with pytest.raises(LLMAPIKeyError):
            OpenAIClient()

    def test_accepts_explicit_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")
        assert client._api_key == "sk-test"

    def test_accepts_env_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient()
        assert client._api_key == "sk-from-env"

    def test_default_model_is_gpt_4o_mini(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")
        assert client._model == "gpt-4o-mini"

    def test_custom_model_stored(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test", model="gpt-4o")
        assert client._model == "gpt-4o"


# ---------------------------------------------------------------------------
# TestOpenAIClientComplete
# ---------------------------------------------------------------------------


class TestOpenAIClientComplete:
    def setup_method(self):
        self._fake = _install_fake_openai(output_text="test output")

    def teardown_method(self):
        _remove_fake_openai()

    def _make_client(self) -> "OpenAIClient":  # noqa: F821
        from gonghaebun.llm.openai_client import OpenAIClient

        return OpenAIClient(api_key="sk-test")

    def test_complete_uses_responses_api(self):
        client = self._make_client()
        client.complete("sys", "usr")
        # responses.create must be called, not chat.completions
        client._client.responses.create.assert_called_once()

    def test_complete_passes_instructions_and_input(self):
        client = self._make_client()
        client.complete("my system", "my user")
        call_kwargs = client._client.responses.create.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert kwargs.get("instructions") == "my system"
        assert kwargs.get("input") == "my user"

    def test_complete_returns_output_text_from_response(self):
        client = self._make_client()
        result = client.complete("sys", "usr")
        assert result == "test output"

    def test_complete_json_returns_dict(self):
        _install_fake_openai(output_text=json.dumps({"key": "value"}))
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")
        result = client.complete_json("sys", "usr")
        assert result == {"key": "value"}

    def test_complete_json_raises_response_error_on_bad_json(self):
        _install_fake_openai(output_text="not valid json {{{")
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")
        with pytest.raises(LLMResponseError):
            client.complete_json("sys", "usr")

    def test_openai_api_error_raised_as_llm_error(self):
        client = self._make_client()
        # Make responses.create raise the fake APIError
        fake_openai = sys.modules["openai"]

        class _FakeAPIError(Exception):
            pass

        fake_openai.APIError = _FakeAPIError
        client._client.responses.create.side_effect = _FakeAPIError("quota exceeded")

        with pytest.raises(LLMError):
            client.complete("sys", "usr")

"""Tests for OpenAI client retry logic, _is_retryable, and per-call logging."""
from __future__ import annotations

import logging
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from gonghaebun.llm.errors import LLMError


# ---------------------------------------------------------------------------
# Fake openai module with typed exception classes
# ---------------------------------------------------------------------------

def _make_fake_openai_with_exceptions(output_text: str = "hello") -> ModuleType:
    """Return a fake openai module with typed exception hierarchy."""
    fake = ModuleType("openai")

    fake_response = MagicMock()
    fake_response.output_text = output_text

    fake_responses = MagicMock()
    fake_responses.create.return_value = fake_response

    fake_client_instance = MagicMock()
    fake_client_instance.responses = fake_responses

    fake_openai_cls = MagicMock(return_value=fake_client_instance)
    fake.OpenAI = fake_openai_cls

    class FakeAPIError(Exception):
        pass

    class FakeAPITimeoutError(FakeAPIError):
        pass

    class FakeRateLimitError(FakeAPIError):
        pass

    class FakeInternalServerError(FakeAPIError):
        pass

    class FakeAPIConnectionError(FakeAPIError):
        pass

    fake.APIError = FakeAPIError
    fake.APITimeoutError = FakeAPITimeoutError
    fake.RateLimitError = FakeRateLimitError
    fake.InternalServerError = FakeInternalServerError
    fake.APIConnectionError = FakeAPIConnectionError

    return fake


def _install(output_text: str = "hello") -> ModuleType:
    fake = _make_fake_openai_with_exceptions(output_text)
    sys.modules["openai"] = fake
    return fake


def _cleanup():
    sys.modules.pop("openai", None)


@pytest.fixture(autouse=True)
def _fake_openai():
    _install()
    yield
    _cleanup()


def _make_client():
    from gonghaebun.llm.openai_client import OpenAIClient

    return OpenAIClient(api_key="sk-test")


# ---------------------------------------------------------------------------
# SDK max_retries=0
# ---------------------------------------------------------------------------


class TestSDKMaxRetries:
    def test_sdk_constructed_with_max_retries_zero(self):
        fake = sys.modules["openai"]
        _make_client()
        call_kwargs = fake.OpenAI.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert kwargs.get("max_retries") == 0


# ---------------------------------------------------------------------------
# _is_retryable exception-type detection
# ---------------------------------------------------------------------------


class TestIsRetryable:
    def _make_llm_error_with_cause(self, cause):
        exc = LLMError(f"OpenAI API error: {cause}")
        exc.__cause__ = cause
        return exc

    def test_timeout_is_not_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        fake = sys.modules["openai"]
        cause = fake.APITimeoutError("timed out")
        exc = self._make_llm_error_with_cause(cause)
        assert OpenAIClient._is_retryable(exc) is False

    def test_rate_limit_is_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        fake = sys.modules["openai"]
        cause = fake.RateLimitError("429")
        exc = self._make_llm_error_with_cause(cause)
        assert OpenAIClient._is_retryable(exc) is True

    def test_internal_server_error_is_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        fake = sys.modules["openai"]
        cause = fake.InternalServerError("500")
        exc = self._make_llm_error_with_cause(cause)
        assert OpenAIClient._is_retryable(exc) is True

    def test_connection_error_is_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        fake = sys.modules["openai"]
        cause = fake.APIConnectionError("connection reset")
        exc = self._make_llm_error_with_cause(cause)
        assert OpenAIClient._is_retryable(exc) is True

    def test_no_cause_falls_back_to_string_matching(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        exc = LLMError("status code 429 rate limited")
        exc.__cause__ = None
        assert OpenAIClient._is_retryable(exc) is True

    def test_no_cause_unrelated_message_not_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        exc = LLMError("unknown error occurred")
        exc.__cause__ = None
        assert OpenAIClient._is_retryable(exc) is False

    def test_unknown_api_error_type_not_retryable(self):
        from gonghaebun.llm.openai_client import OpenAIClient

        fake = sys.modules["openai"]
        cause = fake.APIError("some other API error")
        exc = self._make_llm_error_with_cause(cause)
        assert OpenAIClient._is_retryable(exc) is False


# ---------------------------------------------------------------------------
# _call_with_retry logging
# ---------------------------------------------------------------------------


class TestCallWithRetryLogging:
    def test_successful_call_logs_ok(self, caplog):
        client = _make_client()
        with caplog.at_level(logging.INFO, logger="gonghaebun.llm.openai"):
            client.complete("sys", "usr")

        ok_logs = [r for r in caplog.records if "llm_call_ok" in r.message]
        assert len(ok_logs) == 1
        assert "method=complete" in ok_logs[0].message
        assert "elapsed_ms=" in ok_logs[0].message

    def test_failed_call_logs_fail_and_error_class(self, caplog):
        client = _make_client()
        fake = sys.modules["openai"]
        client._client.responses.create.side_effect = fake.APIError("boom")

        with caplog.at_level(logging.WARNING, logger="gonghaebun.llm.openai"):
            with pytest.raises(LLMError):
                client.complete("sys", "usr")

        fail_logs = [r for r in caplog.records if "llm_call_fail" in r.message]
        assert len(fail_logs) >= 1
        assert "error_class=LLMError" in fail_logs[0].message

    def test_complete_structured_logs_method_name(self, caplog):
        import json

        _install(output_text=json.dumps({"result": 1}))
        client = _make_client()

        with caplog.at_level(logging.INFO, logger="gonghaebun.llm.openai"):
            client.complete_structured("sys", "usr", {"type": "object", "properties": {}})

        ok_logs = [r for r in caplog.records if "llm_call_ok" in r.message]
        assert len(ok_logs) == 1
        assert "method=complete_structured" in ok_logs[0].message

    def test_retry_on_rate_limit_logs_retry(self, caplog, monkeypatch):
        """Rate limit causes retry with backoff logging."""
        fake = sys.modules["openai"]
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")

        # First call: rate limit; second call: success
        rate_err = fake.RateLimitError("429 rate limited")
        ok_response = MagicMock()
        ok_response.output_text = "ok"
        client._client.responses.create.side_effect = [rate_err, ok_response]

        # Patch sleep to avoid waiting
        monkeypatch.setattr("gonghaebun.llm.openai_client.time.sleep", lambda _: None)

        with caplog.at_level(logging.INFO, logger="gonghaebun.llm.openai"):
            result = client.complete("sys", "usr")

        assert result == "ok"
        retry_logs = [r for r in caplog.records if "llm_retry" in r.message]
        assert len(retry_logs) == 1

    def test_timeout_not_retried(self, monkeypatch):
        """Timeout error should NOT trigger retry."""
        fake = sys.modules["openai"]
        from gonghaebun.llm.openai_client import OpenAIClient

        client = OpenAIClient(api_key="sk-test")
        timeout_err = fake.APITimeoutError("request timed out")
        client._client.responses.create.side_effect = timeout_err

        monkeypatch.setattr("gonghaebun.llm.openai_client.time.sleep", lambda _: None)

        with pytest.raises(LLMError):
            client.complete("sys", "usr")

        # Should have been called exactly once (no retry)
        assert client._client.responses.create.call_count == 1

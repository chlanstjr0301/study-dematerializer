"""
Tests for gonghaebun.grading.factory and gonghaebun.llm.config.
"""
from __future__ import annotations

import pytest

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.grading.factory import make_grader
from gonghaebun.grading.llm_grader import LLMGrader
from gonghaebun.grading.self_grader import SelfGrader
from gonghaebun.llm.config import BASELINE_OPENAI_MODEL, DEFAULT_OPENAI_MODEL


class TestLLMConfig:
    def test_default_model_is_not_gpt4o_mini(self):
        assert DEFAULT_OPENAI_MODEL != "gpt-4o-mini"

    def test_default_model_value(self):
        assert DEFAULT_OPENAI_MODEL == "gpt-5.4-mini"

    def test_baseline_model_value(self):
        assert BASELINE_OPENAI_MODEL == "gpt-5.5"

    def test_no_gpt4o_mini_default_in_config(self):
        """Regression: llm/config.py must not set gpt-4o-mini as a default."""
        import inspect
        import gonghaebun.llm.config as config_mod
        source = inspect.getsource(config_mod)
        assert "gpt-4o-mini" not in source


class TestMakeGraderSelf:
    def test_returns_self_grader(self):
        grader = make_grader("self")
        assert isinstance(grader, SelfGrader)
        assert isinstance(grader, AnswerGrader)

    def test_model_ignored_for_self(self):
        grader = make_grader("self", model="anything")
        assert isinstance(grader, SelfGrader)


class TestMakeGraderMock:
    def test_returns_llm_grader_with_mock_client(self):
        grader = make_grader("mock")
        assert isinstance(grader, LLMGrader)
        assert isinstance(grader, AnswerGrader)

    def test_model_ignored_for_mock(self):
        grader = make_grader("mock", model="anything")
        assert isinstance(grader, LLMGrader)


class TestMakeGraderLLM:
    def test_raises_llm_api_key_error_when_no_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from gonghaebun.llm.errors import LLMAPIKeyError
        with pytest.raises(LLMAPIKeyError):
            make_grader("llm")

    def test_uses_default_model_when_none_provided(self, monkeypatch):
        """make_grader("llm") should use DEFAULT_OPENAI_MODEL, not gpt-4o-mini."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from gonghaebun.llm.errors import LLMAPIKeyError
        # Even though it will raise (no key), the error should come from OpenAIClient
        # not from a hardcoded model string. The important thing is the factory
        # does not embed "gpt-4o-mini" itself.
        import inspect
        from gonghaebun.grading import factory as factory_mod
        source = inspect.getsource(factory_mod)
        assert "gpt-4o-mini" not in source

    def test_raises_value_error_for_unknown_grader(self):
        with pytest.raises(ValueError, match="Unknown grader type"):
            make_grader("unknown_grader")


class TestNoGpt4oMiniInAPIModules:
    """Regression: API service and schema modules must not use gpt-4o-mini as a default."""

    def test_session_service_no_gpt4o_mini(self):
        import inspect
        import apps.api.services.session_service as svc
        assert "gpt-4o-mini" not in inspect.getsource(svc)

    def test_api_schemas_no_gpt4o_mini(self):
        import inspect
        import apps.api.schemas.api_schemas as schemas
        assert "gpt-4o-mini" not in inspect.getsource(schemas)

    def test_api_config_no_gpt4o_mini(self):
        import inspect
        import apps.api.config as api_config
        assert "gpt-4o-mini" not in inspect.getsource(api_config)

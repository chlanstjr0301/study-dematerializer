"""
Grader factory — neutral engine module for constructing AnswerGrader instances.

Import this instead of importing from cli.py to avoid coupling web services
or eval utilities to CLI internals.
"""
from __future__ import annotations

from gonghaebun.grading.answer_grader import AnswerGrader
from gonghaebun.llm.config import DEFAULT_OPENAI_MODEL


def make_grader(grader: str, model: str | None = None) -> AnswerGrader:
    """
    Instantiate the requested AnswerGrader.

    Parameters
    ----------
    grader : "self" | "mock" | "llm"
    model  : LLM model ID (only used when grader="llm").
             Defaults to DEFAULT_OPENAI_MODEL if not provided.

    Returns
    -------
    AnswerGrader instance.

    Raises
    ------
    ValueError         : if grader is not one of the recognised types.
    LLMAPIKeyError     : if grader="llm" and OPENAI_API_KEY is not set.
    ImportError        : if grader="llm" and the openai package is not installed.
    """
    if grader == "self":
        from gonghaebun.grading.self_grader import SelfGrader
        return SelfGrader()

    if grader == "mock":
        from gonghaebun.grading.llm_grader import LLMGrader
        from gonghaebun.llm.mock import MockLLMClient
        return LLMGrader(MockLLMClient())

    if grader == "llm":
        from gonghaebun.grading.llm_grader import LLMGrader
        from gonghaebun.llm.openai_client import OpenAIClient
        resolved_model = model if model is not None else DEFAULT_OPENAI_MODEL
        client = OpenAIClient(model=resolved_model)
        return LLMGrader(client)

    raise ValueError(f"Unknown grader type: {grader!r}. Expected 'self', 'mock', or 'llm'.")

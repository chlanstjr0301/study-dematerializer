"""
Build the (system, user) prompt pair for LLM-based answer grading.

Loads the system prompt from prompts/answer_grader.txt via load_prompt().
"""
from __future__ import annotations

from gonghaebun.prompts import load_prompt


def build_grading_prompt(
    question: str,
    expected_answer: str,
    evidence_text: str,
    learner_response: str,
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the answer-grading LLM call.

    The user prompt embeds all four inputs so the LLM can grade without
    external knowledge. Also includes the MockLLMClient fixture key so that
    MockLLMClient returns the grading fixture during tests.
    """
    system = load_prompt("answer_grader")

    user = (
        f"## Question\n{question}\n\n"
        f"## Expected Answer (source-grounded)\n{expected_answer}\n\n"
        f"## Source Evidence\n{evidence_text}\n\n"
        f"## Learner Response\n{learner_response}\n\n"
        "__fixture__:grading/answer_grader"
    )

    return system, user

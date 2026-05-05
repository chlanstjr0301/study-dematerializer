"""
Build the (system, user) prompt pair for LLM-based answer grading.

Loads the system prompt from prompts/answer_grader.txt via load_prompt().
"""
from __future__ import annotations

from gonghaebun.prompts import load_prompt

_STRICT_REPRESENTATION_TYPES = {"formal", "proof_schema"}


def build_grading_prompt(
    question: str,
    expected_answer: str,
    evidence_text: str,
    learner_response: str,
    concept_id: str = "",
    representation_type: str = "",
) -> tuple[str, str]:
    """
    Return (system_prompt, user_prompt) for the answer-grading LLM call.

    The user prompt embeds all four inputs so the LLM can grade without
    external knowledge. Also includes the MockLLMClient fixture key so that
    MockLLMClient returns the grading fixture during tests.

    Parameters
    ----------
    question          : the study question text
    expected_answer   : source-grounded expected answer
    evidence_text     : raw source evidence passage
    learner_response  : the learner's free-text response
    concept_id        : optional concept context (e.g. "compactness")
    representation_type : optional rep context (e.g. "formal", "intuitive")
    """
    system = load_prompt("answer_grader")

    parts = []

    # Optional context block
    if concept_id or representation_type:
        context_lines = ["## Context"]
        if concept_id:
            context_lines.append(f"Concept: {concept_id}")
        if representation_type:
            context_lines.append(f"Representation type: {representation_type}")
        parts.append("\n".join(context_lines))

    parts += [
        f"## Question\n{question}",
        f"## Expected Answer (source-grounded)\n{expected_answer}",
        f"## Source Evidence\n{evidence_text}",
        f"## Learner Response\n{learner_response}",
    ]

    # Strictness note for formal/proof_schema representations
    if representation_type in _STRICT_REPRESENTATION_TYPES:
        parts.append(
            "## Grading Note\n"
            "This is a formal or proof-schema question. "
            "Missing quantifiers, imprecise variable scoping, or informal "
            "phrasing that omits required logical structure should be "
            "reflected in missing_elements and a reduced accuracy_score."
        )

    # MockLLMClient fixture key (must be last)
    parts.append("__fixture__:grading/answer_grader")

    user = "\n\n".join(parts)
    return system, user

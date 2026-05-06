"""
Stage 5: Self-Explanation Evaluator.

Generates the self-explanation prompt template (no LLM for prompt generation)
and evaluates a learner's response using the LLM.

In a non-interactive session the learner_response is left empty and no
evaluation is performed.
"""
from __future__ import annotations

from gonghaebun.llm.base import LLMClient
from gonghaebun.models.representations import RepresentationSet
from gonghaebun.models.session_models import RecallEvaluation
from gonghaebun.pipeline.evaluation_schema import EVALUATION_OUTPUT_SCHEMA, validate_evaluation_output
from gonghaebun.prompts import load_prompt


def render_self_explanation_prompt(
    concept_id: str,
    rep_set: RepresentationSet,
) -> str:
    """
    Generate the self-explanation prompt Markdown for the learner.
    No LLM call — pure template.
    """
    lines = [
        f"# Self-Explanation — {concept_id}",
        "",
        "Read through the representations below, then **close your notes** and "
        "write your own explanation from memory.",
        "",
    ]
    for rep in rep_set.as_list():
        lines += [
            f"## {rep.type.replace('_', ' ').title()}",
            "",
            rep.content,
            "",
        ]
    lines += [
        "---",
        "",
        "## Your Explanation",
        "",
        "> Write your explanation here. Do not look at the representations above.",
        "",
    ]
    return "\n".join(lines)


def evaluate_self_explanation(
    concept_id: str,
    representation_type: str,
    target_content: str,
    learner_response: str,
    llm: LLMClient,
) -> RecallEvaluation:
    """
    Ask the LLM to evaluate the learner's self-explanation.
    Returns a RecallEvaluation.
    """
    system = load_prompt("global_system")
    stage5_prompt = load_prompt("stage5_self_explanation_evaluator")

    user = (
        f"{stage5_prompt}\n\n"
        f"## Concept\n{concept_id}\n\n"
        f"## Representation Type\n{representation_type}\n\n"
        f"## Target Content\n{target_content}\n\n"
        f"## Learner Explanation\n{learner_response}\n\n"
        f"__fixture__:{concept_id}/self_explanation_eval"
    )

    data = llm.complete_structured(system, user, EVALUATION_OUTPUT_SCHEMA)
    return validate_evaluation_output(data)

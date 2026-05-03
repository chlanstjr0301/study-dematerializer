"""
Stage 6: White Recall Orchestrator.

Generates retrieval-practice tasks based on the learner's current mastery state.
In a non-interactive session, tasks are written to recall_tasks.md and no
learner responses are collected.
"""
from __future__ import annotations

from gonghaebun.llm.base import LLMClient
from gonghaebun.prompts import load_prompt


def generate_recall_tasks(
    concept_id: str,
    mastery_state: str,
    llm: LLMClient,
) -> dict:
    """
    Ask the LLM to generate retrieval tasks appropriate for the mastery_state.

    Returns the raw tasks dict, e.g.:
    {
      "concept_id": "compactness",
      "mastery_state": "unknown",
      "tasks": [{"id": ..., "type": ..., "prompt": ..., "hint": null}]
    }
    """
    system = load_prompt("global_system")
    stage6_prompt = load_prompt("stage6_recall_orchestrator")

    user = (
        f"{stage6_prompt}\n\n"
        f"## Concept\n{concept_id}\n\n"
        f"## Current Mastery State\n{mastery_state}\n\n"
        f"__fixture__:{concept_id}/recall_tasks"
    )

    return llm.complete_json(system, user)


def render_recall_tasks(tasks_data: dict) -> str:
    """Render the recall tasks dict to a Markdown string."""
    concept_id = tasks_data.get("concept_id", "unknown")
    mastery_state = tasks_data.get("mastery_state", "unknown")
    tasks = tasks_data.get("tasks", [])

    lines = [
        f"# White Recall Tasks — {concept_id}",
        f"_Mastery state: {mastery_state}_",
        "",
        "> **Instructions**: Complete these tasks WITHOUT looking at any notes or materials.",
        "",
    ]
    for i, task in enumerate(tasks, 1):
        lines += [
            f"## Task {i} ({task.get('type', 'recall')})",
            "",
            task.get("prompt", ""),
            "",
        ]

    return "\n".join(lines)

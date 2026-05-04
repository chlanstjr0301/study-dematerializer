"""
Stage 6: White Recall Orchestrator.

Generates retrieval-practice tasks based on the learner's current mastery state.
In a non-interactive session, tasks are written to recall_tasks.md and no
learner responses are collected.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from gonghaebun.llm.base import LLMClient
from gonghaebun.models.question_bank import Evidence, Question
from gonghaebun.prompts import load_prompt

# Maps recall task type → representation type key in representation_set.json
TASK_TYPE_TO_REP: dict[str, str] = {
    "definition_recall": "formal",
    "counterexample_recall": "counterexample",
    "intuition_recall": "intuitive",
    "proof_schema_recall": "proof_schema",
    "visual_recall": "visual",
}


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


def convert_tasks_to_questions(
    tasks_data: dict,
    rep_set_data: dict,
    concept_id: str,
) -> list[Question]:
    """
    Convert recall_tasks dict + representation_set dict → list[Question].

    Each task becomes one Question:
    - question_id: f"q_compiler_{concept_id}_{task_id}"
    - question:    task["prompt"]
    - question_type: task["type"]
    - expected_answer: representation content for that type (capped at 800 chars)
    - status: "candidate"
    - difficulty: "hard" for proof_schema_recall, "medium" otherwise
    """
    now = datetime.now(timezone.utc).isoformat()
    questions: list[Question] = []

    for task in tasks_data.get("tasks", []):
        task_id = task.get("id", "")
        task_type = task.get("type", "")
        prompt = task.get("prompt", "")

        rep_key = TASK_TYPE_TO_REP.get(task_type, "formal")
        rep_entry = rep_set_data.get(rep_key, {})
        rep_content = rep_entry.get("content", "") if isinstance(rep_entry, dict) else ""
        expected = rep_content[:800]

        difficulty = "hard" if task_type == "proof_schema_recall" else "medium"

        text_hash = hashlib.sha256(rep_content.encode("utf-8")).hexdigest()
        evidence = Evidence(
            source_text=expected or prompt[:800],
            source_file=f"representation_set.json#{rep_key}",
            start_line=None,
            end_line=None,
            text_hash=text_hash,
        )

        questions.append(
            Question(
                question_id=f"q_compiler_{concept_id}_{task_id}",
                document_id=concept_id,
                source_block_id=f"{concept_id}_{rep_key}",
                question_type=task_type,
                difficulty=difficulty,
                question=prompt,
                expected_answer=expected or prompt[:800],
                evidence=evidence,
                rule_id="compiler_representation",
                status="candidate",
                created_at=now,
                updated_at=now,
            )
        )

    return questions

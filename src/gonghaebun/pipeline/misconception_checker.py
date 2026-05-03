"""
Stage 4: Misconception Checker.

Given a concept and its representations, the LLM identifies common
misconceptions and checks whether the learner's current understanding
shows signs of them.

Returns the raw diagnosis dict (as returned by the LLM / fixture).
"""
from __future__ import annotations

from gonghaebun.llm.base import LLMClient
from gonghaebun.models.representations import RepresentationSet
from gonghaebun.prompts import load_prompt


def check_misconceptions(
    concept_id: str,
    rep_set: RepresentationSet,
    source_coverage: str,
    llm: LLMClient,
) -> dict:
    """
    Call the LLM to identify potential misconceptions for this concept.

    Returns the full diagnosis dict, e.g.:
    {
      "concept_id": "compactness",
      "misconceptions": [
        {"id": ..., "claim": ..., "is_correct": false, "counterexample": ..., ...}
      ]
    }
    """
    system = load_prompt("global_system")
    stage4_prompt = load_prompt("stage4_misconception_checker")

    representations_summary = "\n".join(
        f"### {r.type}\n{r.content[:300]}..." for r in rep_set.as_list()
    )

    user = (
        f"{stage4_prompt}\n\n"
        f"## Concept\n{concept_id}\n\n"
        f"## Representations (summary)\n{representations_summary}\n\n"
        f"## Source Coverage\n{source_coverage}\n\n"
        f"__fixture__:{concept_id}/misconceptions"
    )

    result = llm.complete_json(system, user)
    result.setdefault("source_coverage_notes", f"Source coverage: {source_coverage}")
    return result

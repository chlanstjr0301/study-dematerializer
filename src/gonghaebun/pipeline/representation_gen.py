"""
Stage 3: Representation Generator.

Generates all 5 representation types for a concept using the LLM.
Each representation is generated with its own prompt and the source excerpt
for grounding.

Returns a RepresentationSet.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.llm.base import LLMClient
from gonghaebun.models.representations import Representation, RepresentationSet
from gonghaebun.prompts import load_prompt

logger = logging.getLogger("gonghaebun.pipeline.representation_gen")

_STAGE3_KEYS = {
    "formal": "stage3_formal",
    "intuitive": "stage3_intuitive",
    "visual": "stage3_visual",
    "counterexample": "stage3_counterexample",
    "proof_schema": "stage3_proof_schema",
}


def generate_representations(
    concept_id: str,
    source_excerpt: str,
    source_hash: str,
    llm: LLMClient,
) -> RepresentationSet:
    """
    Call the LLM once per representation type (5 calls total).
    Returns a RepresentationSet with all 5 populated Representations.
    """
    system = load_prompt("global_system")
    reps: dict[str, Representation] = {}

    for rep_type, stage_key in _STAGE3_KEYS.items():
        logger.info("rep_gen_start rep_type=%s concept=%s", rep_type, concept_id)
        _t0 = time.monotonic()
        prompt_template = load_prompt(stage_key)
        user = (
            f"{prompt_template}\n\n"
            f"## Concept\n{concept_id}\n\n"
            f"## Source Excerpt\n{source_excerpt}\n\n"
            f"## Grounding\nSource hash: {source_hash}\n\n"
            f"__fixture__:{concept_id}/representations"
        )
        raw = llm.complete(system, user)
        logger.info(
            "rep_gen_done rep_type=%s elapsed_ms=%.0f",
            rep_type, (time.monotonic() - _t0) * 1000,
        )

        # MockLLMClient returns full JSON; parse and extract this rep_type
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and rep_type in data:
                entry = data[rep_type]
                content = entry.get("content", raw)
            else:
                content = raw
        except (json.JSONDecodeError, TypeError):
            content = raw

        # Append grounding footer
        content = (
            f"{content}\n\n"
            f"> **Grounding**: Based on local private source material.\n"
            f"> Source hash: {source_hash}\n"
            f"> Full source text not reproduced."
        )

        reps[rep_type] = Representation(type=rep_type, content=content)  # type: ignore[arg-type]

    now = datetime.now(timezone.utc).isoformat()
    return RepresentationSet(
        concept_id=concept_id,
        formal=reps["formal"],
        intuitive=reps["intuitive"],
        visual=reps["visual"],
        counterexample=reps["counterexample"],
        proof_schema=reps["proof_schema"],
        generated_at=now,
        model_used=llm.__class__.__name__,
    )


def render_representation_cards(rep_set: RepresentationSet) -> str:
    """Render all 5 representations to a single Markdown string."""
    lines = [
        f"# Representation Cards — {rep_set.concept_id}",
        f"_Generated: {rep_set.generated_at}_",
        f"_Model: {rep_set.model_used}_",
        "",
    ]
    for rep in rep_set.as_list():
        lines += [
            "---",
            "",
            f"## {rep.type.replace('_', ' ').title()}",
            "",
            rep.content,
            "",
        ]
    return "\n".join(lines)

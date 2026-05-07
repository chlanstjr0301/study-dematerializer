"""
Top-level session orchestrator for Gonghaebun MVP 1.

Runs Stages 0–7 in sequence and writes all 10 artifacts to output_dir.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.knowledge.real_analysis import CONCEPT_KEYWORDS
from gonghaebun.llm.base import LLMClient
from gonghaebun.models.session_models import MasteryUpdate, StudySession
from gonghaebun.pipeline.concept_resolver import resolve_concept
from gonghaebun.pipeline.graph_builder import build_prerequisite_graph
from gonghaebun.pipeline.misconception_checker import check_misconceptions
from gonghaebun.pipeline.recall_orchestrator import generate_recall_tasks, render_recall_tasks
from gonghaebun.pipeline.representation_gen import (
    generate_representations,
    render_representation_cards,
)
from gonghaebun.pipeline.self_explanation import render_self_explanation_prompt
from gonghaebun.pipeline.source_loader import load_and_extract
from gonghaebun.pipeline.study_writer import write_study_artifacts
from gonghaebun.study_md.writer import compute_mastery_state, compute_next_review_date

logger = logging.getLogger("gonghaebun.session")


def run_new_concept_session(
    concept_input: str,
    source_path: Path,
    llm: LLMClient,
    output_dir: Path,
    study_md_path: Path,
    interactive: bool = False,
    session_id: str | None = None,
) -> StudySession:
    """
    Run a full new-concept study session (Stages 0–7).

    Writes all 12 artifacts to output_dir:
      1. source_manifest.json
      2. source_excerpt.md
      3. concept_decomposition.json
      4. prerequisite_graph.json
      5. representation_cards.md
      6. representation_set.json
      7. self_explanation_prompt.md
      8. diagnosis.json
      9. recall_tasks.md
      10. recall_tasks.json
      11. STUDY.patch.md
      12. session.json

    If session_id is provided it is used as-is; otherwise a new UUID is generated.
    Returns the finalized StudySession.
    """
    session_id = session_id or str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Stage 0: Source Loader
    # ------------------------------------------------------------------
    logger.info("stage_start stage=0 name=source_loader concept=%s", concept_input)
    _t0 = time.monotonic()
    concept = resolve_concept(concept_input)
    concept_id = concept.concept_id
    keywords = CONCEPT_KEYWORDS.get(concept_id, [])

    manifest = load_and_extract(
        source_path=source_path,
        concept_id=concept_id,
        keywords=keywords,
        output_dir=output_dir,
    )

    source_excerpt_path = output_dir / "source_excerpt.md"
    source_excerpt = source_excerpt_path.read_text(encoding="utf-8")
    logger.info("stage_done stage=0 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Stage 1: Concept Resolver — write concept_decomposition.json
    # ------------------------------------------------------------------
    logger.info("stage_start stage=1 name=concept_resolver concept=%s", concept_id)
    _t0 = time.monotonic()
    concept_decomposition = {
        "concept_id": concept_id,
        "canonical_name": concept.canonical_name,
        "domain": concept.domain,
        "aliases": concept.aliases,
        "prerequisites": concept.prerequisites,
        "grounding_status": "source_excerpt",
        "source_coverage": manifest.source_coverage,
        "generated_at": started_at,
        "llm_backend": llm.__class__.__name__,
    }
    (output_dir / "concept_decomposition.json").write_text(
        json.dumps(concept_decomposition, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("stage_done stage=1 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Stage 2: Prerequisite Graph — write prerequisite_graph.json
    # ------------------------------------------------------------------
    logger.info("stage_start stage=2 name=graph_builder concept=%s", concept_id)
    _t0 = time.monotonic()
    graph = build_prerequisite_graph(concept_id)
    graph_data = {
        "root_concept_id": graph.root_concept_id,
        "nodes": [
            {
                "concept_id": n.concept_id,
                "canonical_name": n.canonical_name,
                "depth": n.depth,
                "mastery_state": n.mastery_state,
            }
            for n in graph.nodes
        ],
        "edges": [
            {"from_concept": e.from_concept, "to_concept": e.to_concept}
            for e in graph.edges
        ],
        "generated_at": graph.generated_at,
    }
    (output_dir / "prerequisite_graph.json").write_text(
        json.dumps(graph_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("stage_done stage=2 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Stage 3: Representation Generator — write representation_cards.md
    # ------------------------------------------------------------------
    logger.info("stage_start stage=3 name=representation_gen concept=%s", concept_id)
    _t0 = time.monotonic()
    rep_set = generate_representations(
        concept_id=concept_id,
        source_excerpt=source_excerpt,
        source_hash=manifest.source_hash,
        llm=llm,
    )
    cards_md = render_representation_cards(rep_set)
    (output_dir / "representation_cards.md").write_text(cards_md, encoding="utf-8")

    rep_set_data = {
        rep.type: {
            "type": rep.type,
            "content": rep.content,
            "mastery_state": rep.mastery_state,
            "last_reviewed": rep.last_reviewed,
        }
        for rep in rep_set.as_list()
    }
    (output_dir / "representation_set.json").write_text(
        json.dumps(rep_set_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("stage_done stage=3 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Stage 5 (template only): Self-Explanation Prompt
    # ------------------------------------------------------------------
    self_exp_md = render_self_explanation_prompt(concept_id, rep_set)
    (output_dir / "self_explanation_prompt.md").write_text(self_exp_md, encoding="utf-8")

    # ------------------------------------------------------------------
    # Stage 4: Misconception Checker — write diagnosis.json
    # ------------------------------------------------------------------
    logger.info("stage_start stage=4 name=misconception_checker concept=%s", concept_id)
    _t0 = time.monotonic()
    diagnosis = check_misconceptions(
        concept_id=concept_id,
        rep_set=rep_set,
        source_coverage=manifest.source_coverage,
        llm=llm,
    )
    (output_dir / "diagnosis.json").write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("stage_done stage=4 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Stage 6: White Recall — write recall_tasks.md
    # ------------------------------------------------------------------
    logger.info("stage_start stage=6 name=recall_orchestrator concept=%s", concept_id)
    _t0 = time.monotonic()
    # Default mastery for a brand-new concept
    recall_mastery = "unknown"
    tasks_data = generate_recall_tasks(
        concept_id=concept_id,
        mastery_state=recall_mastery,
        llm=llm,
    )
    recall_md = render_recall_tasks(tasks_data)
    (output_dir / "recall_tasks.md").write_text(recall_md, encoding="utf-8")
    (output_dir / "recall_tasks.json").write_text(
        json.dumps(tasks_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("stage_done stage=6 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Build mastery updates (one per representation type, from recall tasks)
    # ------------------------------------------------------------------
    mastery_updates: list[MasteryUpdate] = []
    for rep in rep_set.as_list():
        after = compute_mastery_state(0.0)  # no learner response in non-interactive
        next_review = compute_next_review_date(after)
        mastery_updates.append(
            MasteryUpdate(
                concept_id=concept_id,
                representation_type=rep.type,
                before="unknown",
                after=after,
                next_review_date=next_review,
            )
        )

    # ------------------------------------------------------------------
    # Assemble StudySession
    # ------------------------------------------------------------------
    ended_at = datetime.now(timezone.utc).isoformat()
    session = StudySession(
        session_id=session_id,
        session_type="new_concept",
        concept_ids=[concept_id],
        started_at=started_at,
        ended_at=ended_at,
        llm_backend=llm.__class__.__name__,
        source_path=str(source_path),
        source_hash=manifest.source_hash,
        grounding_mode=manifest.grounding_mode,
        source_excerpt_path=str(output_dir / "source_excerpt.md"),
        source_manifest_path=str(output_dir / "source_manifest.json"),
        mastery_updates=mastery_updates,
        recall_attempts=[],
    )

    # ------------------------------------------------------------------
    # Stage 7: Study Writer — STUDY.patch.md + STUDY.md
    # ------------------------------------------------------------------
    logger.info("stage_start stage=7 name=study_writer concept=%s", concept_id)
    _t0 = time.monotonic()
    write_study_artifacts(session, output_dir, study_md_path)
    logger.info("stage_done stage=7 elapsed_ms=%.0f", (time.monotonic() - _t0) * 1000)

    # ------------------------------------------------------------------
    # Write session.json (artifact 10)
    # ------------------------------------------------------------------
    session_data = {
        "session_id": session.session_id,
        "session_type": session.session_type,
        "concept_ids": session.concept_ids,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "llm_backend": session.llm_backend,
        "source_path": session.source_path,
        "source_hash": session.source_hash,
        "grounding_mode": session.grounding_mode,
        "source_excerpt_path": session.source_excerpt_path,
        "source_manifest_path": session.source_manifest_path,
        "mastery_updates": [
            {
                "concept_id": u.concept_id,
                "representation_type": u.representation_type,
                "before": u.before,
                "after": u.after,
                "next_review_date": u.next_review_date,
            }
            for u in session.mastery_updates
        ],
    }
    (output_dir / "session.json").write_text(
        json.dumps(session_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return session

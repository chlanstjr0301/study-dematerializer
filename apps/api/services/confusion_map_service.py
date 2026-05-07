"""
Confusion map lifecycle service for MVP6.

Manages the per-session ConfusionMap artifact: initialization, per-step updates,
persistence to disk, and loading from disk.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.models.confusion_map import (
    ConfusionMap,
    EvidenceSnippet,
    MappingEdge,
    PrerequisiteNode,
)
from gonghaebun.models.evaluation_output import EvaluationOutput
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.mapping_models import MappingResult

_CONFUSION_MAP_FILENAME = "confusion_map.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------


def initialize_confusion_map(
    session_id: str,
    concept_id: str,
    card: GroundTruthCard,
) -> ConfusionMap:
    """Create an initial empty confusion map from the card's prerequisites."""
    now = _now_iso()
    return ConfusionMap(
        concept_id=concept_id,
        session_id=session_id,
        prerequisite_nodes=[
            PrerequisiteNode(concept_id=prereq, mastery="unknown")
            for prereq in card.prerequisite_concepts
        ],
        mapping_edges=[],
        misconception_tags=[],
        next_recall_triggers=[],
        evidence_snippets=[],
        last_updated_step="init",
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Per-step updates
# ---------------------------------------------------------------------------


def update_from_diagnosis(
    cmap: ConfusionMap,
    diagnosis: dict,
) -> ConfusionMap:
    """Update confusion map after diagnosis step.

    diagnosis dict may contain:
      - "mastery_estimates": {concept_id: mastery_level} for prerequisites
      - "misconception_cues": list[str] of misconception IDs detected
    """
    mastery_estimates = diagnosis.get("mastery_estimates", {})
    for node in cmap.prerequisite_nodes:
        if node.concept_id in mastery_estimates:
            node.mastery = mastery_estimates[node.concept_id]

    cues = diagnosis.get("misconception_cues", [])
    for cue in cues:
        if cue not in cmap.misconception_tags:
            cmap.misconception_tags.append(cue)

    cmap.last_updated_step = "diagnosis"
    cmap.updated_at = _now_iso()
    return cmap


def update_from_prerequisites(
    cmap: ConfusionMap,
    prerequisite_checks: list[dict],
) -> ConfusionMap:
    """Update prerequisite nodes from self-report.

    Each dict: {"concept_id": str, "self_reported": str}
    where self_reported is "known", "unsure", or "never_seen".
    """
    report_by_id = {p["concept_id"]: p["self_reported"] for p in prerequisite_checks}
    for node in cmap.prerequisite_nodes:
        if node.concept_id in report_by_id:
            node.self_reported = report_by_id[node.concept_id]

    cmap.last_updated_step = "prerequisites"
    cmap.updated_at = _now_iso()
    return cmap


def update_from_self_explanation(
    cmap: ConfusionMap,
    rep_type: str,
    evaluation: EvaluationOutput,
) -> ConfusionMap:
    """Update confusion map after self-explanation evaluation.

    Adds evidence snippets for failed evaluations and misconception tags.
    """
    for tag in evaluation.misconception_tags:
        if tag not in cmap.misconception_tags:
            cmap.misconception_tags.append(tag)

    if not evaluation.passed and evaluation.missing_elements:
        cmap.evidence_snippets.append(
            EvidenceSnippet(
                step="self_explanation",
                task_type=f"self_explain_{rep_type}",
                learner_text=", ".join(evaluation.missing_elements[:5]),
                issue=f"Missing terms in {rep_type} self-explanation",
            )
        )

    if evaluation.next_recall_trigger and evaluation.next_recall_trigger not in cmap.next_recall_triggers:
        cmap.next_recall_triggers.append(evaluation.next_recall_trigger)

    cmap.last_updated_step = "self_explanation"
    cmap.updated_at = _now_iso()
    return cmap


def update_from_mapping(
    cmap: ConfusionMap,
    result: MappingResult,
) -> ConfusionMap:
    """Update confusion map with mapping result.

    Adds mapping edge, misconception tags, evidence snippet, recall trigger.
    """
    # Determine source/target reps from task_type
    task_type = result.task_type
    if hasattr(task_type, "value"):
        task_type_str = task_type.value
    else:
        task_type_str = str(task_type)

    rep_map = {
        "formal_to_counterexample": ("formal", "counterexample"),
        "counterexample_to_formal": ("counterexample", "formal"),
        "formal_counterexample_to_proof_schema": ("formal+counterexample", "proof_schema"),
    }
    from_rep, to_rep = rep_map.get(task_type_str, ("unknown", "unknown"))

    # Check if edge already exists (retry)
    existing = next(
        (e for e in cmap.mapping_edges if e.task_type == task_type_str),
        None,
    )
    if existing:
        existing.passed = result.passed
        existing.score = result.score
        existing.attempt_count += 1
    else:
        cmap.mapping_edges.append(
            MappingEdge(
                from_rep=from_rep,
                to_rep=to_rep,
                task_type=task_type_str,
                passed=result.passed,
                score=result.score,
            )
        )

    # Misconception tags
    for tag in result.misconception_tags:
        if tag not in cmap.misconception_tags:
            cmap.misconception_tags.append(tag)

    # Evidence snippet for failures
    if not result.passed:
        cmap.evidence_snippets.append(
            EvidenceSnippet(
                step="mapping",
                task_type=task_type_str,
                learner_text=result.learner_response[:200],
                issue=f"Failed {task_type_str}: {', '.join(result.missing_elements[:3]) or 'misconception detected'}",
            )
        )

    # Recall trigger
    if result.next_recall_trigger and result.next_recall_trigger not in cmap.next_recall_triggers:
        cmap.next_recall_triggers.append(result.next_recall_trigger)

    cmap.last_updated_step = "mapping"
    cmap.updated_at = _now_iso()
    return cmap


def update_from_misconceptions(
    cmap: ConfusionMap,
    misconception_results: list[dict],
) -> ConfusionMap:
    """Update confusion map after misconception quiz.

    Each dict: {"misconception_id": str, "correct": bool}
    """
    for r in misconception_results:
        mid = r["misconception_id"]
        if not r["correct"] and mid not in cmap.misconception_tags:
            cmap.misconception_tags.append(mid)

    cmap.last_updated_step = "misconceptions"
    cmap.updated_at = _now_iso()
    return cmap


def update_from_recall(
    cmap: ConfusionMap,
    recall_evaluation: EvaluationOutput,
) -> ConfusionMap:
    """Update confusion map after recall evaluation.

    Adds misconception tags and evidence from recall.
    """
    for tag in recall_evaluation.misconception_tags:
        if tag not in cmap.misconception_tags:
            cmap.misconception_tags.append(tag)

    if not recall_evaluation.passed:
        cmap.evidence_snippets.append(
            EvidenceSnippet(
                step="recall",
                task_type=None,
                learner_text=", ".join(recall_evaluation.missing_elements[:5]) or "insufficient recall",
                issue="Recall did not meet threshold",
            )
        )

    cmap.last_updated_step = "recall"
    cmap.updated_at = _now_iso()
    return cmap


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_confusion_map(cmap: ConfusionMap, session_dir: Path) -> None:
    """Write confusion_map.json to the session directory."""
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / _CONFUSION_MAP_FILENAME
    path.write_text(cmap.model_dump_json(indent=2), encoding="utf-8")


def load_confusion_map(session_dir: Path) -> ConfusionMap | None:
    """Load confusion map from disk, or None if not yet created."""
    path = session_dir / _CONFUSION_MAP_FILENAME
    if not path.exists():
        return None
    return ConfusionMap.model_validate_json(path.read_text(encoding="utf-8"))

"""
MVP3.1 visualization artifact generator.

Reads StudySession + list[AttemptResult] and writes visualization-ready
JSON + Mermaid files under viz_dir/.

No LLM calls, no grading recomputation, no STUDY.md parsing.
Uses only stdlib (json, datetime.date, pathlib).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from gonghaebun.models.session_models import MasteryUpdate, StudySession
from gonghaebun.study_loop.mastery import AttemptResult, aggregate_by_rep, question_type_to_rep

# Mastery ordering: lower index = weaker
_MASTERY_ORDER = ["unknown", "partial", "solid"]


def _mastery_rank(level: str) -> int:
    """Return ordinal rank for a mastery level string (lower = weaker)."""
    try:
        return _MASTERY_ORDER.index(level)
    except ValueError:
        return 0


def _overall_mastery(mastery_updates: list[MasteryUpdate]) -> str | None:
    """
    Return the weakest mastery level across all updates.
    Returns None when there are no updates.
    """
    if not mastery_updates:
        return None
    return min((u.after for u in mastery_updates), key=_mastery_rank)


def _weakest_links(mastery_updates: list[MasteryUpdate]) -> list[str]:
    """
    Return all representation types whose 'after' mastery equals the minimum
    mastery level seen in this session.  Returns [] if all are solid.
    """
    if not mastery_updates:
        return []
    min_rank = min(_mastery_rank(u.after) for u in mastery_updates)
    if _MASTERY_ORDER[min_rank] == "solid":
        return []
    return [u.representation_type for u in mastery_updates if _mastery_rank(u.after) == min_rank]


def _weakest_update(
    mastery_updates: list[MasteryUpdate],
    rep_accuracy: dict[str, float],
) -> MasteryUpdate | None:
    """
    Return the MasteryUpdate with the worst 'after' mastery.
    Tie-broken by lowest accuracy_score.
    """
    if not mastery_updates:
        return None
    return min(
        mastery_updates,
        key=lambda u: (_mastery_rank(u.after), rep_accuracy.get(u.representation_type, 0.0)),
    )


def _due_status(next_review_date: str, today: date) -> str:
    review = date.fromisoformat(next_review_date)
    if review < today:
        return "overdue"
    if review == today:
        return "due_today"
    return "upcoming"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_visualization_artifacts(
    session: StudySession,
    attempt_results: list[AttemptResult],
    viz_dir: Path,
    today: date | None = None,
) -> None:
    """
    Write 5 visualization artifacts to viz_dir/:
      mastery_map.json
      recall_feedback.json
      review_queue.json
      mastery_map.mmd
      session_flow.mmd

    Parameters
    ----------
    session        : StudySession produced by build_study_session()
    attempt_results: list[AttemptResult] from run_white_recall_session()
    viz_dir        : output directory (created if missing)
    today          : override for date.today() — use in tests for determinism
    """
    viz_dir.mkdir(parents=True, exist_ok=True)
    if today is None:
        today = date.today()

    rep_accuracy = aggregate_by_rep(attempt_results)

    _write_mastery_map(session, rep_accuracy, viz_dir)
    _write_recall_feedback(attempt_results, viz_dir)
    _write_review_queue(session, rep_accuracy, today, viz_dir)
    _write_mastery_map_mmd(session, viz_dir)
    _write_session_flow_mmd(session, attempt_results, viz_dir)


# ---------------------------------------------------------------------------
# Artifact builders
# ---------------------------------------------------------------------------


def _write_mastery_map(
    session: StudySession,
    rep_accuracy: dict[str, float],
    viz_dir: Path,
) -> None:
    concept_id = session.concept_ids[0] if session.concept_ids else ""
    updates = [u for u in session.mastery_updates if u.concept_id == concept_id]

    representations = [
        {
            "type": u.representation_type,
            "before": u.before,
            "after": u.after,
            "accuracy_score": rep_accuracy.get(u.representation_type),
        }
        for u in updates
    ]

    data = {
        "concept_id": concept_id,
        "overall_mastery": _overall_mastery(updates),
        "representations": representations,
        "weakest_links": _weakest_links(updates),
    }
    _write_json(viz_dir / "mastery_map.json", data)


def _write_recall_feedback(
    attempt_results: list[AttemptResult],
    viz_dir: Path,
) -> None:
    data = [
        {
            "question_id": ar.question.question_id,
            "representation_type": question_type_to_rep(ar.question.question_type),
            "learner_response": ar.learner_response,
            "accuracy_score": ar.grading.accuracy_score,
            "missing_elements": ar.grading.missing_elements,
            "errors": ar.grading.errors,
            "feedback": ar.grading.feedback,
            "needs_human_review": ar.grading.needs_human_review,
        }
        for ar in attempt_results
    ]
    _write_json(viz_dir / "recall_feedback.json", data)


def _write_review_queue(
    session: StudySession,
    rep_accuracy: dict[str, float],
    today: date,
    viz_dir: Path,
) -> None:
    entries = []
    for concept_id in session.concept_ids:
        updates = [u for u in session.mastery_updates if u.concept_id == concept_id]
        weakest = _weakest_update(updates, rep_accuracy)
        if weakest is None:
            entries.append({
                "concept_id": concept_id,
                "next_review_date": None,
                "weakest_representation": None,
                "due_status": None,
            })
        else:
            entries.append({
                "concept_id": concept_id,
                "next_review_date": weakest.next_review_date,
                "weakest_representation": weakest.representation_type,
                "due_status": _due_status(weakest.next_review_date, today),
            })
    _write_json(viz_dir / "review_queue.json", entries)


def _write_mastery_map_mmd(session: StudySession, viz_dir: Path) -> None:
    concept_id = session.concept_ids[0] if session.concept_ids else "concept"
    lines = ["flowchart TD"]
    # Sanitise concept_id for use as a Mermaid node ID (alphanumeric + underscore)
    node_id = concept_id.replace("-", "_").replace(" ", "_")
    lines.append(f'    {node_id}["{concept_id}"]')
    for u in session.mastery_updates:
        rep_node = f"{node_id}_{u.representation_type}"
        label = f"{u.representation_type} - {u.after}"
        lines.append(f'    {rep_node}["{label}"]')
        lines.append(f"    {node_id} --> {rep_node}")
    (viz_dir / "mastery_map.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_session_flow_mmd(
    session: StudySession,
    attempt_results: list[AttemptResult],
    viz_dir: Path,
) -> None:
    n_attempts = len(attempt_results)
    # Derive a summary mastery label from mastery_updates
    if session.mastery_updates:
        first = session.mastery_updates[0]
        mastery_label = f"{first.representation_type}: {first.after}"
    else:
        mastery_label = "no updates"
    review_date = (
        session.mastery_updates[0].next_review_date if session.mastery_updates else "none"
    )
    grader = session.llm_backend or "unknown"

    lines = [
        "flowchart LR",
        f'    Q["accepted_questions ({n_attempts})"] --> A["recall_attempts ({n_attempts})"]',
        f'    A["recall_attempts ({n_attempts})"] --> G["grading ({grader})"]',
        f'    G["grading ({grader})"] --> M["mastery_update ({mastery_label})"]',
        f'    M["mastery_update ({mastery_label})"] --> S["STUDY.md (updated)"]',
        f'    S["STUDY.md (updated)"] --> D["review_due ({review_date})"]',
    ]
    (viz_dir / "session_flow.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

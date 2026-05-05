"""
Session writer for MVP3 White Recall sessions.

Converts AttemptResults into a StudySession, writes all session artifacts,
and updates STUDY.md via apply_patch().

Artifacts written per session (under runs/{session_id}/):
  session.json              — StudySession fields (serialised)
  recall_attempts.json      — list of {question_id, learner_response, grading}
  grading_results.json      — list of GradingResult dicts
  llm_traces.jsonl          — one JSON line per {question_id, raw_response}
                              (only when grader_type="llm")
  STUDY.patch.md            — from generate_patch(session)
  session_summary.md        — human-readable summary
  visualization/            — MVP3.1 visualization-ready artifacts
    mastery_map.json        — per-concept mastery state + accuracy per rep
    recall_feedback.json    — per-question grading with needs_human_review
    review_queue.json       — next review date + due_status per concept
    mastery_map.mmd         — Mermaid flowchart: concept → rep nodes
    session_flow.mmd        — Mermaid flowchart: session pipeline
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.models.session_models import (
    MasteryUpdate,
    RecallAttempt,
    RecallEvaluation,
    StudySession,
)
from gonghaebun.study_loop.mastery import AttemptResult, aggregate_by_rep, question_type_to_rep
from gonghaebun.study_md.writer import (
    apply_patch,
    compute_mastery_state,
    compute_next_review_date,
    generate_patch,
)
from gonghaebun.visualization.session_visualizer import write_visualization_artifacts


def build_study_session(
    session_id: str,
    concept_id: str,
    source_path: str,
    attempt_results: list[AttemptResult],
    started_at: str,
    ended_at: str,
    grader_type: str = "self",
) -> StudySession:
    """
    Build a StudySession from a list of AttemptResults.

    - Groups attempts by representation_type, averages accuracy_score per group.
    - Derives MasteryLevel and next_review_date per representation_type.
    - Builds RecallAttempt + RecallEvaluation per individual attempt.
    - Builds MasteryUpdate per representation_type.

    Parameters
    ----------
    session_id     : UUID string for the session
    concept_id     : concept key that will be written to STUDY.md
    source_path    : path to the source file (for session.source_path)
    attempt_results: list of AttemptResult from run_white_recall_session
    started_at     : ISO 8601 timestamp when the session started
    ended_at       : ISO 8601 timestamp when the session ended
    grader_type    : "self" | "llm" | "mock" — stored in session metadata

    Returns
    -------
    StudySession with mastery_updates and recall_attempts populated.
    """
    # Aggregate accuracy per representation type
    rep_accuracy = aggregate_by_rep(attempt_results)

    # Build MasteryUpdates (one per representation_type seen in this session)
    mastery_updates: list[MasteryUpdate] = []
    for rep_type, avg_accuracy in rep_accuracy.items():
        after_mastery = compute_mastery_state(avg_accuracy)
        next_review = compute_next_review_date(after_mastery)
        mastery_updates.append(MasteryUpdate(
            concept_id=concept_id,
            representation_type=rep_type,  # type: ignore[arg-type]
            before="unknown",              # no prior state in MVP3 (no DB)
            after=after_mastery,
            next_review_date=next_review,
        ))

    # Build RecallAttempts (one per individual attempt)
    recall_attempts: list[RecallAttempt] = []
    for ar in attempt_results:
        rep_type = question_type_to_rep(ar.question.question_type)
        evaluation = RecallEvaluation(
            accuracy_score=ar.grading.accuracy_score,
            missing_elements=ar.grading.missing_elements,
            errors=ar.grading.errors,
            feedback=ar.grading.feedback,
        )
        recall_attempts.append(RecallAttempt(
            session_id=session_id,
            concept_id=concept_id,
            representation_type=rep_type,  # type: ignore[arg-type]
            learner_response=ar.learner_response,
            evaluation=evaluation,
            attempted_at=ended_at,
        ))

    return StudySession(
        session_id=session_id,
        session_type="review",
        concept_ids=[concept_id],
        started_at=started_at,
        ended_at=ended_at,
        llm_backend=grader_type,
        source_path=source_path,
        mastery_updates=mastery_updates,
        recall_attempts=recall_attempts,
    )


def write_session_artifacts(
    session: StudySession,
    attempt_results: list[AttemptResult],
    runs_dir: Path,
    study_md_path: Path,
    grader_type: str = "self",
    grader: object = None,
) -> Path:
    """
    Write all session artifacts and update STUDY.md.

    Creates runs_dir/session_id/ and writes:
      session.json
      recall_attempts.json
      grading_results.json
      llm_traces.jsonl    (only if grader_type == "llm")
      STUDY.patch.md
      session_summary.md

    Then calls apply_patch(study_md_path, session) to update STUDY.md.

    Returns the output directory path.
    """
    output_dir = runs_dir / session.session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # session.json
    session_dict = dataclasses.asdict(session)
    _write_json(output_dir / "session.json", session_dict)

    # recall_attempts.json
    attempts_data = [
        {
            "question_id": ar.question.question_id,
            "question_type": ar.question.question_type,
            "learner_response": ar.learner_response,
            "grading": {
                "accuracy_score": ar.grading.accuracy_score,
                "missing_elements": ar.grading.missing_elements,
                "errors": ar.grading.errors,
                "feedback": ar.grading.feedback,
                "mastery_suggestion": ar.grading.mastery_suggestion,
                "confidence": ar.grading.confidence,
                "needs_human_review": ar.grading.needs_human_review,
                "evidence_alignment": ar.grading.evidence_alignment,
            },
        }
        for ar in attempt_results
    ]
    _write_json(output_dir / "recall_attempts.json", attempts_data)

    # grading_results.json
    grading_data = [
        {
            "question_id": ar.question.question_id,
            "accuracy_score": ar.grading.accuracy_score,
            "missing_elements": ar.grading.missing_elements,
            "errors": ar.grading.errors,
            "feedback": ar.grading.feedback,
            "mastery_suggestion": ar.grading.mastery_suggestion,
            "confidence": ar.grading.confidence,
            "needs_human_review": ar.grading.needs_human_review,
            "evidence_alignment": ar.grading.evidence_alignment,
            "raw_response": ar.grading.raw_response,
        }
        for ar in attempt_results
    ]
    _write_json(output_dir / "grading_results.json", grading_data)

    # llm_traces/ — per-question JSON files; only when grader_type is "llm"
    if grader_type == "llm":
        from gonghaebun.grading.trace_models import write_trace_artifacts
        traces_dir = output_dir / "llm_traces"
        traces = getattr(grader, "traces", [])
        write_trace_artifacts(traces, traces_dir)

    # STUDY.patch.md
    patch_text = generate_patch(session)
    (output_dir / "STUDY.patch.md").write_text(patch_text, encoding="utf-8")

    # session_summary.md
    summary = _build_summary(session, attempt_results)
    (output_dir / "session_summary.md").write_text(summary, encoding="utf-8")

    # Update STUDY.md (backs up to .bak and validates after write)
    apply_patch(study_md_path, session)

    # Write visualization artifacts (MVP3.1)
    write_visualization_artifacts(session, attempt_results, output_dir / "visualization")

    return output_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_summary(session: StudySession, attempt_results: list[AttemptResult]) -> str:
    from datetime import timezone as tz

    lines = [
        f"# Session Summary — {session.session_id}",
        f"_Concept: {', '.join(session.concept_ids)}_",
        f"_Date: {session.ended_at or session.started_at}_",
        "",
        f"Questions answered: {len(attempt_results)}",
        "",
    ]

    if session.mastery_updates:
        lines += [
            "## Mastery Changes",
            "",
            "| representation | after | next_review |",
            "|----------------|-------|-------------|",
        ]
        for u in session.mastery_updates:
            lines.append(f"| {u.representation_type} | {u.after} | {u.next_review_date} |")
        lines.append("")

    if attempt_results:
        lines += ["## Answer Attempts", ""]
        for ar in attempt_results:
            score_pct = int(ar.grading.accuracy_score * 100)
            lines.append(
                f"- **{ar.question.question_id}** ({ar.question.question_type}): "
                f"{score_pct}% — {ar.grading.mastery_suggestion}"
            )
        lines.append("")

    return "\n".join(lines)

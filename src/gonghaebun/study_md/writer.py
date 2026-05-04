"""
Stage 7: STUDY.md Writer (pure Python, no LLM).

Responsibilities:
- compute_mastery_state(accuracy_score) → MasteryLevel
- compute_next_review_date(mastery) → YYYY-MM-DD string
- generate_patch(session) → STUDY.patch.md string
- apply_patch(study_md_path, session) → writes/updates STUDY.md
"""
from __future__ import annotations
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path

from gonghaebun.models.concept import MasteryLevel
from gonghaebun.models.session_models import StudySession
from gonghaebun.study_md.parser import parse_study_md, ConceptRecord


def compute_mastery_state(accuracy_score: float) -> MasteryLevel:
    if accuracy_score >= 0.85:
        return "solid"
    if accuracy_score >= 0.50:
        return "partial"
    return "unknown"


def compute_next_review_date(mastery: MasteryLevel) -> str:
    offsets: dict[str, int] = {"solid": 7, "partial": 3, "unknown": 1}
    d = date.today() + timedelta(days=offsets[mastery])
    return d.isoformat()


def generate_patch(session: StudySession) -> str:
    """Return the content of STUDY.patch.md for the given session."""
    lines = [
        f"# STUDY.md Patch — Session {session.session_id}",
        f"_Generated: {session.ended_at or 'in progress'}_",
        "",
    ]

    if session.mastery_updates:
        lines.append("## Representation Mastery Updates")
        lines.append("")
        lines.append("| concept | representation | before | after | next_review |")
        lines.append("|---------|---------------|--------|-------|-------------|")
        for u in session.mastery_updates:
            lines.append(
                f"| {u.concept_id} | {u.representation_type} "
                f"| {u.before} | {u.after} | {u.next_review_date} |"
            )
        lines.append("")

    if session.recall_attempts:
        lines.append("## Recall Attempt Summary")
        lines.append("")
        for attempt in session.recall_attempts:
            score_pct = int(attempt.evaluation.accuracy_score * 100)
            lines.append(f"- **{attempt.representation_type}**: {score_pct}% accuracy")
            if attempt.evaluation.errors:
                for err in attempt.evaluation.errors:
                    lines.append(f"  - Error: {err}")
            if attempt.evaluation.missing_elements:
                for miss in attempt.evaluation.missing_elements:
                    lines.append(f"  - Missing: {miss}")
        lines.append("")

    lines.append("## Source Grounding")
    lines.append("")
    lines.append(f"- Source hash: `{session.source_hash}`")
    lines.append(f"- Grounding mode: {session.grounding_mode}")
    lines.append("")

    return "\n".join(lines)


def apply_patch(study_md_path: Path, session: StudySession) -> None:
    """
    Write or update STUDY.md with session results.
    Backs up existing file to STUDY.md.bak before writing.
    Creates parent directories if needed.
    """
    study_md_path.parent.mkdir(parents=True, exist_ok=True)

    # Back up existing file
    if study_md_path.exists():
        shutil.copy2(study_md_path, study_md_path.with_suffix(".bak"))

    existing = parse_study_md(study_md_path)

    for concept_id in session.concept_ids:
        if concept_id not in existing:
            existing[concept_id] = ConceptRecord(concept_id=concept_id)
        _update_record(existing[concept_id], session)

    _write_study_md(study_md_path, existing)
    validate_study_md(study_md_path)


def validate_study_md(path: Path) -> None:
    """
    Parse the written STUDY.md and raise ValueError if it contains no concept records.

    Called automatically by apply_patch() after every write to catch corruption.
    """
    records = parse_study_md(path)
    if not records:
        raise ValueError(
            f"STUDY.md validation failed: no concept records were parsed from {path}. "
            "The file may be corrupt or empty."
        )


def _update_record(record: ConceptRecord, session: StudySession) -> None:
    today = date.today().isoformat()
    # Build mastery map from recall attempts
    mastery_map: dict[str, str] = {}
    for attempt in session.recall_attempts:
        if attempt.concept_id == record.concept_id:
            new_mastery = compute_mastery_state(attempt.evaluation.accuracy_score)
            mastery_map[attempt.representation_type] = new_mastery

    # Update representation records
    existing_types = {r.type: r for r in record.representations}
    for rep_type in ["formal", "intuitive", "visual", "counterexample", "proof_schema"]:
        if rep_type in existing_types:
            if rep_type in mastery_map:
                existing_types[rep_type].mastery = mastery_map[rep_type]
                existing_types[rep_type].last_reviewed = today
        else:
            from gonghaebun.study_md.parser import RepresentationRecord
            mastery = mastery_map.get(rep_type, "unknown")
            last = today if rep_type in mastery_map else None
            record.representations.append(RepresentationRecord(rep_type, mastery, last))

    # Recompute overall mastery (weakest link)
    all_masteries = [r.mastery for r in record.representations]
    if all_masteries:
        if "unknown" in all_masteries:
            record.overall_mastery = "unknown"
        elif "partial" in all_masteries:
            record.overall_mastery = "partial"
        else:
            record.overall_mastery = "solid"

    # Next review date from mastery updates
    for u in session.mastery_updates:
        if u.concept_id == record.concept_id:
            record.next_review = u.next_review_date
            break
    if not record.next_review:
        record.next_review = compute_next_review_date(record.overall_mastery)  # type: ignore[arg-type]


def _write_study_md(path: Path, records: dict[str, ConceptRecord]) -> None:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()

    lines = [
        "# STUDY.md",
        f"_last_updated: {today}_",
        "",
    ]

    for concept_id, record in records.items():
        lines += [
            "---",
            "",
            f"## {concept_id}",
            "",
            f"**domain**: {record.domain}",
            f"**overall_mastery**: {record.overall_mastery}",
            f"**next_review**: {record.next_review or '—'}",
            "",
            "### Representations",
            "",
            "| type           | mastery | last_reviewed |",
            "|----------------|---------|---------------|",
        ]
        for rep in record.representations:
            last = rep.last_reviewed or "—"
            lines.append(f"| {rep.type:<14} | {rep.mastery:<7} | {last:<13} |")

        lines += [
            "",
            "### Prerequisites",
            "",
            "| concept        | mastery | note |",
            "|----------------|---------|------|",
        ]
        for prereq in record.prerequisites:
            note = prereq.note or ""
            lines.append(f"| {prereq.concept:<14} | {prereq.mastery:<7} | {note} |")

        lines += [
            "",
            "### Misconceptions Encountered",
            "",
        ]
        for misc in record.misconceptions:
            check = "x" if misc.confirmed else " "
            lines.append(f"- [{check}] {misc.claim}")

        if record.notes:
            lines += ["", "### Notes", "", f"> {record.notes}"]

        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")

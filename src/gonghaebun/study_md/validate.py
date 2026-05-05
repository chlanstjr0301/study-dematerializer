"""
STUDY.md canonical-state validator.

Checks structural invariants and provides auto-repair for fixable violations.
Can be used as a library or run as a CLI:

    python -m gonghaebun.study_md.validate [STUDY_MD_PATH] [--repair-dry-run] [--repair]
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from gonghaebun.study_md.parser import parse_study_md

VALID_MASTERY: frozenset[str] = frozenset({"unknown", "partial", "solid"})
VALID_REP_TYPES: frozenset[str] = frozenset(
    {"formal", "intuitive", "visual", "counterexample", "proof_schema"}
)

_MASTERY_RANK = {"unknown": 0, "partial": 1, "solid": 2}


@dataclass
class Violation:
    code: str                   # E001, W001, etc.
    concept_id: str | None      # None = file-level violation (e.g. E005)
    field: str | None           # "overall_mastery", "rep[formal].mastery", etc.
    message: str


@dataclass
class ValidationReport:
    valid: bool                 # True iff no errors (warnings don't affect validity)
    errors: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)


def _weakest_mastery(masteries: list[str]) -> str:
    """Return weakest mastery level from a list (unknown < partial < solid)."""
    return min(masteries, key=lambda m: _MASTERY_RANK.get(m, 0))


def _try_parse_date(value: str) -> bool:
    """Return True if value is a valid ISO date string."""
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _scan_duplicate_concepts(text: str) -> list[str]:
    """Return concept_ids that appear more than once as ## headers."""
    counts: dict[str, int] = {}
    for m in re.finditer(r"^## (.+)$", text, re.MULTILINE):
        cid = m.group(1).strip()
        counts[cid] = counts.get(cid, 0) + 1
    return [cid for cid, n in counts.items() if n > 1]


def validate_study_md_full(
    study_md_path: Path,
    today: date | None = None,
) -> ValidationReport:
    """
    Parse STUDY.md and check all canonical invariants.

    Returns a ValidationReport with errors (hard violations) and warnings (informational).
    Returns valid=True with empty lists if the file does not exist.
    """
    if not study_md_path.exists():
        return ValidationReport(valid=True)

    today = today or date.today()
    errors: list[Violation] = []
    warnings: list[Violation] = []

    # Read raw text for E005 duplicate detection
    raw_text = study_md_path.read_text(encoding="utf-8")
    duplicates = _scan_duplicate_concepts(raw_text)
    for dup in duplicates:
        errors.append(Violation(
            code="E005",
            concept_id=dup,
            field=None,
            message=f'Concept "{dup}" appears more than once in STUDY.md',
        ))

    # Parse structured records
    records = parse_study_md(study_md_path)

    # Import CONCEPTS for W002 prerequisite resolvability
    try:
        from gonghaebun.knowledge.real_analysis import CONCEPTS as KB_CONCEPTS
        kb_keys: frozenset[str] = frozenset(KB_CONCEPTS.keys())
    except ImportError:
        kb_keys = frozenset()

    for concept_id, record in records.items():

        # E001: invalid overall_mastery
        if record.overall_mastery not in VALID_MASTERY:
            errors.append(Violation(
                code="E001",
                concept_id=concept_id,
                field="overall_mastery",
                message=(
                    f'overall_mastery="{record.overall_mastery}" is not a valid mastery level '
                    f"(expected: unknown | partial | solid)"
                ),
            ))

        # E003: malformed next_review date
        if record.next_review and record.next_review != "—":
            if not _try_parse_date(record.next_review):
                errors.append(Violation(
                    code="E003",
                    concept_id=concept_id,
                    field="next_review",
                    message=f'next_review="{record.next_review}" is not a valid ISO date (YYYY-MM-DD)',
                ))

        for rep in record.representations:
            # E001: invalid representation mastery
            if rep.mastery not in VALID_MASTERY:
                errors.append(Violation(
                    code="E001",
                    concept_id=concept_id,
                    field=f"rep[{rep.type}].mastery",
                    message=(
                        f'rep[{rep.type}].mastery="{rep.mastery}" is not a valid mastery level '
                        f"(expected: unknown | partial | solid)"
                    ),
                ))

            # E002: invalid representation type
            if rep.type not in VALID_REP_TYPES:
                errors.append(Violation(
                    code="E002",
                    concept_id=concept_id,
                    field=f"rep[{rep.type}].type",
                    message=(
                        f'Representation type "{rep.type}" is not valid '
                        f"(expected: formal | intuitive | visual | counterexample | proof_schema)"
                    ),
                ))

            # E003: malformed last_reviewed date
            if rep.last_reviewed and rep.last_reviewed != "—":
                if not _try_parse_date(rep.last_reviewed):
                    errors.append(Violation(
                        code="E003",
                        concept_id=concept_id,
                        field=f"rep[{rep.type}].last_reviewed",
                        message=(
                            f'rep[{rep.type}].last_reviewed="{rep.last_reviewed}" '
                            f"is not a valid ISO date (YYYY-MM-DD)"
                        ),
                    ))

        # E004: overall_mastery drift (only check if overall_mastery is itself valid)
        if record.overall_mastery in VALID_MASTERY and record.representations:
            valid_masteries = [
                r.mastery for r in record.representations if r.mastery in VALID_MASTERY
            ]
            if valid_masteries:
                computed = _weakest_mastery(valid_masteries)
                if computed != record.overall_mastery:
                    errors.append(Violation(
                        code="E004",
                        concept_id=concept_id,
                        field="overall_mastery",
                        message=(
                            f'Recorded overall_mastery="{record.overall_mastery}" but '
                            f'computed weakest-link is "{computed}"'
                        ),
                    ))

        # W001: no representations
        if not record.representations:
            warnings.append(Violation(
                code="W001",
                concept_id=concept_id,
                field="representations",
                message="Concept has no representation rows — expected 5 (formal, intuitive, visual, counterexample, proof_schema)",
            ))

        # W002: prerequisite not resolvable
        for prereq in record.prerequisites:
            cid = prereq.concept
            if cid not in records and cid not in kb_keys:
                warnings.append(Violation(
                    code="W002",
                    concept_id=concept_id,
                    field=f"prerequisites[{cid}]",
                    message=(
                        f'Prerequisite "{cid}" is not in STUDY.md or the knowledge base — '
                        f"may be an external stub or typo"
                    ),
                ))

        # W003: next_review inconsistent (has reps but no schedule)
        # Treat None, "—", and empty string all as "not set"
        next_review_absent = not record.next_review or record.next_review in ("—", "")
        if record.representations and next_review_absent:
            warnings.append(Violation(
                code="W003",
                concept_id=concept_id,
                field="next_review",
                message="Concept has representations but next_review is not set",
            ))

    return ValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def repair_study_md(study_md_path: Path, dry_run: bool = True) -> list[str]:
    """
    Auto-repair fixable violations in STUDY.md.

    Fixes:
    - E004 overall_mastery_drift: recompute from weakest-link of representations
    - W003 next_review_inconsistent: compute next_review from overall_mastery

    Args:
        study_md_path: Path to STUDY.md
        dry_run: If True, return change descriptions without writing. If False, write the
                 repaired file (after backing up) and return applied changes.

    Returns:
        List of human-readable change descriptions (empty = nothing to fix).
    """
    from gonghaebun.study_md.writer import (
        _write_study_md,      # type: ignore[attr-defined]
        compute_next_review_date,
    )

    if not study_md_path.exists():
        return []

    records = parse_study_md(study_md_path)
    changes: list[str] = []

    for concept_id, record in records.items():
        # E004: recompute overall_mastery
        if record.representations:
            valid_masteries = [
                r.mastery for r in record.representations if r.mastery in VALID_MASTERY
            ]
            if valid_masteries:
                computed = _weakest_mastery(valid_masteries)
                if computed != record.overall_mastery:
                    changes.append(
                        f'[E004] {concept_id}: overall_mastery '
                        f'"{record.overall_mastery}" → "{computed}"'
                    )
                    if not dry_run:
                        record.overall_mastery = computed  # type: ignore[assignment]

        # W003: set next_review if missing (treat "—" and "" as absent)
        next_review_absent = not record.next_review or record.next_review in ("—", "")
        if record.representations and next_review_absent:
            mastery = record.overall_mastery
            if mastery in VALID_MASTERY:
                new_date = compute_next_review_date(mastery)  # type: ignore[arg-type]
                changes.append(
                    f"[W003] {concept_id}: next_review None → {new_date} "
                    f"(derived from overall_mastery={mastery})"
                )
                if not dry_run:
                    record.next_review = new_date

    if not dry_run and changes:
        shutil.copy2(study_md_path, study_md_path.with_suffix(".bak"))
        _write_study_md(study_md_path, records)

    return changes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m gonghaebun.study_md.validate",
        description="Validate (and optionally repair) STUDY.md canonical state.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to STUDY.md (default: GONGHAEBUN_STUDY_MD env var or data/gonghaebun/default/STUDY.md)",
    )
    parser.add_argument(
        "--repair-dry-run",
        action="store_true",
        help="Show what auto-repair would change without writing",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Apply auto-repair (E004, W003); backs up file first",
    )
    args = parser.parse_args()

    if args.repair and args.repair_dry_run:
        print("Error: --repair and --repair-dry-run are mutually exclusive.", file=sys.stderr)
        sys.exit(2)

    study_md_path = Path(
        args.path
        or os.getenv("GONGHAEBUN_STUDY_MD", "data/gonghaebun/default/STUDY.md")
    )

    if args.repair_dry_run or args.repair:
        action = "DRY RUN" if args.repair_dry_run else "REPAIR"
        print(f"STUDY.md Auto-Repair ({action})")
        print("=" * 40)
        print(f"Path: {study_md_path}")
        changes = repair_study_md(study_md_path, dry_run=args.repair_dry_run)
        if not changes:
            print("No auto-repairable violations found.")
        else:
            print(f"\n{len(changes)} change(s):")
            for c in changes:
                print(f"  {c}")
            if not args.repair_dry_run:
                print(f"\nRepaired. Backup: {study_md_path.with_suffix('.bak')}")
        sys.exit(0)

    # Default: validate and report
    report = validate_study_md_full(study_md_path)

    print("STUDY.md Validation Report")
    print("=" * 40)
    print(f"Path : {study_md_path}")
    status = "OK" if report.valid else "ERRORS FOUND"
    print(f"Valid: {status}  ({len(report.errors)} errors, {len(report.warnings)} warnings)")

    if report.errors:
        print("\nERRORS:")
        for v in report.errors:
            loc = f"{v.concept_id} · {v.field}" if v.concept_id else "(file-level)"
            print(f"  [{v.code}] {loc}")
            print(f"         {v.message}")

    if report.warnings:
        print("\nWARNINGS:")
        for v in report.warnings:
            loc = f"{v.concept_id} · {v.field}" if v.concept_id else "(file-level)"
            print(f"  [{v.code}] {loc}")
            print(f"         {v.message}")

    sys.exit(0 if report.valid else 1)

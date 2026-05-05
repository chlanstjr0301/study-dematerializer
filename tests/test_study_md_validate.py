"""
Unit tests for STUDY.md canonical-state validator (MVP4-H).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from gonghaebun.study_md.validate import (
    ValidationReport,
    Violation,
    repair_study_md,
    validate_study_md_full,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _clean_study_md(
    concept_id: str = "compactness",
    overall_mastery: str = "unknown",
    next_review: str | None = None,
    reps: list[tuple[str, str, str | None]] | None = None,
    prereqs: list[str] | None = None,
) -> str:
    """Build a syntactically valid STUDY.md string."""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    nr = next_review or tomorrow

    if reps is None:
        reps = [
            ("formal",         "unknown", None),
            ("intuitive",      "unknown", None),
            ("visual",         "unknown", None),
            ("counterexample", "unknown", None),
            ("proof_schema",   "unknown", None),
        ]

    lines = [
        "# STUDY.md",
        f"_last_updated: {today}_",
        "",
        "---",
        "",
        f"## {concept_id}",
        "",
        "**domain**: real_analysis",
        f"**overall_mastery**: {overall_mastery}",
        f"**next_review**: {nr}",
        "",
        "### Representations",
        "",
        "| type           | mastery | last_reviewed |",
        "|----------------|---------|---------------|",
    ]
    for rtype, mastery, last in reps:
        lines.append(f"| {rtype:<14} | {mastery:<7} | {last or '—':<13} |")

    lines += [
        "",
        "### Prerequisites",
        "",
        "| concept        | mastery | note |",
        "|----------------|---------|------|",
    ]
    for cid in (prereqs or []):
        lines.append(f"| {cid:<14} | unknown |      |")

    lines += [
        "",
        "### Misconceptions Encountered",
        "",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Error detection tests
# ---------------------------------------------------------------------------

class TestErrors:
    def test_valid_study_md_returns_valid_true(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md())
        report = validate_study_md_full(p)
        assert report.valid is True
        assert report.errors == []

    def test_detects_invalid_mastery_level_on_rep(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(reps=[("formal", "strong", None)]))
        report = validate_study_md_full(p)
        assert any(v.code == "E001" for v in report.errors)

    def test_detects_invalid_overall_mastery(self, tmp_path):
        p = tmp_path / "STUDY.md"
        content = _clean_study_md().replace(
            "**overall_mastery**: unknown", "**overall_mastery**: great"
        )
        _write(p, content)
        report = validate_study_md_full(p)
        assert any(v.code == "E001" for v in report.errors)

    def test_detects_invalid_rep_type(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(reps=[("verbal", "unknown", None)]))
        report = validate_study_md_full(p)
        assert any(v.code == "E002" for v in report.errors)

    def test_detects_malformed_last_reviewed(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(reps=[("formal", "unknown", "not-a-date")]))
        report = validate_study_md_full(p)
        assert any(v.code == "E003" for v in report.errors)

    def test_detects_malformed_next_review(self, tmp_path):
        p = tmp_path / "STUDY.md"
        content = _clean_study_md().replace(
            "**next_review**:", "**next_review**: 2026/05/05\n_ignore_: "
        )
        # Build more directly
        p2 = tmp_path / "STUDY2.md"
        raw = _clean_study_md(next_review="2026/05/05")
        _write(p2, raw)
        report = validate_study_md_full(p2)
        assert any(v.code == "E003" for v in report.errors)

    def test_detects_overall_mastery_drift(self, tmp_path):
        p = tmp_path / "STUDY.md"
        # overall_mastery says "solid" but formal rep is "unknown"
        _write(
            p,
            _clean_study_md(
                overall_mastery="solid",
                reps=[("formal", "unknown", None)],
            ),
        )
        report = validate_study_md_full(p)
        drift_errors = [v for v in report.errors if v.code == "E004"]
        assert len(drift_errors) == 1
        assert "compactness" in drift_errors[0].concept_id

    def test_detects_duplicate_concept(self, tmp_path):
        p = tmp_path / "STUDY.md"
        block = _clean_study_md()
        _write(p, block + "\n" + block)  # two ## compactness headers
        report = validate_study_md_full(p)
        assert any(v.code == "E005" for v in report.errors)

    def test_missing_file_returns_valid(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        report = validate_study_md_full(p)
        assert report.valid is True
        assert report.errors == []
        assert report.warnings == []


# ---------------------------------------------------------------------------
# Warning detection tests
# ---------------------------------------------------------------------------

class TestWarnings:
    def test_warns_no_representations(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(reps=[]))
        report = validate_study_md_full(p)
        assert any(v.code == "W001" for v in report.warnings)

    def test_warns_prerequisite_unresolvable(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(prereqs=["zz_nonexistent_concept"]))
        report = validate_study_md_full(p)
        assert any(v.code == "W002" for v in report.warnings)

    def test_warns_next_review_inconsistent(self, tmp_path):
        p = tmp_path / "STUDY.md"
        # Force next_review to be absent (use — which parser converts to None)
        content = _clean_study_md().replace(
            f"**next_review**: {(date.today() + timedelta(days=1)).isoformat()}",
            "**next_review**: —",
        )
        _write(p, content)
        report = validate_study_md_full(p)
        assert any(v.code == "W003" for v in report.warnings)

    def test_known_stub_not_flagged(self, tmp_path):
        """metric_space is in CONCEPTS knowledge base — should not trigger W002."""
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(prereqs=["metric_space"]))
        report = validate_study_md_full(p)
        w002 = [v for v in report.warnings if v.code == "W002"]
        assert all("metric_space" not in v.message for v in w002)

    def test_past_next_review_is_valid_due_state(self, tmp_path):
        """next_review in the past is a normal due-review state — no warnings."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md(next_review=yesterday))
        report = validate_study_md_full(p)
        # No warning codes for stale next_review
        stale_warnings = [v for v in report.warnings if "stale" in v.message.lower()]
        assert stale_warnings == []
        # And specifically no W003 triggered by past date (W003 = None, not past)
        w003 = [v for v in report.warnings if v.code == "W003"]
        assert w003 == []


# ---------------------------------------------------------------------------
# Repair tests
# ---------------------------------------------------------------------------

class TestRepair:
    def test_repair_dry_run_returns_changes_without_writing(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(
            p,
            _clean_study_md(
                overall_mastery="solid",
                reps=[("formal", "unknown", None)],
            ),
        )
        original_mtime = p.stat().st_mtime
        changes = repair_study_md(p, dry_run=True)
        assert len(changes) > 0
        assert p.stat().st_mtime == original_mtime  # file not modified

    def test_repair_fixes_overall_mastery_drift(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(
            p,
            _clean_study_md(
                overall_mastery="solid",
                reps=[("formal", "unknown", None)],
            ),
        )
        changes = repair_study_md(p, dry_run=False)
        assert any("E004" in c for c in changes)
        # After repair, should be valid
        report = validate_study_md_full(p)
        e004 = [v for v in report.errors if v.code == "E004"]
        assert e004 == []

    def test_repair_fixes_missing_next_review(self, tmp_path):
        p = tmp_path / "STUDY.md"
        content = _clean_study_md().replace(
            f"**next_review**: {(date.today() + timedelta(days=1)).isoformat()}",
            "**next_review**: —",
        )
        _write(p, content)
        changes = repair_study_md(p, dry_run=False)
        assert any("W003" in c for c in changes)
        # After repair, next_review should be set
        report = validate_study_md_full(p)
        w003 = [v for v in report.warnings if v.code == "W003"]
        assert w003 == []

    def test_repair_creates_backup(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(
            p,
            _clean_study_md(
                overall_mastery="solid",
                reps=[("formal", "unknown", None)],
            ),
        )
        repair_study_md(p, dry_run=False)
        assert (tmp_path / "STUDY.bak").exists()

    def test_repair_dry_run_returns_empty_for_valid_file(self, tmp_path):
        p = tmp_path / "STUDY.md"
        _write(p, _clean_study_md())
        changes = repair_study_md(p, dry_run=True)
        assert changes == []

    def test_repair_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        changes = repair_study_md(p, dry_run=True)
        assert changes == []

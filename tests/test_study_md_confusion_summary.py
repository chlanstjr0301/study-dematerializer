"""
Tests for Step 12: STUDY.md Confusion Summary section (parser + writer).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from gonghaebun.study_md.parser import (
    ConfusionMappingStatus,
    ConceptRecord,
    parse_study_md,
)
from gonghaebun.study_md.writer import _write_study_md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_study_md(
    *,
    confusion_summary: str = "",
    notes: str = "",
) -> str:
    """Build a STUDY.md with optional Confusion Summary section."""
    today = date.today().isoformat()
    base = (
        f"# STUDY.md\n_last_updated: {today}_\n\n---\n\n"
        f"## compactness\n\n"
        f"**domain**: real_analysis\n"
        f"**overall_mastery**: unknown\n"
        f"**next_review**: {today}\n\n"
        f"### Representations\n\n"
        f"| type           | mastery | last_reviewed |\n"
        f"|----------------|---------|---------------|\n"
        f"| formal         | unknown | —             |\n"
        f"| counterexample | unknown | —             |\n"
        f"| proof_schema   | unknown | —             |\n\n"
        f"### Prerequisites\n\n"
        f"| concept        | mastery | note |\n"
        f"|----------------|---------|------|\n\n"
        f"### Misconceptions Encountered\n\n"
    )
    if confusion_summary:
        base += f"\n{confusion_summary}\n"
    if notes:
        base += f"\n### Notes\n\n> {notes}\n"
    return base


CONFUSION_SECTION = """\
### Confusion Summary

| mapping | status | last_session |
|---------|--------|-------------|
| formal → counterexample | failed | 2026-05-08 |
| counterexample → formal | passed | 2026-05-08 |
| formal+CE → proof_schema | failed | 2026-05-08 |

**Active misconceptions**: misuses_heine_borel, bounded_implies_compact
**Next recall trigger**: open cover로 (0,1)이 compact하지 않음을 설명하라."""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParserConfusionSummary:
    def test_parse_with_section_present(self, tmp_path):
        """Confusion Summary present → fields populated."""
        p = tmp_path / "STUDY.md"
        p.write_text(_base_study_md(confusion_summary=CONFUSION_SECTION), encoding="utf-8")
        records = parse_study_md(p)
        rec = records["compactness"]

        assert len(rec.confusion_mapping_status) == 3
        assert rec.confusion_mapping_status[0].mapping == "formal → counterexample"
        assert rec.confusion_mapping_status[0].status == "failed"
        assert rec.confusion_mapping_status[1].status == "passed"

    def test_parse_active_misconceptions(self, tmp_path):
        p = tmp_path / "STUDY.md"
        p.write_text(_base_study_md(confusion_summary=CONFUSION_SECTION), encoding="utf-8")
        rec = parse_study_md(p)["compactness"]

        assert rec.active_misconceptions == ["misuses_heine_borel", "bounded_implies_compact"]

    def test_parse_next_recall_trigger(self, tmp_path):
        p = tmp_path / "STUDY.md"
        p.write_text(_base_study_md(confusion_summary=CONFUSION_SECTION), encoding="utf-8")
        rec = parse_study_md(p)["compactness"]

        assert rec.next_recall_trigger == "open cover로 (0,1)이 compact하지 않음을 설명하라."

    def test_parse_without_section_returns_defaults(self, tmp_path):
        """Missing Confusion Summary → empty defaults."""
        p = tmp_path / "STUDY.md"
        p.write_text(_base_study_md(), encoding="utf-8")
        rec = parse_study_md(p)["compactness"]

        assert rec.confusion_mapping_status == []
        assert rec.active_misconceptions == []
        assert rec.next_recall_trigger is None

    def test_parse_with_notes_after_confusion(self, tmp_path):
        """Confusion Summary before Notes — both parsed correctly."""
        p = tmp_path / "STUDY.md"
        p.write_text(
            _base_study_md(confusion_summary=CONFUSION_SECTION, notes="Study more."),
            encoding="utf-8",
        )
        rec = parse_study_md(p)["compactness"]

        assert len(rec.confusion_mapping_status) == 3
        assert "Study more." in rec.notes


# ---------------------------------------------------------------------------
# Writer tests
# ---------------------------------------------------------------------------


class TestWriterConfusionSummary:
    def test_write_with_confusion_data(self, tmp_path):
        """Writer produces Confusion Summary when data exists."""
        rec = ConceptRecord(
            concept_id="compactness",
            next_review=date.today().isoformat(),
        )
        rec.confusion_mapping_status = [
            ConfusionMappingStatus("formal → counterexample", "failed", "2026-05-08"),
            ConfusionMappingStatus("counterexample → formal", "passed", "2026-05-08"),
        ]
        rec.active_misconceptions = ["bounded_implies_compact"]
        rec.next_recall_trigger = "finite subcover 조건을 설명하라."

        p = tmp_path / "STUDY.md"
        _write_study_md(p, {"compactness": rec})

        content = p.read_text(encoding="utf-8")
        assert "### Confusion Summary" in content
        assert "formal → counterexample" in content
        assert "failed" in content
        assert "**Active misconceptions**: bounded_implies_compact" in content
        assert "**Next recall trigger**: finite subcover 조건을 설명하라." in content

    def test_write_omits_section_when_no_data(self, tmp_path):
        """Writer omits Confusion Summary when no confusion data."""
        rec = ConceptRecord(
            concept_id="compactness",
            next_review=date.today().isoformat(),
        )
        p = tmp_path / "STUDY.md"
        _write_study_md(p, {"compactness": rec})

        content = p.read_text(encoding="utf-8")
        assert "### Confusion Summary" not in content

    def test_write_with_notes_and_confusion(self, tmp_path):
        """Confusion Summary appears before Notes."""
        rec = ConceptRecord(
            concept_id="compactness",
            next_review=date.today().isoformat(),
            notes="Important note.",
        )
        rec.confusion_mapping_status = [
            ConfusionMappingStatus("formal → counterexample", "failed", "2026-05-08"),
        ]
        rec.active_misconceptions = []
        rec.next_recall_trigger = None

        p = tmp_path / "STUDY.md"
        _write_study_md(p, {"compactness": rec})

        content = p.read_text(encoding="utf-8")
        confusion_pos = content.index("### Confusion Summary")
        notes_pos = content.index("### Notes")
        assert confusion_pos < notes_pos


# ---------------------------------------------------------------------------
# Roundtrip tests
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_write_then_parse_matches(self, tmp_path):
        """Write confusion data → parse it back → fields match."""
        rec = ConceptRecord(
            concept_id="compactness",
            next_review=date.today().isoformat(),
        )
        rec.confusion_mapping_status = [
            ConfusionMappingStatus("formal → counterexample", "failed", "2026-05-08"),
            ConfusionMappingStatus("counterexample → formal", "passed", "2026-05-08"),
            ConfusionMappingStatus("formal+CE → proof_schema", "failed", "2026-05-08"),
        ]
        rec.active_misconceptions = ["misuses_heine_borel", "bounded_implies_compact"]
        rec.next_recall_trigger = "open cover로 (0,1)이 compact하지 않음을 설명하라."

        p = tmp_path / "STUDY.md"
        _write_study_md(p, {"compactness": rec})

        parsed = parse_study_md(p)["compactness"]

        assert len(parsed.confusion_mapping_status) == 3
        assert parsed.confusion_mapping_status[0].mapping == "formal → counterexample"
        assert parsed.confusion_mapping_status[0].status == "failed"
        assert parsed.confusion_mapping_status[2].mapping == "formal+CE → proof_schema"
        assert parsed.active_misconceptions == ["misuses_heine_borel", "bounded_implies_compact"]
        assert parsed.next_recall_trigger == "open cover로 (0,1)이 compact하지 않음을 설명하라."

    def test_roundtrip_no_confusion_data(self, tmp_path):
        """Write without confusion data → parse → defaults."""
        rec = ConceptRecord(
            concept_id="compactness",
            next_review=date.today().isoformat(),
        )
        p = tmp_path / "STUDY.md"
        _write_study_md(p, {"compactness": rec})

        parsed = parse_study_md(p)["compactness"]
        assert parsed.confusion_mapping_status == []
        assert parsed.active_misconceptions == []
        assert parsed.next_recall_trigger is None


# ---------------------------------------------------------------------------
# Validator compatibility
# ---------------------------------------------------------------------------


class TestValidatorCompat:
    def test_validator_does_not_flag_confusion_summary(self, tmp_path):
        """Existing validator should not error on files with Confusion Summary."""
        from gonghaebun.study_md.validate import validate_study_md_full

        p = tmp_path / "STUDY.md"
        p.write_text(_base_study_md(confusion_summary=CONFUSION_SECTION), encoding="utf-8")

        report = validate_study_md_full(p)
        assert report.valid is True, f"Unexpected errors: {report.errors}"

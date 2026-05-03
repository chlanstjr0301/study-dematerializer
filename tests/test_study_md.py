"""Tests for gonghaebun.study_md (parser + writer)."""
from __future__ import annotations

import pytest
from pathlib import Path

from gonghaebun.study_md.parser import ConceptRecord, parse_study_md
from gonghaebun.study_md.writer import (
    compute_mastery_state,
    compute_next_review_date,
    generate_patch,
)
from gonghaebun.models.session_models import MasteryUpdate, StudySession


SAMPLE_STUDY_MD = """\
# STUDY.md
_last_updated: 2026-01-01_

---

## compactness

**domain**: real_analysis
**overall_mastery**: partial
**next_review**: 2026-01-04

### Representations

| type           | mastery | last_reviewed |
|----------------|---------|---------------|
| formal         | partial | 2026-01-01    |
| intuitive      | unknown | —             |

### Prerequisites

| concept        | mastery | note |
|----------------|---------|------|
| metric_space   | unknown |      |

### Misconceptions Encountered

- [x] compact = bounded
- [ ] closed implies compact

### Notes

> Study more carefully.

"""


class TestComputeMasteryState:
    def test_solid(self):
        assert compute_mastery_state(0.85) == "solid"
        assert compute_mastery_state(1.0) == "solid"

    def test_partial(self):
        assert compute_mastery_state(0.50) == "partial"
        assert compute_mastery_state(0.84) == "partial"

    def test_unknown(self):
        assert compute_mastery_state(0.0) == "unknown"
        assert compute_mastery_state(0.49) == "unknown"


class TestComputeNextReviewDate:
    def test_returns_iso_date_string(self):
        d = compute_next_review_date("solid")
        assert len(d) == 10
        assert d[4] == "-"

    def test_solid_7_days(self):
        from datetime import date, timedelta
        expected = (date.today() + timedelta(days=7)).isoformat()
        assert compute_next_review_date("solid") == expected

    def test_partial_3_days(self):
        from datetime import date, timedelta
        expected = (date.today() + timedelta(days=3)).isoformat()
        assert compute_next_review_date("partial") == expected

    def test_unknown_1_day(self):
        from datetime import date, timedelta
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert compute_next_review_date("unknown") == expected


class TestParseStudyMd:
    def test_empty_when_file_missing(self, tmp_path):
        result = parse_study_md(tmp_path / "nonexistent.md")
        assert result == {}

    def test_parses_concept(self, tmp_path):
        md_path = tmp_path / "STUDY.md"
        md_path.write_text(SAMPLE_STUDY_MD, encoding="utf-8")
        records = parse_study_md(md_path)
        assert "compactness" in records
        r = records["compactness"]
        assert r.domain == "real_analysis"
        assert r.overall_mastery == "partial"
        assert r.next_review == "2026-01-04"

    def test_parses_representations(self, tmp_path):
        md_path = tmp_path / "STUDY.md"
        md_path.write_text(SAMPLE_STUDY_MD, encoding="utf-8")
        records = parse_study_md(md_path)
        reps = records["compactness"].representations
        assert len(reps) == 2
        types = [r.type for r in reps]
        assert "formal" in types
        assert "intuitive" in types

    def test_parses_misconceptions(self, tmp_path):
        md_path = tmp_path / "STUDY.md"
        md_path.write_text(SAMPLE_STUDY_MD, encoding="utf-8")
        records = parse_study_md(md_path)
        miscs = records["compactness"].misconceptions
        assert len(miscs) == 2
        confirmed = [m for m in miscs if m.confirmed]
        assert len(confirmed) == 1

    def test_parses_prerequisites(self, tmp_path):
        md_path = tmp_path / "STUDY.md"
        md_path.write_text(SAMPLE_STUDY_MD, encoding="utf-8")
        records = parse_study_md(md_path)
        prereqs = records["compactness"].prerequisites
        assert len(prereqs) == 1
        assert prereqs[0].concept == "metric_space"


class TestGeneratePatch:
    def _make_session(self) -> StudySession:
        return StudySession(
            session_id="test-session",
            session_type="new_concept",
            concept_ids=["compactness"],
            started_at="2026-01-01T00:00:00Z",
            ended_at="2026-01-01T01:00:00Z",
            source_hash="sha256:abc",
            grounding_mode="local_private_source",
            mastery_updates=[
                MasteryUpdate(
                    concept_id="compactness",
                    representation_type="formal",
                    before="unknown",
                    after="partial",
                    next_review_date="2026-01-04",
                )
            ],
        )

    def test_patch_contains_session_id(self):
        patch = generate_patch(self._make_session())
        assert "test-session" in patch

    def test_patch_contains_source_hash(self):
        patch = generate_patch(self._make_session())
        assert "sha256:abc" in patch

    def test_patch_contains_mastery_update(self):
        patch = generate_patch(self._make_session())
        assert "compactness" in patch
        assert "formal" in patch

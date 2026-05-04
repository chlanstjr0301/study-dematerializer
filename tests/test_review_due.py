"""Tests for study_loop/review_due.py (MVP3 Step 6)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from gonghaebun.study_loop.review_due import find_question_bank, get_due_concepts

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2026, 5, 4)


def write_study_md(path: Path, concepts: list[dict]) -> None:
    """Write a minimal STUDY.md with the given concept records."""
    lines = ["# STUDY.md", ""]
    for c in concepts:
        lines += [
            f"## {c['concept_id']}",
            "",
            f"**domain**: {c.get('domain', 'real_analysis')}",
            f"**overall_mastery**: {c.get('overall_mastery', 'unknown')}",
            f"**next_review**: {c.get('next_review', '—')}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# TestGetDueConcepts
# ---------------------------------------------------------------------------


class TestGetDueConcepts:
    def test_returns_list(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [{"concept_id": "compactness", "next_review": "2026-05-01"}])
        result = get_due_concepts(md, today=_TODAY)
        assert isinstance(result, list)

    def test_past_due_returned(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [{"concept_id": "compactness", "next_review": "2026-05-01"}])
        result = get_due_concepts(md, today=_TODAY)
        assert "compactness" in result

    def test_same_day_returned(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [{"concept_id": "compactness", "next_review": "2026-05-04"}])
        result = get_due_concepts(md, today=_TODAY)
        assert "compactness" in result

    def test_future_not_returned(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [{"concept_id": "compactness", "next_review": "2026-05-10"}])
        result = get_due_concepts(md, today=_TODAY)
        assert "compactness" not in result

    def test_missing_next_review_treated_as_due(self, tmp_path):
        md = tmp_path / "STUDY.md"
        # next_review = "—" will be stored as None after parsing
        write_study_md(md, [{"concept_id": "limits", "next_review": "—"}])
        result = get_due_concepts(md, today=_TODAY)
        assert "limits" in result

    def test_empty_study_md_returns_empty(self, tmp_path):
        md = tmp_path / "STUDY.md"
        md.write_text("# STUDY.md\n", encoding="utf-8")
        result = get_due_concepts(md, today=_TODAY)
        assert result == []

    def test_missing_study_md_returns_empty(self, tmp_path):
        md = tmp_path / "STUDY.md"  # does not exist
        result = get_due_concepts(md, today=_TODAY)
        assert result == []

    def test_multiple_mixed_concepts(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [
            {"concept_id": "compactness", "next_review": "2026-05-01"},  # due
            {"concept_id": "limits",      "next_review": "2026-05-10"},  # not due
            {"concept_id": "continuity",  "next_review": "2026-05-04"},  # due (same day)
        ])
        result = get_due_concepts(md, today=_TODAY)
        assert "compactness" in result
        assert "continuity" in result
        assert "limits" not in result

    def test_defaults_to_today(self, tmp_path):
        md = tmp_path / "STUDY.md"
        # Past date — always due regardless of real today
        write_study_md(md, [{"concept_id": "compactness", "next_review": "2000-01-01"}])
        result = get_due_concepts(md)
        assert "compactness" in result

    def test_order_matches_study_md_order(self, tmp_path):
        md = tmp_path / "STUDY.md"
        write_study_md(md, [
            {"concept_id": "alpha", "next_review": "2026-05-01"},
            {"concept_id": "beta",  "next_review": "2026-05-02"},
            {"concept_id": "gamma", "next_review": "2026-05-03"},
        ])
        result = get_due_concepts(md, today=_TODAY)
        assert result == ["alpha", "beta", "gamma"]

    def test_malformed_date_treated_as_due(self, tmp_path):
        md = tmp_path / "STUDY.md"
        # Write raw text with a bad date value
        md.write_text(
            "## badconcept\n\n"
            "**domain**: real_analysis\n"
            "**overall_mastery**: unknown\n"
            "**next_review**: not-a-date\n",
            encoding="utf-8",
        )
        result = get_due_concepts(md, today=_TODAY)
        assert "badconcept" in result


# ---------------------------------------------------------------------------
# TestFindQuestionBank
# ---------------------------------------------------------------------------


class TestFindQuestionBank:
    def test_returns_path_when_exists(self, tmp_path):
        bank = tmp_path / "compactness" / "questions.accepted.json"
        bank.parent.mkdir(parents=True)
        bank.write_text("[]", encoding="utf-8")
        result = find_question_bank(tmp_path, "compactness")
        assert result == bank

    def test_raises_file_not_found_when_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_question_bank(tmp_path, "nonexistent")

    def test_error_message_contains_concept_id(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            find_question_bank(tmp_path, "nonexistent")

    def test_error_message_contains_expected_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="questions.accepted.json"):
            find_question_bank(tmp_path, "nonexistent")

    def test_no_fallback_to_sibling_concept(self, tmp_path):
        # A bank exists for a different concept — must NOT be returned
        sibling = tmp_path / "other_concept" / "questions.accepted.json"
        sibling.parent.mkdir(parents=True)
        sibling.write_text("[]", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            find_question_bank(tmp_path, "target_concept")

    def test_does_not_find_wrong_filename(self, tmp_path):
        # questions.generated.json exists but questions.accepted.json does not
        wrong = tmp_path / "compactness" / "questions.generated.json"
        wrong.parent.mkdir(parents=True)
        wrong.write_text("[]", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            find_question_bank(tmp_path, "compactness")

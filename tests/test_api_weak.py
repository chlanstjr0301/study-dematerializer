"""
Tests for GET /api/weak — weakness-driven review loop (MVP4-G).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.config as cfg

client = TestClient(app)

# ---------------------------------------------------------------------------
# STUDY.md helpers
# ---------------------------------------------------------------------------

def _write_study_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _study_md_with_reps(
    compactness_reps: list[tuple[str, str, str | None]],  # (type, mastery, last_reviewed)
    compactness_next_review: str | None = None,
    connectedness_reps: list[tuple[str, str, str | None]] | None = None,
    connectedness_next_review: str | None = None,
) -> str:
    today = date.today().isoformat()
    lines = ["# STUDY.md", f"_last_updated: {today}_", "", "---", "", "## compactness", "",
             "**domain**: real_analysis", "**overall_mastery**: unknown",
             f"**next_review**: {compactness_next_review or '—'}", "",
             "### Representations", "",
             "| type           | mastery | last_reviewed |",
             "|----------------|---------|---------------|"]
    for rtype, mastery, last in compactness_reps:
        lines.append(f"| {rtype:<14} | {mastery:<7} | {last or '—':<13} |")
    lines += ["", "### Prerequisites", "", "| concept        | mastery | note |",
              "|----------------|---------|------|", "", "### Misconceptions Encountered", "", ""]

    if connectedness_reps is not None:
        lines += ["---", "", "## connectedness", "",
                  "**domain**: real_analysis", "**overall_mastery**: unknown",
                  f"**next_review**: {connectedness_next_review or '—'}", "",
                  "### Representations", "",
                  "| type           | mastery | last_reviewed |",
                  "|----------------|---------|---------------|"]
        for rtype, mastery, last in connectedness_reps:
            lines.append(f"| {rtype:<14} | {mastery:<7} | {last or '—':<13} |")
        lines += ["", "### Prerequisites", "", "| concept        | mastery | note |",
                  "|----------------|---------|------|", "", "### Misconceptions Encountered", "", ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def weak_env(tmp_path: Path, monkeypatch):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow  = (date.today() + timedelta(days=1)).isoformat()

    study_md = tmp_path / "STUDY.md"
    content = _study_md_with_reps(
        compactness_reps=[
            ("formal",         "unknown", None),       # never reviewed
            ("intuitive",      "partial", yesterday),  # partial, reviewed yesterday
            ("visual",         "unknown", yesterday),  # unknown, reviewed yesterday
            ("counterexample", "solid",   yesterday),  # solid — should be excluded
            ("proof_schema",   "partial", yesterday),  # partial
        ],
        compactness_next_review=tomorrow,
        connectedness_reps=[
            ("formal",         "unknown", None),
            ("intuitive",      "unknown", None),
            ("visual",         "unknown", None),
            ("counterexample", "unknown", None),
            ("proof_schema",   "unknown", None),
        ],
        connectedness_next_review=yesterday,  # overdue
    )
    _write_study_md(study_md, content)
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md, "yesterday": yesterday, "tomorrow": tomorrow}


@pytest.fixture()
def no_study_md_env(tmp_path: Path, monkeypatch):
    study_md = tmp_path / "STUDY.md"
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md}


@pytest.fixture()
def all_solid_env(tmp_path: Path, monkeypatch):
    today = date.today().isoformat()
    study_md = tmp_path / "STUDY.md"
    content = _study_md_with_reps(
        compactness_reps=[
            ("formal",         "solid", today),
            ("intuitive",      "solid", today),
            ("visual",         "solid", today),
            ("counterexample", "solid", today),
            ("proof_schema",   "solid", today),
        ],
        compactness_next_review=(date.today() + timedelta(days=7)).isoformat(),
    )
    _write_study_md(study_md, content)
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetWeak:
    def test_get_weak_returns_200(self, weak_env):
        resp = client.get("/api/weak")
        assert resp.status_code == 200

    def test_get_weak_returns_list(self, weak_env):
        resp = client.get("/api/weak")
        assert isinstance(resp.json(), list)

    def test_solid_reps_excluded(self, weak_env):
        items = client.get("/api/weak").json()
        for item in items:
            if item["concept_id"] == "compactness":
                assert item["rep_type"] != "counterexample", "solid reps must be excluded"

    def test_unknown_reps_included(self, weak_env):
        items = client.get("/api/weak").json()
        unknown = [i for i in items if i["mastery"] == "unknown"]
        assert len(unknown) > 0

    def test_partial_reps_included(self, weak_env):
        items = client.get("/api/weak").json()
        partial = [i for i in items if i["mastery"] == "partial"]
        assert len(partial) > 0

    def test_unknown_sorted_before_partial(self, weak_env):
        items = client.get("/api/weak").json()
        masteries = [i["mastery"] for i in items]
        # Find last unknown and first partial
        last_unknown = max((idx for idx, m in enumerate(masteries) if m == "unknown"), default=-1)
        first_partial = min((idx for idx, m in enumerate(masteries) if m == "partial"), default=len(masteries))
        assert last_unknown < first_partial, "All unknown items must precede all partial items"

    def test_overdue_before_upcoming_within_same_mastery(self, weak_env):
        items = client.get("/api/weak").json()
        unknown_items = [i for i in items if i["mastery"] == "unknown"]
        # connectedness is overdue; compactness formal is not_scheduled but connectedness is overdue
        due_statuses = [i["due_status"] for i in unknown_items]
        # overdue items should appear before upcoming/not_scheduled within unknown
        overdue_indices = [idx for idx, s in enumerate(due_statuses) if s == "overdue"]
        non_overdue_indices = [idx for idx, s in enumerate(due_statuses) if s != "overdue"]
        if overdue_indices and non_overdue_indices:
            assert max(overdue_indices) < min(non_overdue_indices), \
                "Overdue items must appear before non-overdue within same mastery level"

    def test_empty_when_no_study_md(self, no_study_md_env):
        resp = client.get("/api/weak")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_all_solid_returns_empty(self, all_solid_env):
        resp = client.get("/api/weak")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_response_fields_present(self, weak_env):
        items = client.get("/api/weak").json()
        assert len(items) > 0
        for item in items:
            assert "concept_id" in item
            assert "rep_type" in item
            assert "mastery" in item
            assert "last_reviewed" in item
            assert "next_review" in item
            assert "due_status" in item

    def test_not_scheduled_due_status_when_no_next_review(self, tmp_path, monkeypatch):
        study_md = tmp_path / "STUDY.md"
        content = _study_md_with_reps(
            compactness_reps=[("formal", "unknown", None)],
            compactness_next_review=None,  # no next_review
        )
        _write_study_md(study_md, content)
        monkeypatch.setattr(cfg, "STUDY_MD", study_md)
        items = client.get("/api/weak").json()
        assert len(items) == 1
        assert items[0]["due_status"] == "not_scheduled"

    def test_compactness_has_correct_weak_count(self, weak_env):
        items = client.get("/api/weak").json()
        compactness_items = [i for i in items if i["concept_id"] == "compactness"]
        # formal(unknown) + intuitive(partial) + visual(unknown) + proof_schema(partial) = 4
        # counterexample(solid) excluded
        assert len(compactness_items) == 4

    def test_connectedness_all_five_reps_weak(self, weak_env):
        items = client.get("/api/weak").json()
        connectedness_items = [i for i in items if i["concept_id"] == "connectedness"]
        assert len(connectedness_items) == 5


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestGetWeakRepresentationsService:
    def test_excludes_solid(self, tmp_path):
        from apps.api.services.study_md_service import get_weak_representations
        study_md = tmp_path / "STUDY.md"
        content = _study_md_with_reps(
            compactness_reps=[("formal", "solid", "2026-01-01")],
        )
        _write_study_md(study_md, content)
        result = get_weak_representations(study_md)
        assert result == []

    def test_includes_unknown_and_partial(self, tmp_path):
        from apps.api.services.study_md_service import get_weak_representations
        study_md = tmp_path / "STUDY.md"
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        content = _study_md_with_reps(
            compactness_reps=[
                ("formal",    "unknown", None),
                ("intuitive", "partial", "2026-01-01"),
                ("visual",    "solid",   "2026-01-01"),
            ],
            compactness_next_review=tomorrow,
        )
        _write_study_md(study_md, content)
        result = get_weak_representations(study_md)
        rep_types = {r["rep_type"] for r in result}
        assert "formal" in rep_types
        assert "intuitive" in rep_types
        assert "visual" not in rep_types

    def test_empty_when_file_missing(self, tmp_path):
        from apps.api.services.study_md_service import get_weak_representations
        result = get_weak_representations(tmp_path / "nonexistent.md")
        assert result == []

    def test_sort_unknown_before_partial(self, tmp_path):
        from apps.api.services.study_md_service import get_weak_representations
        study_md = tmp_path / "STUDY.md"
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        content = _study_md_with_reps(
            compactness_reps=[
                ("formal",    "partial", "2026-01-01"),
                ("intuitive", "unknown", None),
            ],
            compactness_next_review=tomorrow,
        )
        _write_study_md(study_md, content)
        result = get_weak_representations(study_md)
        assert result[0]["mastery"] == "unknown"
        assert result[1]["mastery"] == "partial"

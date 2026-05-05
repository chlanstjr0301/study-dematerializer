"""
Comprehensive tests for GET /api/due — Due Review Scheduler (MVP4-I).
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
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _study_md(concepts: list[dict]) -> str:
    """Build a STUDY.md with multiple concept sections."""
    today_str = date.today().isoformat()
    lines = ["# STUDY.md", f"_last_updated: {today_str}_", ""]
    for c in concepts:
        lines += [
            "---",
            "",
            f"## {c['concept_id']}",
            "",
            "**domain**: real_analysis",
            f"**overall_mastery**: {c.get('overall_mastery', 'unknown')}",
            f"**next_review**: {c.get('next_review', '—')}",
            "",
            "### Representations",
            "",
            "| type           | mastery | last_reviewed |",
            "|----------------|---------|---------------|",
        ]
        for rtype, mastery in c.get("reps", []):
            lines.append(f"| {rtype:<14} | {mastery:<7} | —             |")
        lines += [
            "",
            "### Prerequisites",
            "",
            "| concept        | mastery | note |",
            "|----------------|---------|------|",
            "",
            "### Misconceptions Encountered",
            "",
            "",
        ]
    return "\n".join(lines)


def _weakest(masteries: list[str]) -> str:
    rank = {"unknown": 0, "partial": 1, "solid": 2}
    return min(masteries, key=lambda m: rank.get(m, 0))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def due_env(tmp_path, monkeypatch):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today_str = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # compactness: mixed reps, overdue
    compactness_reps = [
        ("formal",         "unknown"),
        ("intuitive",      "partial"),
        ("visual",         "unknown"),
        ("counterexample", "solid"),
        ("proof_schema",   "partial"),
    ]
    # connectedness: all unknown, due today
    connectedness_reps = [
        ("formal",         "unknown"),
        ("intuitive",      "unknown"),
        ("visual",         "unknown"),
        ("counterexample", "unknown"),
        ("proof_schema",   "unknown"),
    ]
    # uniform_continuity: all solid, overdue — full_recall mode
    uc_reps = [
        ("formal",         "solid"),
        ("intuitive",      "solid"),
        ("visual",         "solid"),
        ("counterexample", "solid"),
        ("proof_schema",   "solid"),
    ]

    content = _study_md([
        {"concept_id": "compactness", "overall_mastery": "unknown",
         "next_review": yesterday, "reps": compactness_reps},
        {"concept_id": "connectedness", "overall_mastery": "unknown",
         "next_review": today_str, "reps": connectedness_reps},
        {"concept_id": "uniform_continuity", "overall_mastery": "solid",
         "next_review": yesterday, "reps": uc_reps},
    ])
    study_md = tmp_path / "STUDY.md"
    _write(study_md, content)
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"yesterday": yesterday, "today": today_str, "tomorrow": tomorrow}


@pytest.fixture()
def future_env(tmp_path, monkeypatch):
    """Concept with next_review in the future — should NOT appear in /api/due."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    content = _study_md([
        {"concept_id": "compactness", "overall_mastery": "unknown",
         "next_review": tomorrow,
         "reps": [("formal", "unknown")]},
    ])
    study_md = tmp_path / "STUDY.md"
    _write(study_md, content)
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {}


@pytest.fixture()
def no_study_md_env(tmp_path, monkeypatch):
    study_md = tmp_path / "STUDY.md"
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {}


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class TestGetDue:
    def test_due_returns_200(self, due_env):
        resp = client.get("/api/due")
        assert resp.status_code == 200

    def test_due_returns_list(self, due_env):
        resp = client.get("/api/due")
        assert isinstance(resp.json(), list)

    def test_future_concept_not_in_due(self, future_env):
        items = client.get("/api/due").json()
        assert all(i["concept_id"] != "compactness" for i in items)

    def test_due_today_concept_appears(self, due_env):
        items = client.get("/api/due").json()
        assert any(i["concept_id"] == "connectedness" for i in items)

    def test_overdue_concept_appears(self, due_env):
        items = client.get("/api/due").json()
        assert any(i["concept_id"] == "compactness" for i in items)

    def test_overdue_flag_true_for_past_date(self, due_env):
        items = client.get("/api/due").json()
        compact = next(i for i in items if i["concept_id"] == "compactness")
        assert compact["overdue"] is True

    def test_overdue_flag_false_for_today(self, due_env):
        items = client.get("/api/due").json()
        conn = next(i for i in items if i["concept_id"] == "connectedness")
        assert conn["overdue"] is False

    def test_response_fields_present(self, due_env):
        items = client.get("/api/due").json()
        assert len(items) > 0
        required = {
            "concept_id", "next_review", "overdue",
            "overall_mastery", "weak_rep_count",
            "target_representations", "suggested_mode", "reason",
        }
        for item in items:
            for field in required:
                assert field in item, f"Missing field: {field}"

    def test_target_reps_excludes_solid(self, due_env):
        items = client.get("/api/due").json()
        compact = next(i for i in items if i["concept_id"] == "compactness")
        # counterexample is solid → must not appear in target_representations
        assert "counterexample" not in compact["target_representations"]

    def test_target_reps_sorted_unknown_before_partial(self, due_env):
        items = client.get("/api/due").json()
        compact = next(i for i in items if i["concept_id"] == "compactness")
        reps = compact["target_representations"]
        # formal=unknown, visual=unknown should come before intuitive=partial, proof_schema=partial
        # Find last unknown and first partial position
        from apps.api.services.study_md_service import parse_study_md  # noqa: local import
        # Just check ordering by re-examining rep types
        # formal and visual are unknown → should precede intuitive and proof_schema (partial)
        unknown_reps = {"formal", "visual"}
        partial_reps = {"intuitive", "proof_schema"}
        unknown_indices = [i for i, r in enumerate(reps) if r in unknown_reps]
        partial_indices = [i for i, r in enumerate(reps) if r in partial_reps]
        if unknown_indices and partial_indices:
            assert max(unknown_indices) < min(partial_indices)

    def test_all_solid_suggested_mode_full_recall(self, due_env):
        """uniform_continuity has all-solid reps and next_review=yesterday → appears in due, full_recall mode."""
        items = client.get("/api/due").json()
        uc = next((i for i in items if i["concept_id"] == "uniform_continuity"), None)
        assert uc is not None, "uniform_continuity should appear in due (next_review=yesterday)"
        assert uc["suggested_mode"] == "full_recall"
        assert uc["target_representations"] == []
        assert uc["weak_rep_count"] == 0

    def test_weak_concept_suggested_mode_weak_only(self, due_env):
        items = client.get("/api/due").json()
        compact = next(i for i in items if i["concept_id"] == "compactness")
        assert compact["suggested_mode"] == "weak_only"

    def test_weak_rep_count_matches_target_reps_length(self, due_env):
        items = client.get("/api/due").json()
        for item in items:
            assert item["weak_rep_count"] == len(item["target_representations"])

    def test_missing_study_md_returns_empty(self, no_study_md_env):
        resp = client.get("/api/due")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestBuildDueItem:
    def test_target_reps_include_non_solid(self, tmp_path, monkeypatch):
        from apps.api.services.study_md_service import get_due

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        study_md = tmp_path / "STUDY.md"
        content = _study_md([
            {
                "concept_id": "compactness",
                "overall_mastery": "unknown",
                "next_review": yesterday,
                "reps": [
                    ("formal",    "unknown"),
                    ("intuitive", "partial"),
                    ("visual",    "solid"),
                ],
            }
        ])
        _write(study_md, content)
        monkeypatch.setattr(cfg, "STUDY_MD", study_md)
        items = get_due(study_md)
        assert len(items) == 1
        target = items[0]["target_representations"]
        assert "formal" in target
        assert "intuitive" in target
        assert "visual" not in target

    def test_target_reps_sorted_unknown_before_partial(self, tmp_path, monkeypatch):
        from apps.api.services.study_md_service import get_due

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        study_md = tmp_path / "STUDY.md"
        content = _study_md([
            {
                "concept_id": "compactness",
                "overall_mastery": "unknown",
                "next_review": yesterday,
                "reps": [
                    ("intuitive", "partial"),  # partial — should come after unknown
                    ("formal",    "unknown"),  # unknown — should come first
                ],
            }
        ])
        _write(study_md, content)
        monkeypatch.setattr(cfg, "STUDY_MD", study_md)
        items = get_due(study_md)
        reps = items[0]["target_representations"]
        assert reps.index("formal") < reps.index("intuitive")

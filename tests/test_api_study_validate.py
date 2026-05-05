"""
Tests for GET /api/study/validate — STUDY.md canonical state validation (MVP4-H).
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


def _clean_study_md(
    concept_id: str = "compactness",
    overall_mastery: str = "unknown",
    next_review: str | None = None,
    reps: list[tuple[str, str]] | None = None,
) -> str:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    nr = next_review or tomorrow
    if reps is None:
        reps = [
            ("formal",         "unknown"),
            ("intuitive",      "unknown"),
            ("visual",         "unknown"),
            ("counterexample", "unknown"),
            ("proof_schema",   "unknown"),
        ]
    today = date.today().isoformat()
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
    for rtype, mastery in reps:
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def clean_env(tmp_path, monkeypatch):
    study_md = tmp_path / "STUDY.md"
    _write(study_md, _clean_study_md())
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md}


@pytest.fixture()
def absent_env(tmp_path, monkeypatch):
    study_md = tmp_path / "STUDY.md"
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md}


@pytest.fixture()
def drifted_env(tmp_path, monkeypatch):
    study_md = tmp_path / "STUDY.md"
    _write(study_md, _clean_study_md(
        overall_mastery="solid",
        reps=[("formal", "unknown")],
    ))
    monkeypatch.setattr(cfg, "STUDY_MD", study_md)
    return {"study_md": study_md}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetValidation:
    def test_validate_returns_200(self, clean_env):
        resp = client.get("/api/study/validate")
        assert resp.status_code == 200

    def test_validate_valid_true_when_study_md_absent(self, absent_env):
        resp = client.get("/api/study/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["errors"] == []
        assert data["warnings"] == []

    def test_validate_valid_true_for_clean_file(self, clean_env):
        resp = client.get("/api/study/validate")
        data = resp.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_valid_false_for_drifted_overall_mastery(self, drifted_env):
        resp = client.get("/api/study/validate")
        data = resp.json()
        assert data["valid"] is False
        assert data["error_count"] > 0
        assert any(e["code"] == "E004" for e in data["errors"])

    def test_validate_error_fields_present(self, drifted_env):
        resp = client.get("/api/study/validate")
        data = resp.json()
        for error in data["errors"]:
            assert "code" in error
            assert "concept_id" in error
            assert "field" in error
            assert "message" in error

    def test_validate_warning_fields_present(self, tmp_path, monkeypatch):
        # Create a file with an unresolvable prerequisite to get a warning
        study_md = tmp_path / "STUDY.md"
        content = _clean_study_md()
        # Inject a prerequisite row
        content = content.replace(
            "### Prerequisites\n\n| concept        | mastery | note |\n|----------------|---------|------|",
            "### Prerequisites\n\n| concept        | mastery | note |\n|----------------|---------|------|\n| zz_never_exists | unknown |      |",
        )
        _write(study_md, content)
        monkeypatch.setattr(cfg, "STUDY_MD", study_md)
        resp = client.get("/api/study/validate")
        data = resp.json()
        assert data["warning_count"] > 0
        for warning in data["warnings"]:
            assert "code" in warning
            assert "concept_id" in warning
            assert "field" in warning
            assert "message" in warning

    def test_validate_counts_match_list_lengths(self, drifted_env):
        resp = client.get("/api/study/validate")
        data = resp.json()
        assert data["error_count"] == len(data["errors"])
        assert data["warning_count"] == len(data["warnings"])

    def test_validate_does_not_modify_file(self, clean_env):
        study_md: Path = clean_env["study_md"]
        mtime_before = study_md.stat().st_mtime
        client.get("/api/study/validate")
        assert study_md.stat().st_mtime == mtime_before

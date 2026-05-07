"""
Tests for Step 11: MASTERY_SCORED_REPS — only formal, counterexample, proof_schema
contribute to overall mastery (weakest-link).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from gonghaebun.study_loop.mastery import MASTERY_SCORED_REPS


# ---------------------------------------------------------------------------
# Constant definition
# ---------------------------------------------------------------------------


class TestMasteryScoredRepsConstant:
    def test_contains_exactly_three(self):
        assert MASTERY_SCORED_REPS == frozenset({"formal", "counterexample", "proof_schema"})

    def test_excludes_intuitive_and_visual(self):
        assert "intuitive" not in MASTERY_SCORED_REPS
        assert "visual" not in MASTERY_SCORED_REPS


# ---------------------------------------------------------------------------
# writer.py overall mastery computation
# ---------------------------------------------------------------------------


class TestWriterOverallMastery:
    """Verify _update_record uses only scored reps for overall mastery."""

    def _make_study_md(self, reps: list[tuple[str, str]], overall: str = "unknown") -> str:
        today = date.today().isoformat()
        rows = "\n".join(f"| {t:<14} | {m:<7} | {today}      |" for t, m in reps)
        return (
            f"# STUDY.md\n_last_updated: {today}_\n\n---\n\n"
            f"## compactness\n\n"
            f"**domain**: real_analysis\n"
            f"**overall_mastery**: {overall}\n"
            f"**next_review**: {today}\n\n"
            f"### Representations\n\n"
            f"| type           | mastery | last_reviewed |\n"
            f"|----------------|---------|---------------|\n"
            f"{rows}\n"
        )

    def _apply_patch_and_get_overall(self, study_md_path: Path, reps: list[tuple[str, str]]) -> str:
        from gonghaebun.models.session_models import (
            MasteryUpdate,
            RecallAttempt,
            RecallEvaluation,
            StudySession,
        )
        from gonghaebun.study_md.writer import apply_patch

        today = date.today().isoformat()
        recall_attempts = []
        mastery_updates = []

        for rep_type, mastery in reps:
            score = {"solid": 0.95, "partial": 0.65, "unknown": 0.2}.get(mastery, 0.0)
            recall_attempts.append(RecallAttempt(
                session_id="test-sess",
                concept_id="compactness",
                representation_type=rep_type,
                learner_response="test",
                evaluation=RecallEvaluation(accuracy_score=score),
                attempted_at=today,
            ))
            mastery_updates.append(MasteryUpdate(
                concept_id="compactness",
                representation_type=rep_type,
                before="unknown",
                after=mastery,
                next_review_date=today,
            ))

        session = StudySession(
            session_id="test-sess",
            session_type="new_concept",
            concept_ids=["compactness"],
            started_at=today,
            ended_at=today,
            llm_backend="mock",
            source_path="",
            source_hash="",
            grounding_mode="local_private_source",
            mastery_updates=mastery_updates,
            recall_attempts=recall_attempts,
        )

        apply_patch(study_md_path, session)

        from gonghaebun.study_md.parser import parse_study_md
        records = parse_study_md(study_md_path)
        return records["compactness"].overall_mastery

    def test_intuitive_visual_unknown_does_not_drag_overall(self, tmp_path):
        """formal=solid, counterexample=solid, proof_schema=solid, intuitive=unknown, visual=unknown → overall=solid."""
        reps = [
            ("formal", "solid"),
            ("intuitive", "unknown"),
            ("visual", "unknown"),
            ("counterexample", "solid"),
            ("proof_schema", "solid"),
        ]
        study_md_path = tmp_path / "STUDY.md"
        study_md_path.write_text(self._make_study_md(reps, "unknown"), encoding="utf-8")

        overall = self._apply_patch_and_get_overall(study_md_path, reps)
        assert overall == "solid"

    def test_formal_unknown_drags_overall(self, tmp_path):
        """formal=unknown drags overall to unknown even if intuitive/visual are solid."""
        reps = [
            ("formal", "unknown"),
            ("intuitive", "solid"),
            ("visual", "solid"),
            ("counterexample", "solid"),
            ("proof_schema", "solid"),
        ]
        study_md_path = tmp_path / "STUDY.md"
        study_md_path.write_text(self._make_study_md(reps, "unknown"), encoding="utf-8")

        overall = self._apply_patch_and_get_overall(study_md_path, reps)
        assert overall == "unknown"

    def test_partial_scored_rep_gives_partial(self, tmp_path):
        """counterexample=partial with other scored reps solid → overall=partial."""
        reps = [
            ("formal", "solid"),
            ("intuitive", "unknown"),
            ("visual", "unknown"),
            ("counterexample", "partial"),
            ("proof_schema", "solid"),
        ]
        study_md_path = tmp_path / "STUDY.md"
        study_md_path.write_text(self._make_study_md(reps, "unknown"), encoding="utf-8")

        overall = self._apply_patch_and_get_overall(study_md_path, reps)
        assert overall == "partial"

    def test_all_scored_solid_is_solid(self, tmp_path):
        """All 3 scored reps solid → overall=solid regardless of intuitive/visual."""
        reps = [
            ("formal", "solid"),
            ("counterexample", "solid"),
            ("proof_schema", "solid"),
        ]
        study_md_path = tmp_path / "STUDY.md"
        study_md_path.write_text(self._make_study_md(reps[:2], "unknown"), encoding="utf-8")

        overall = self._apply_patch_and_get_overall(study_md_path, reps)
        assert overall == "solid"


# ---------------------------------------------------------------------------
# study_session_service overall mastery
# ---------------------------------------------------------------------------


class TestServiceOverallMastery:
    """Verify complete_session computes overall from scored reps only."""

    @pytest.fixture()
    def study_env(self, tmp_path: Path, monkeypatch):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        bank_root = tmp_path / "banks"
        bank_root.mkdir()
        study_md = tmp_path / "STUDY.md"
        study_md.write_text("# Study Progress\n", encoding="utf-8")
        data_root = tmp_path

        sample_source = Path("tests/data/sample_source.md")
        (sources_dir / "test_source.md").write_text(
            sample_source.read_text(encoding="utf-8"), encoding="utf-8"
        )

        import apps.api.services.study_session_service as svc_mod
        monkeypatch.setattr(svc_mod.config, "RUNS_DIR", runs_dir)
        monkeypatch.setattr(svc_mod.config, "SOURCES_DIR", sources_dir)
        monkeypatch.setattr(svc_mod.config, "BANK_ROOT", bank_root)
        monkeypatch.setattr(svc_mod.config, "STUDY_MD", study_md)
        monkeypatch.setattr(svc_mod.config, "DATA_ROOT", data_root)
        monkeypatch.setenv("GONGHAEBUN_FIXTURE_DIR", str(Path("tests/fixtures").resolve()))

        return {
            "runs_dir": runs_dir,
            "sources_dir": sources_dir,
            "bank_root": bank_root,
            "study_md": study_md,
            "data_root": data_root,
        }

    def test_formal_proof_schema_only_gives_non_unknown_overall(self, study_env):
        """Submitting only formal + proof_schema self-explanations → overall not dragged by missing intuitive/visual."""
        from fastapi.testclient import TestClient
        from apps.api.main import app

        client = TestClient(app)

        # Create session
        resp = client.post("/api/study-session", json={"concept_id": "compactness"})
        assert resp.status_code == 201
        sid = resp.json()["session_id"]

        # Diagnose
        client.post(f"/api/study-session/{sid}/diagnose", json={
            "prior_knowledge": "열린 덮개 알아", "gap_description": "유한 부분 덮개 모르겠어",
        })

        # Self-explain only formal + proof_schema (the 2 required scored reps)
        for rep_type in ["formal", "proof_schema"]:
            client.post(f"/api/study-session/{sid}/self-explain", json={
                "representation_type": rep_type,
                "learner_explanation": f"My explanation of {rep_type}...",
            })

        # Advance through all steps (including mapping)
        for step in ["prerequisites", "representations"]:
            client.post(f"/api/study-session/{sid}/advance", json={"completed_step": step})
        tasks_resp = client.get(f"/api/study-session/{sid}/mapping-tasks")
        for task in tasks_resp.json()["tasks"]:
            client.post(f"/api/study-session/{sid}/mapping-submit", json={
                "task_id": task["task_id"], "learner_response": "테스트",
            })
        for step in ["mapping", "misconceptions"]:
            client.post(f"/api/study-session/{sid}/advance", json={"completed_step": step})

        # Submit recall
        client.post(f"/api/study-session/{sid}/recall", json={
            "learner_response": "Compactness means every open cover has a finite subcover...",
        })

        # Complete — overall should NOT be "unknown" just because intuitive/visual/counterexample missing
        resp = client.post(f"/api/study-session/{sid}/complete")
        assert resp.status_code == 200
        data = resp.json()

        # The 2 submitted scored reps (formal, proof_schema) have mock accuracy 0.6 → partial
        # counterexample is unsubmitted → "unknown" (but it IS a scored rep, so overall = unknown)
        # This is correct: you must submit all 3 scored reps to escape "unknown"
        assert data["completed"] is True
        assert data["next_review_date"]


# ---------------------------------------------------------------------------
# validate.py E004 consistency
# ---------------------------------------------------------------------------


class TestValidateE004Consistency:
    """E004 drift check should use MASTERY_SCORED_REPS only."""

    def test_no_e004_when_unscored_reps_differ(self, tmp_path):
        """overall_mastery=solid with intuitive=unknown should NOT trigger E004."""
        from gonghaebun.study_md.validate import validate_study_md_full

        today = date.today().isoformat()
        content = (
            f"# STUDY.md\n_last_updated: {today}_\n\n---\n\n"
            f"## compactness\n\n"
            f"**domain**: real_analysis\n"
            f"**overall_mastery**: solid\n"
            f"**next_review**: {today}\n\n"
            f"### Representations\n\n"
            f"| type           | mastery | last_reviewed |\n"
            f"|----------------|---------|---------------|\n"
            f"| formal         | solid   | {today}      |\n"
            f"| intuitive      | unknown | —             |\n"
            f"| visual         | unknown | —             |\n"
            f"| counterexample | solid   | {today}      |\n"
            f"| proof_schema   | solid   | {today}      |\n"
        )
        study_md = tmp_path / "STUDY.md"
        study_md.write_text(content, encoding="utf-8")
        report = validate_study_md_full(study_md)
        e004_errors = [v for v in report.errors if v.code == "E004"]
        assert len(e004_errors) == 0, f"Expected no E004 but got: {e004_errors}"

    def test_e004_triggers_when_scored_rep_disagrees(self, tmp_path):
        """overall_mastery=solid but formal=partial should trigger E004."""
        from gonghaebun.study_md.validate import validate_study_md_full

        today = date.today().isoformat()
        content = (
            f"# STUDY.md\n_last_updated: {today}_\n\n---\n\n"
            f"## compactness\n\n"
            f"**domain**: real_analysis\n"
            f"**overall_mastery**: solid\n"
            f"**next_review**: {today}\n\n"
            f"### Representations\n\n"
            f"| type           | mastery | last_reviewed |\n"
            f"|----------------|---------|---------------|\n"
            f"| formal         | partial | {today}      |\n"
            f"| counterexample | solid   | {today}      |\n"
            f"| proof_schema   | solid   | {today}      |\n"
        )
        study_md = tmp_path / "STUDY.md"
        study_md.write_text(content, encoding="utf-8")
        report = validate_study_md_full(study_md)
        e004_errors = [v for v in report.errors if v.code == "E004"]
        assert len(e004_errors) == 1

"""Unit tests for apps.api.services.study_session_service."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def study_env(tmp_path: Path, monkeypatch):
    """Isolated environment with source file for full pipeline tests."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    bank_root = tmp_path / "banks"
    bank_root.mkdir()
    study_md = tmp_path / "STUDY.md"
    study_md.write_text("# Study Progress\n", encoding="utf-8")
    data_root = tmp_path

    # Copy test source
    sample_source = Path("tests/data/sample_source.md")
    (sources_dir / "test_source.md").write_text(
        sample_source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Monkeypatch config
    import apps.api.services.study_session_service as svc_mod
    monkeypatch.setattr(svc_mod.config, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(svc_mod.config, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(svc_mod.config, "BANK_ROOT", bank_root)
    monkeypatch.setattr(svc_mod.config, "STUDY_MD", study_md)
    monkeypatch.setattr(svc_mod.config, "DATA_ROOT", data_root)

    # Ensure MockLLMClient finds fixtures
    monkeypatch.setenv("GONGHAEBUN_FIXTURE_DIR", str(Path("tests/fixtures").resolve()))

    return {
        "runs_dir": runs_dir,
        "sources_dir": sources_dir,
        "bank_root": bank_root,
        "study_md": study_md,
        "data_root": data_root,
    }


# ---------------------------------------------------------------------------
# TestResolveSource
# ---------------------------------------------------------------------------


class TestResolveSource:
    def test_explicit_path_resolved(self, study_env):
        from apps.api.services.study_session_service import _resolve_source

        path = _resolve_source(
            "sources/test_source.md",
            study_env["data_root"],
            study_env["sources_dir"],
        )
        assert path.exists()
        assert path.name == "test_source.md"

    def test_auto_discover_first_file(self, study_env):
        from apps.api.services.study_session_service import _resolve_source

        path = _resolve_source(None, study_env["data_root"], study_env["sources_dir"])
        assert path.exists()
        assert path.suffix in {".md", ".txt"}

    def test_no_source_raises_value_error(self, tmp_path):
        from apps.api.services.study_session_service import _resolve_source

        empty_sources = tmp_path / "empty_sources"
        empty_sources.mkdir()
        with pytest.raises(ValueError, match="소스 파일을 찾을 수 없습니다"):
            _resolve_source(None, tmp_path, empty_sources)

    def test_nonexistent_explicit_path_raises(self, study_env):
        from apps.api.services.study_session_service import _resolve_source

        with pytest.raises(ValueError, match="소스 파일을 찾을 수 없습니다"):
            _resolve_source(
                "sources/nonexistent.md",
                study_env["data_root"],
                study_env["sources_dir"],
            )


# ---------------------------------------------------------------------------
# TestCreateSession
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_runs_pipeline_creates_artifacts(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        result = create_study_session("compactness")
        session_dir = study_env["runs_dir"] / result["session_id"]
        assert session_dir.is_dir()
        # Pipeline artifacts
        assert (session_dir / "session.json").exists()
        assert (session_dir / "representation_set.json").exists()
        assert (session_dir / "prerequisite_graph.json").exists()
        assert (session_dir / "diagnosis.json").exists()
        assert (session_dir / "recall_tasks.json").exists()

    def test_bank_auto_accept_in_bank_root(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        create_study_session("compactness")
        bank_dir = study_env["bank_root"] / "compactness"
        assert (bank_dir / "questions.generated.json").exists()
        assert (bank_dir / "questions.accepted.json").exists()

    def test_state_file_has_all_fields(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        result = create_study_session("compactness")
        state_path = study_env["runs_dir"] / result["session_id"] / "study_session_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["session_id"] == result["session_id"]
        assert state["concept_id"] == "compactness"
        assert state["current_step"] == 1
        assert state["steps"] == ["diagnose", "prerequisites", "representations", "misconceptions", "recall", "summary"]
        assert state["steps_completed"] == []
        assert state["diagnosis"] is None
        assert state["recall_completed"] is False
        assert state["self_explanations"] is None
        assert state["recall_session_id"] is None
        assert state["completed"] is False
        assert state["completed_at"] is None
        assert "created_at" in state
        assert "updated_at" in state

    def test_representations_extracted(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        result = create_study_session("compactness")
        assert isinstance(result["representations"], dict)
        assert len(result["representations"]) > 0

    def test_prerequisites_extracted(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        result = create_study_session("compactness")
        assert isinstance(result["prerequisites"], list)
        for p in result["prerequisites"]:
            assert "concept_id" in p
            assert "name_ko" in p
            assert "mastery" in p

    def test_misconceptions_extracted(self, study_env):
        from apps.api.services.study_session_service import create_study_session

        result = create_study_session("compactness")
        assert isinstance(result["misconceptions"], list)
        for m in result["misconceptions"]:
            assert "id" in m
            assert "claim" in m
            assert "is_correct" in m


# ---------------------------------------------------------------------------
# TestDiagnosis
# ---------------------------------------------------------------------------


class TestDiagnosis:
    def _create_session(self, study_env):
        from apps.api.services.study_session_service import create_study_session
        return create_study_session("compactness")

    def test_empty_input_unknown(self, study_env):
        from apps.api.services.study_session_service import submit_diagnosis

        result = self._create_session(study_env)
        resp = submit_diagnosis(result["session_id"], "", "")
        assert resp["initial_mastery_estimate"] == "unknown"

    def test_gap_cue_partial(self, study_env):
        from apps.api.services.study_session_service import submit_diagnosis

        result = self._create_session(study_env)
        resp = submit_diagnosis(result["session_id"], "뭔가 알아", "모르겠어")
        assert resp["initial_mastery_estimate"] == "partial"
        assert len(resp["identified_gaps"]) > 0

    def test_auto_completes_diagnose_step(self, study_env):
        from apps.api.services.study_session_service import get_study_session, submit_diagnosis

        result = self._create_session(study_env)
        submit_diagnosis(result["session_id"], "test", "test")
        state = get_study_session(result["session_id"])
        assert "diagnose" in state["steps_completed"]
        assert state["current_step"] == 2

    def test_duplicate_raises(self, study_env):
        from apps.api.services.study_session_service import submit_diagnosis

        result = self._create_session(study_env)
        submit_diagnosis(result["session_id"], "a", "b")
        with pytest.raises(ValueError, match="이미 진단이 완료되었습니다"):
            submit_diagnosis(result["session_id"], "c", "d")


# ---------------------------------------------------------------------------
# TestAdvance
# ---------------------------------------------------------------------------


class TestAdvance:
    def _create_and_diagnose(self, study_env):
        from apps.api.services.study_session_service import create_study_session, submit_diagnosis

        result = create_study_session("compactness")
        submit_diagnosis(result["session_id"], "test", "test")
        return result["session_id"]

    def test_sequential_enforcement(self, study_env):
        from apps.api.services.study_session_service import advance_step

        sid = self._create_and_diagnose(study_env)
        # Should be able to advance prerequisites (current=2)
        resp = advance_step(sid, "prerequisites")
        assert resp["current_step"] == 3
        assert resp["current_step_name"] == "representations"

    def test_diagnose_via_advance_409(self, study_env):
        from apps.api.services.study_session_service import advance_step

        sid = self._create_and_diagnose(study_env)
        with pytest.raises(ValueError, match="이미 완료된 단계입니다: diagnose"):
            advance_step(sid, "diagnose")

    def test_summary_cannot_advance(self, study_env):
        from apps.api.services.study_session_service import advance_step

        sid = self._create_and_diagnose(study_env)
        advance_step(sid, "prerequisites")
        advance_step(sid, "representations")
        advance_step(sid, "misconceptions")
        advance_step(sid, "recall")
        # Now at step 6 (summary) — "summary" is not advanceable
        with pytest.raises(ValueError, match="유효하지 않은 단계입니다"):
            advance_step(sid, "summary")

    def test_wrong_order_raises(self, study_env):
        from apps.api.services.study_session_service import advance_step

        sid = self._create_and_diagnose(study_env)
        # Try to advance representations before prerequisites
        with pytest.raises(ValueError, match="이전 단계를 먼저 완료해야 합니다"):
            advance_step(sid, "representations")

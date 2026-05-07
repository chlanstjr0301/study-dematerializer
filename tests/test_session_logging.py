"""Tests for stage-level logging in session.py and representation_gen.py."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gonghaebun.llm.mock import MockLLMClient


@pytest.fixture()
def tmp_session(tmp_path):
    """Create minimal session inputs."""
    source = tmp_path / "source.md"
    source.write_text("# Test Source\nCompactness is a topological property.", encoding="utf-8")
    study_md = tmp_path / "STUDY.md"
    study_md.write_text("", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return source, study_md, output_dir


class TestSessionLogging:
    def test_session_logs_stage_start_and_done(self, tmp_session, caplog):
        source, study_md, output_dir = tmp_session
        from gonghaebun.session import run_new_concept_session

        llm = MockLLMClient()
        with caplog.at_level(logging.INFO, logger="gonghaebun.session"):
            run_new_concept_session(
                concept_input="compactness",
                source_path=source,
                llm=llm,
                output_dir=output_dir,
                study_md_path=study_md,
            )

        start_logs = [r for r in caplog.records if "stage_start" in r.message]
        done_logs = [r for r in caplog.records if "stage_done" in r.message]

        # Stages 0, 1, 2, 3, 4, 6, 7 (7 stages with logging)
        assert len(start_logs) >= 7
        assert len(done_logs) >= 7

    def test_session_logs_include_concept_id(self, tmp_session, caplog):
        source, study_md, output_dir = tmp_session
        from gonghaebun.session import run_new_concept_session

        llm = MockLLMClient()
        with caplog.at_level(logging.INFO, logger="gonghaebun.session"):
            run_new_concept_session(
                concept_input="compactness",
                source_path=source,
                llm=llm,
                output_dir=output_dir,
                study_md_path=study_md,
            )

        start_logs = [r for r in caplog.records if "stage_start" in r.message]
        for log in start_logs:
            assert "compactness" in log.message

    def test_session_logs_include_elapsed_ms(self, tmp_session, caplog):
        source, study_md, output_dir = tmp_session
        from gonghaebun.session import run_new_concept_session

        llm = MockLLMClient()
        with caplog.at_level(logging.INFO, logger="gonghaebun.session"):
            run_new_concept_session(
                concept_input="compactness",
                source_path=source,
                llm=llm,
                output_dir=output_dir,
                study_md_path=study_md,
            )

        done_logs = [r for r in caplog.records if "stage_done" in r.message]
        for log in done_logs:
            assert "elapsed_ms=" in log.message


class TestRepresentationGenLogging:
    def test_rep_gen_logs_per_rep_type(self, caplog):
        from gonghaebun.pipeline.representation_gen import generate_representations

        llm = MockLLMClient()
        with caplog.at_level(logging.INFO, logger="gonghaebun.pipeline.representation_gen"):
            generate_representations(
                concept_id="compactness",
                source_excerpt="Test source text",
                source_hash="abc123",
                llm=llm,
            )

        start_logs = [r for r in caplog.records if "rep_gen_start" in r.message]
        done_logs = [r for r in caplog.records if "rep_gen_done" in r.message]

        assert len(start_logs) == 5
        assert len(done_logs) == 5

        rep_types = {"formal", "intuitive", "visual", "counterexample", "proof_schema"}
        logged_types = {log.message.split("rep_type=")[1].split(" ")[0] for log in start_logs}
        assert logged_types == rep_types

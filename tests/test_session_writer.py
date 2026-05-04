"""Tests for study_loop/session_writer.py and study_md/writer.validate_study_md
(MVP3 Step 5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Evidence, Question
from gonghaebun.models.session_models import MasteryUpdate, StudySession
from gonghaebun.study_loop.mastery import AttemptResult
from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
from gonghaebun.study_md.writer import validate_study_md

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EVIDENCE = Evidence(
    source_text="A compact set has every open cover admitting a finite subcover.",
    source_file="test.md",
    start_line=1,
    end_line=3,
    text_hash="abc123",
)

_LONG_TEXT = "A compact set is one where every open cover has a finite subcover."

SESSION_ID = "test-session-0001"
CONCEPT_ID = "compactness"
STARTED = "2026-01-01T10:00:00+00:00"
ENDED = "2026-01-01T10:30:00+00:00"


def make_question(question_type: str = "definition_recall", qid: str = "q1") -> Question:
    return Question(
        question_id=qid,
        document_id="doc",
        source_block_id="doc_b000001",
        question_type=question_type,
        difficulty="medium",
        question="State the definition of compactness.",
        expected_answer=_LONG_TEXT,
        evidence=_EVIDENCE,
        rule_id="R01_definition_recall",
    )


def make_grading(accuracy: float = 0.75) -> GradingResult:
    from gonghaebun.study_md.writer import compute_mastery_state

    return GradingResult(
        accuracy_score=accuracy,
        mastery_suggestion=compute_mastery_state(accuracy),
        raw_response="raw",
    )


def make_attempt(question_type: str = "definition_recall", accuracy: float = 0.75) -> AttemptResult:
    return AttemptResult(
        question=make_question(question_type),
        learner_response="my answer",
        grading=make_grading(accuracy),
    )


# ---------------------------------------------------------------------------
# TestBuildStudySession
# ---------------------------------------------------------------------------


class TestBuildStudySession:
    def test_returns_study_session(self):
        attempts = [make_attempt()]
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", attempts, STARTED, ENDED
        )
        assert isinstance(session, StudySession)

    def test_session_id_stored(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [make_attempt()], STARTED, ENDED
        )
        assert session.session_id == SESSION_ID

    def test_concept_ids_stored(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [make_attempt()], STARTED, ENDED
        )
        assert CONCEPT_ID in session.concept_ids

    def test_mastery_updates_created(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [make_attempt()], STARTED, ENDED
        )
        assert len(session.mastery_updates) >= 1
        assert all(isinstance(u, MasteryUpdate) for u in session.mastery_updates)

    def test_mastery_update_concept_id_matches(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [make_attempt()], STARTED, ENDED
        )
        for u in session.mastery_updates:
            assert u.concept_id == CONCEPT_ID

    def test_recall_attempts_count_matches(self):
        attempts = [make_attempt(), make_attempt("intuition_recall", 1.0)]
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", attempts, STARTED, ENDED
        )
        assert len(session.recall_attempts) == 2

    def test_empty_attempts_produces_empty_updates(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [], STARTED, ENDED
        )
        assert session.mastery_updates == []
        assert session.recall_attempts == []

    def test_multiple_same_rep_type_averaged_to_one_update(self):
        attempts = [
            make_attempt("definition_recall", 0.5),  # formal
            make_attempt("theorem_recall", 1.0),     # formal
        ]
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", attempts, STARTED, ENDED
        )
        formal_updates = [u for u in session.mastery_updates if u.representation_type == "formal"]
        assert len(formal_updates) == 1

    def test_grader_type_stored_in_llm_backend(self):
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", [], STARTED, ENDED, grader_type="mock"
        )
        assert session.llm_backend == "mock"


# ---------------------------------------------------------------------------
# TestWriteSessionArtifacts
# ---------------------------------------------------------------------------


class TestWriteSessionArtifacts:
    def _run(self, tmp_path, attempts=None, grader_type="self"):
        if attempts is None:
            attempts = [make_attempt()]
        session = build_study_session(
            SESSION_ID, CONCEPT_ID, "src.md", attempts, STARTED, ENDED,
            grader_type=grader_type,
        )
        output_dir = write_session_artifacts(
            session=session,
            attempt_results=attempts,
            runs_dir=tmp_path / "runs",
            study_md_path=tmp_path / "STUDY.md",
            grader_type=grader_type,
        )
        return output_dir, session

    def test_returns_output_dir_path(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert isinstance(output_dir, Path)

    def test_output_dir_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert output_dir.is_dir()

    def test_session_json_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert (output_dir / "session.json").exists()

    def test_recall_attempts_json_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert (output_dir / "recall_attempts.json").exists()

    def test_grading_results_json_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert (output_dir / "grading_results.json").exists()

    def test_study_patch_md_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert (output_dir / "STUDY.patch.md").exists()

    def test_session_summary_md_created(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        assert (output_dir / "session_summary.md").exists()

    def test_llm_traces_created_only_for_llm_grader(self, tmp_path):
        output_dir, _ = self._run(tmp_path, grader_type="llm")
        assert (output_dir / "llm_traces.jsonl").exists()

    def test_llm_traces_not_created_for_self_grader(self, tmp_path):
        output_dir, _ = self._run(tmp_path, grader_type="self")
        assert not (output_dir / "llm_traces.jsonl").exists()

    def test_study_md_created(self, tmp_path):
        self._run(tmp_path)
        assert (tmp_path / "STUDY.md").exists()

    def test_study_md_bak_created_on_second_run(self, tmp_path):
        # First run creates STUDY.md; second run creates STUDY.bak
        # (writer.py: shutil.copy2(path, path.with_suffix(".bak")))
        self._run(tmp_path)
        self._run(tmp_path)
        assert (tmp_path / "STUDY.bak").exists()

    def test_recall_attempts_json_is_list(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        data = json.loads((output_dir / "recall_attempts.json").read_text("utf-8"))
        assert isinstance(data, list)

    def test_grading_results_json_contains_raw_response(self, tmp_path):
        output_dir, _ = self._run(tmp_path)
        data = json.loads((output_dir / "grading_results.json").read_text("utf-8"))
        assert all("raw_response" in item for item in data)

    def test_llm_traces_jsonl_line_per_attempt(self, tmp_path):
        attempts = [make_attempt(), make_attempt("intuition_recall")]
        output_dir, _ = self._run(tmp_path, attempts=attempts, grader_type="llm")
        lines = (output_dir / "llm_traces.jsonl").read_text("utf-8").strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert "question_id" in obj
            assert "raw_response" in obj


# ---------------------------------------------------------------------------
# TestValidateStudyMd
# ---------------------------------------------------------------------------


class TestValidateStudyMd:
    def test_valid_study_md_does_not_raise(self, tmp_path):
        md = tmp_path / "STUDY.md"
        md.write_text(
            "# STUDY.md\n\n## compactness\n\n"
            "**domain**: real_analysis\n"
            "**overall_mastery**: unknown\n"
            "**next_review**: 2026-01-01\n",
            encoding="utf-8",
        )
        validate_study_md(md)  # Should not raise

    def test_empty_file_raises_value_error(self, tmp_path):
        md = tmp_path / "STUDY.md"
        md.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="no concept records"):
            validate_study_md(md)

    def test_file_without_concepts_raises(self, tmp_path):
        md = tmp_path / "STUDY.md"
        md.write_text("# STUDY.md\n\n_last_updated: 2026-01-01_\n", encoding="utf-8")
        with pytest.raises(ValueError, match="no concept records"):
            validate_study_md(md)

    def test_apply_patch_creates_bak(self, tmp_path):
        """Verify apply_patch backs up before writing."""
        from gonghaebun.models.session_models import StudySession
        from gonghaebun.study_md.writer import apply_patch

        # Create a first STUDY.md
        md = tmp_path / "STUDY.md"
        md.write_text(
            "## compactness\n\n"
            "**domain**: real_analysis\n"
            "**overall_mastery**: unknown\n"
            "**next_review**: 2026-01-01\n",
            encoding="utf-8",
        )

        session = build_study_session(
            "sess-001", "compactness", "src.md",
            [make_attempt()], STARTED, ENDED,
        )

        apply_patch(md, session)
        # After second call backup exists at STUDY.bak (with_suffix(".bak"))
        apply_patch(md, session)
        assert (tmp_path / "STUDY.bak").exists()

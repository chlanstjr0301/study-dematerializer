"""Tests for visualization/session_visualizer.py (MVP3.1)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from gonghaebun.grading.schemas import GradingResult
from gonghaebun.models.question_bank import Evidence, Question
from gonghaebun.study_loop.mastery import AttemptResult
from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
from gonghaebun.visualization.session_visualizer import write_visualization_artifacts

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_EVIDENCE = Evidence(
    source_text="A compact set has every open cover admitting a finite subcover.",
    source_file="test.md",
    start_line=1,
    end_line=3,
    text_hash="abc123",
)

SESSION_ID = "vis-test-0001"
CONCEPT_ID = "compactness"
STARTED = "2026-01-01T10:00:00+00:00"
ENDED = "2026-01-01T10:30:00+00:00"
TODAY_PAST = date(2020, 1, 1)    # always before any freshly-computed next_review_date → "upcoming"
TODAY_FUTURE = date(2099, 12, 31)  # always after any freshly-computed next_review_date → "overdue"


def make_question(question_type: str = "definition_recall", qid: str = "q1") -> Question:
    return Question(
        question_id=qid,
        document_id="doc",
        source_block_id="doc_b000001",
        question_type=question_type,
        difficulty="medium",
        question="State the definition of compactness.",
        expected_answer="A compact set is one where every open cover has a finite subcover.",
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


def make_attempt(
    question_type: str = "definition_recall",
    accuracy: float = 0.75,
    qid: str = "q1",
) -> AttemptResult:
    return AttemptResult(
        question=make_question(question_type, qid),
        learner_response="my answer",
        grading=make_grading(accuracy),
    )


def _build_session(attempts: list[AttemptResult]) -> object:
    return build_study_session(SESSION_ID, CONCEPT_ID, "src.md", attempts, STARTED, ENDED)


def _run_viz(
    tmp_path: Path,
    attempts: list[AttemptResult] | None = None,
    today: date = TODAY_PAST,
) -> Path:
    if attempts is None:
        attempts = [make_attempt()]
    session = _build_session(attempts)
    viz_dir = tmp_path / "visualization"
    write_visualization_artifacts(session, attempts, viz_dir, today=today)
    return viz_dir


# ---------------------------------------------------------------------------
# TestWriteVisualizationArtifactsDirect
# ---------------------------------------------------------------------------


class TestWriteVisualizationArtifactsDirect:
    def test_viz_dir_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert viz_dir.is_dir()

    def test_mastery_map_json_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert (viz_dir / "mastery_map.json").exists()

    def test_recall_feedback_json_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert (viz_dir / "recall_feedback.json").exists()

    def test_review_queue_json_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert (viz_dir / "review_queue.json").exists()

    def test_mastery_map_mmd_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert (viz_dir / "mastery_map.mmd").exists()

    def test_session_flow_mmd_created(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        assert (viz_dir / "session_flow.mmd").exists()

    # --- mastery_map.json shape ---

    def test_mastery_map_json_has_concept_id(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert data["concept_id"] == CONCEPT_ID

    def test_mastery_map_json_has_overall_mastery(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert "overall_mastery" in data
        assert data["overall_mastery"] in {"unknown", "partial", "solid"}

    def test_mastery_map_json_has_representations_list(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert isinstance(data["representations"], list)
        assert len(data["representations"]) >= 1

    def test_mastery_map_json_representation_has_required_fields(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        for rep in data["representations"]:
            assert "type" in rep
            assert "before" in rep
            assert "after" in rep
            assert "accuracy_score" in rep

    def test_mastery_map_json_has_weakest_links(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert "weakest_links" in data
        assert isinstance(data["weakest_links"], list)

    def test_weakest_links_all_solid_returns_empty(self, tmp_path):
        attempts = [make_attempt(accuracy=1.0)]
        viz_dir = _run_viz(tmp_path, attempts)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert data["weakest_links"] == []

    def test_weakest_links_unknown_included(self, tmp_path):
        # accuracy 0.0 → mastery "unknown"
        attempts = [make_attempt(accuracy=0.0)]
        viz_dir = _run_viz(tmp_path, attempts)
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert len(data["weakest_links"]) >= 1

    # --- recall_feedback.json shape ---

    def test_recall_feedback_is_list(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "recall_feedback.json").read_text("utf-8"))
        assert isinstance(data, list)

    def test_recall_feedback_has_required_fields(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "recall_feedback.json").read_text("utf-8"))
        required = {
            "question_id", "representation_type", "learner_response",
            "accuracy_score", "missing_elements", "errors", "feedback",
            "needs_human_review",
        }
        for item in data:
            assert required <= item.keys()

    def test_recall_feedback_count_matches_attempts(self, tmp_path):
        attempts = [
            make_attempt(qid="q1"),
            make_attempt("intuition_recall", qid="q2"),
        ]
        viz_dir = _run_viz(tmp_path, attempts)
        data = json.loads((viz_dir / "recall_feedback.json").read_text("utf-8"))
        assert len(data) == 2

    # --- review_queue.json shape ---

    def test_review_queue_is_list(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "review_queue.json").read_text("utf-8"))
        assert isinstance(data, list)

    def test_review_queue_has_required_fields(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        data = json.loads((viz_dir / "review_queue.json").read_text("utf-8"))
        required = {"concept_id", "next_review_date", "weakest_representation", "due_status"}
        for item in data:
            assert required <= item.keys()

    def test_review_queue_due_status_overdue(self, tmp_path):
        # today=2099-12-31 is guaranteed past any freshly-computed next_review_date
        viz_dir = _run_viz(tmp_path, today=TODAY_FUTURE)
        data = json.loads((viz_dir / "review_queue.json").read_text("utf-8"))
        assert data[0]["due_status"] == "overdue"

    def test_review_queue_upcoming_status(self, tmp_path):
        # today=2020-01-01 is guaranteed before any freshly-computed next_review_date
        viz_dir = _run_viz(tmp_path, today=TODAY_PAST)
        data = json.loads((viz_dir / "review_queue.json").read_text("utf-8"))
        assert data[0]["due_status"] == "upcoming"

    # --- Mermaid content ---

    def test_mastery_map_mmd_contains_concept_node(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "mastery_map.mmd").read_text("utf-8")
        assert CONCEPT_ID in text

    def test_mastery_map_mmd_contains_rep_node(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "mastery_map.mmd").read_text("utf-8")
        assert "formal" in text

    def test_mastery_map_mmd_starts_with_flowchart(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "mastery_map.mmd").read_text("utf-8")
        assert text.startswith("flowchart")

    def test_session_flow_mmd_contains_grading_node(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "session_flow.mmd").read_text("utf-8")
        assert "grading" in text

    def test_session_flow_mmd_contains_study_md_node(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "session_flow.mmd").read_text("utf-8")
        assert "STUDY.md" in text

    def test_session_flow_mmd_starts_with_flowchart(self, tmp_path):
        viz_dir = _run_viz(tmp_path)
        text = (viz_dir / "session_flow.mmd").read_text("utf-8")
        assert text.startswith("flowchart")


# ---------------------------------------------------------------------------
# TestEmptyAttempts
# ---------------------------------------------------------------------------


class TestEmptyAttempts:
    def test_empty_attempts_no_crash(self, tmp_path):
        viz_dir = _run_viz(tmp_path, attempts=[])
        assert viz_dir.is_dir()

    def test_empty_recall_feedback_is_list(self, tmp_path):
        viz_dir = _run_viz(tmp_path, attempts=[])
        data = json.loads((viz_dir / "recall_feedback.json").read_text("utf-8"))
        assert data == []

    def test_empty_mastery_map_has_no_representations(self, tmp_path):
        viz_dir = _run_viz(tmp_path, attempts=[])
        data = json.loads((viz_dir / "mastery_map.json").read_text("utf-8"))
        assert data["representations"] == []
        assert data["weakest_links"] == []
        assert data["overall_mastery"] is None


# ---------------------------------------------------------------------------
# TestWriteSessionArtifactsCreatesViz  (integration)
# ---------------------------------------------------------------------------


class TestWriteSessionArtifactsCreatesViz:
    def _run_write(self, tmp_path: Path) -> Path:
        attempts = [make_attempt()]
        session = _build_session(attempts)
        output_dir = write_session_artifacts(
            session=session,
            attempt_results=attempts,
            runs_dir=tmp_path / "runs",
            study_md_path=tmp_path / "STUDY.md",
        )
        return output_dir

    def test_visualization_subdir_created(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization").is_dir()

    def test_visualization_mastery_map_json_exists(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization" / "mastery_map.json").exists()

    def test_visualization_recall_feedback_json_exists(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization" / "recall_feedback.json").exists()

    def test_visualization_review_queue_json_exists(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization" / "review_queue.json").exists()

    def test_visualization_mastery_map_mmd_exists(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization" / "mastery_map.mmd").exists()

    def test_visualization_session_flow_mmd_exists(self, tmp_path):
        output_dir = self._run_write(tmp_path)
        assert (output_dir / "visualization" / "session_flow.mmd").exists()

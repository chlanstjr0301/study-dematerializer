"""
Unit tests for:
- study_md.writer.apply_concept_compiler_patch()
- pipeline.recall_orchestrator.convert_tasks_to_questions()
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gonghaebun.study_md.writer import apply_concept_compiler_patch
from gonghaebun.pipeline.recall_orchestrator import convert_tasks_to_questions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PREREQ_GRAPH = {
    "root_concept_id": "connectedness",
    "nodes": [
        {"concept_id": "open_set", "canonical_name": "Open Set", "depth": 1, "mastery_state": "unknown"},
        {"concept_id": "metric_space", "canonical_name": "Metric Space", "depth": 1, "mastery_state": "unknown"},
    ],
    "edges": [
        {"from": "open_set", "to": "connectedness"},
        {"from": "metric_space", "to": "connectedness"},
    ],
}

_DIAGNOSIS = {
    "concept_id": "connectedness",
    "misconceptions": [
        {"id": "m01", "claim": "path-connected implies connected, and conversely", "is_correct": False},
        {"id": "m02", "claim": "ℚ is connected", "is_correct": False},
    ],
}

_TASKS_DATA = {
    "concept_id": "connectedness",
    "mastery_state": "unknown",
    "tasks": [
        {"id": "recall_01", "type": "definition_recall", "prompt": "State the definition."},
        {"id": "recall_02", "type": "counterexample_recall", "prompt": "Give a counterexample."},
        {"id": "recall_03", "type": "proof_schema_recall", "prompt": "What is the first proof step?"},
    ],
}

_REP_SET_DATA = {
    "formal": {"type": "formal", "content": "Formal content " * 60, "mastery_state": "unknown", "last_reviewed": None},
    "counterexample": {"type": "counterexample", "content": "Counter content " * 60, "mastery_state": "unknown", "last_reviewed": None},
    "proof_schema": {"type": "proof_schema", "content": "Proof content " * 60, "mastery_state": "unknown", "last_reviewed": None},
    "intuitive": {"type": "intuitive", "content": "Intuitive content", "mastery_state": "unknown", "last_reviewed": None},
    "visual": {"type": "visual", "content": "Visual content", "mastery_state": "unknown", "last_reviewed": None},
}


# ---------------------------------------------------------------------------
# apply_concept_compiler_patch()
# ---------------------------------------------------------------------------

class TestApplyConceptCompilerPatch:
    def test_writes_prerequisites_table(self, tmp_path: Path):
        study_md = tmp_path / "STUDY.md"
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        content = study_md.read_text(encoding="utf-8")
        assert "open_set" in content
        assert "metric_space" in content

    def test_writes_misconceptions_checkboxes(self, tmp_path: Path):
        study_md = tmp_path / "STUDY.md"
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        content = study_md.read_text(encoding="utf-8")
        assert "path-connected implies connected" in content
        assert "ℚ is connected" in content

    def test_idempotent_no_duplicate_misconceptions(self, tmp_path: Path):
        study_md = tmp_path / "STUDY.md"
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        content = study_md.read_text(encoding="utf-8")
        # claim should appear exactly once
        assert content.count("path-connected implies connected") == 1

    def test_creates_study_md_if_missing(self, tmp_path: Path):
        study_md = tmp_path / "subdir" / "STUDY.md"
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        assert study_md.exists()

    def test_prerequisite_count_matches_non_root_nodes(self, tmp_path: Path):
        study_md = tmp_path / "STUDY.md"
        apply_concept_compiler_patch(study_md, "connectedness", _PREREQ_GRAPH, _DIAGNOSIS)
        content = study_md.read_text(encoding="utf-8")
        # Both open_set and metric_space should be in prerequisites table
        assert content.count("open_set") >= 1
        assert content.count("metric_space") >= 1


# ---------------------------------------------------------------------------
# convert_tasks_to_questions()
# ---------------------------------------------------------------------------

class TestConvertTasksToQuestions:
    def test_produces_correct_count(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        assert len(questions) == 3

    def test_question_type_preserved(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        types = {q.question_type for q in questions}
        assert "definition_recall" in types
        assert "counterexample_recall" in types
        assert "proof_schema_recall" in types

    def test_expected_answer_capped_at_800(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        for q in questions:
            assert len(q.expected_answer) <= 800

    def test_proof_schema_gets_hard_difficulty(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        proof_qs = [q for q in questions if q.question_type == "proof_schema_recall"]
        assert all(q.difficulty == "hard" for q in proof_qs)

    def test_other_types_get_medium_difficulty(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        non_proof = [q for q in questions if q.question_type != "proof_schema_recall"]
        assert all(q.difficulty == "medium" for q in non_proof)

    def test_question_ids_contain_concept_id(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        for q in questions:
            assert "connectedness" in q.question_id

    def test_status_is_candidate(self):
        questions = convert_tasks_to_questions(_TASKS_DATA, _REP_SET_DATA, "connectedness")
        for q in questions:
            assert q.status == "candidate"

    def test_empty_tasks_returns_empty_list(self):
        empty_tasks = {"concept_id": "connectedness", "mastery_state": "unknown", "tasks": []}
        questions = convert_tasks_to_questions(empty_tasks, _REP_SET_DATA, "connectedness")
        assert questions == []

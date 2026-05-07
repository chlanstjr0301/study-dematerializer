"""
Tests for MVP6 data models: MappingTask, MappingResult, ConfusionMap, EvaluationOutput.

Step 2: Validate instantiation, serialization, and rejection of invalid data.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from gonghaebun.models.mapping_models import MappingTask, MappingTaskType, MappingResult
from gonghaebun.models.confusion_map import (
    ConfusionMap,
    EvidenceSnippet,
    MappingEdge,
    PrerequisiteNode,
)
from gonghaebun.models.evaluation_output import EvaluationOutput


# ---------------------------------------------------------------------------
# MappingTask
# ---------------------------------------------------------------------------


class TestMappingTask:
    def _valid_data(self) -> dict:
        return {
            "task_id": "task_001",
            "session_id": "sess_001",
            "concept_id": "compactness",
            "task_type": "formal_to_counterexample",
            "prompt": "Given the formal definition, provide a counterexample.",
            "required_terms": ["open cover", "finite subcover"],
            "grounding_notes": "Must reference (0,1).",
            "source_representations": ["formal"],
            "target_representation": "counterexample",
        }

    def test_valid_mapping_task(self) -> None:
        task = MappingTask(**self._valid_data())
        assert task.task_id == "task_001"
        assert task.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE

    def test_all_task_types(self) -> None:
        for tt in MappingTaskType:
            data = self._valid_data()
            data["task_type"] = tt.value
            task = MappingTask(**data)
            assert task.task_type == tt

    def test_reject_empty_required_terms(self) -> None:
        data = self._valid_data()
        data["required_terms"] = []
        with pytest.raises(ValidationError, match="required_terms"):
            MappingTask(**data)

    def test_reject_empty_source_representations(self) -> None:
        data = self._valid_data()
        data["source_representations"] = []
        with pytest.raises(ValidationError, match="source_representations"):
            MappingTask(**data)

    def test_reject_invalid_task_type(self) -> None:
        data = self._valid_data()
        data["task_type"] = "invalid_type"
        with pytest.raises(ValidationError):
            MappingTask(**data)

    def test_json_roundtrip(self) -> None:
        task = MappingTask(**self._valid_data())
        json_str = task.model_dump_json()
        restored = MappingTask.model_validate_json(json_str)
        assert restored == task


# ---------------------------------------------------------------------------
# MappingResult
# ---------------------------------------------------------------------------


class TestMappingResult:
    def _valid_data(self) -> dict:
        return {
            "task_id": "task_001",
            "task_type": "formal_to_counterexample",
            "learner_response": "(0,1) has no finite subcover for the cover {(1/n,1)}.",
            "score": 0.85,
            "passed": True,
            "missing_elements": [],
            "incorrect_claims": [],
            "misconception_tags": [],
            "mapping_failures": [],
            "feedback": "잘 설명했습니다.",
            "next_recall_trigger": "",
            "evaluated_at": "2026-05-08T12:00:00+09:00",
        }

    def test_valid_result(self) -> None:
        result = MappingResult(**self._valid_data())
        assert result.score == 0.85
        assert result.passed is True

    def test_failed_result_with_misconceptions(self) -> None:
        data = self._valid_data()
        data["score"] = 0.30
        data["passed"] = False
        data["missing_elements"] = ["open cover"]
        data["misconception_tags"] = ["bounded_implies_compact"]
        data["mapping_failures"] = ["formal_to_counterexample"]
        result = MappingResult(**data)
        assert result.passed is False
        assert "bounded_implies_compact" in result.misconception_tags

    def test_reject_score_above_1(self) -> None:
        data = self._valid_data()
        data["score"] = 1.5
        with pytest.raises(ValidationError, match="score"):
            MappingResult(**data)

    def test_reject_score_below_0(self) -> None:
        data = self._valid_data()
        data["score"] = -0.1
        with pytest.raises(ValidationError, match="score"):
            MappingResult(**data)

    def test_json_roundtrip(self) -> None:
        result = MappingResult(**self._valid_data())
        json_str = result.model_dump_json()
        restored = MappingResult.model_validate_json(json_str)
        assert restored == result


# ---------------------------------------------------------------------------
# ConfusionMap sub-models
# ---------------------------------------------------------------------------


class TestPrerequisiteNode:
    def test_valid_node(self) -> None:
        node = PrerequisiteNode(concept_id="metric_space", mastery="unknown")
        assert node.self_reported is None

    def test_with_self_reported(self) -> None:
        node = PrerequisiteNode(
            concept_id="open_cover", mastery="partial", self_reported="unsure"
        )
        assert node.self_reported == "unsure"

    def test_reject_invalid_mastery(self) -> None:
        with pytest.raises(ValidationError):
            PrerequisiteNode(concept_id="x", mastery="excellent")


class TestMappingEdge:
    def test_valid_edge(self) -> None:
        edge = MappingEdge(
            from_rep="formal",
            to_rep="counterexample",
            task_type="formal_to_counterexample",
            passed=False,
            score=0.40,
        )
        assert edge.attempt_count == 1

    def test_reject_negative_score(self) -> None:
        with pytest.raises(ValidationError, match="score"):
            MappingEdge(
                from_rep="a", to_rep="b", task_type="t",
                passed=False, score=-0.1,
            )

    def test_reject_zero_attempt_count(self) -> None:
        with pytest.raises(ValidationError, match="attempt_count"):
            MappingEdge(
                from_rep="a", to_rep="b", task_type="t",
                passed=True, score=0.8, attempt_count=0,
            )


class TestEvidenceSnippet:
    def test_valid_snippet(self) -> None:
        snippet = EvidenceSnippet(
            step="mapping",
            task_type="formal_to_counterexample",
            learner_text="(0,1)은 닫혀 있지 않아서...",
            issue="Missing open cover argument",
        )
        assert snippet.task_type == "formal_to_counterexample"

    def test_truncates_long_text(self) -> None:
        long_text = "a" * 300
        snippet = EvidenceSnippet(
            step="recall", learner_text=long_text, issue="too long"
        )
        assert len(snippet.learner_text) == 200


# ---------------------------------------------------------------------------
# ConfusionMap
# ---------------------------------------------------------------------------


class TestConfusionMap:
    def _valid_data(self) -> dict:
        return {
            "concept_id": "compactness",
            "session_id": "sess_001",
            "prerequisite_nodes": [
                {"concept_id": "metric_space", "mastery": "solid"},
                {"concept_id": "open_cover", "mastery": "unknown"},
            ],
            "mapping_edges": [
                {
                    "from_rep": "formal",
                    "to_rep": "counterexample",
                    "task_type": "formal_to_counterexample",
                    "passed": False,
                    "score": 0.30,
                },
            ],
            "misconception_tags": ["bounded_implies_compact"],
            "next_recall_triggers": [
                "open cover로 (0,1)이 compact하지 않음을 설명하라."
            ],
            "evidence_snippets": [
                {
                    "step": "mapping",
                    "task_type": "formal_to_counterexample",
                    "learner_text": "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
                    "issue": "Missing open cover argument; uses Heine-Borel incorrectly",
                },
            ],
            "last_updated_step": "mapping",
            "created_at": "2026-05-08T10:00:00+09:00",
            "updated_at": "2026-05-08T10:15:00+09:00",
        }

    def test_valid_confusion_map(self) -> None:
        cmap = ConfusionMap(**self._valid_data())
        assert cmap.concept_id == "compactness"
        assert len(cmap.prerequisite_nodes) == 2
        assert len(cmap.mapping_edges) == 1

    def test_empty_lists_valid(self) -> None:
        data = self._valid_data()
        data["prerequisite_nodes"] = []
        data["mapping_edges"] = []
        data["misconception_tags"] = []
        data["next_recall_triggers"] = []
        data["evidence_snippets"] = []
        cmap = ConfusionMap(**data)
        assert len(cmap.mapping_edges) == 0

    def test_json_roundtrip(self) -> None:
        cmap = ConfusionMap(**self._valid_data())
        json_str = cmap.model_dump_json()
        restored = ConfusionMap.model_validate_json(json_str)
        assert restored == cmap

    def test_dict_roundtrip(self) -> None:
        cmap = ConfusionMap(**self._valid_data())
        d = cmap.model_dump()
        restored = ConfusionMap.model_validate(d)
        assert restored.concept_id == cmap.concept_id
        assert len(restored.mapping_edges) == len(cmap.mapping_edges)


# ---------------------------------------------------------------------------
# EvaluationOutput
# ---------------------------------------------------------------------------


class TestEvaluationOutput:
    def _valid_data(self) -> dict:
        return {
            "score": 0.85,
            "mastery": "solid",
            "passed": True,
            "missing_elements": [],
            "incorrect_claims": [],
            "misconception_tags": [],
            "mapping_failures": [],
            "feedback": "잘 설명했습니다.",
            "next_recall_trigger": "",
        }

    def test_valid_output(self) -> None:
        output = EvaluationOutput(**self._valid_data())
        assert output.score == 0.85
        assert output.mastery == "solid"
        assert output.passed is True

    def test_failed_output(self) -> None:
        data = self._valid_data()
        data["score"] = 0.30
        data["mastery"] = "unknown"
        data["passed"] = False
        data["missing_elements"] = ["open cover", "finite subcover"]
        data["misconception_tags"] = ["bounded_implies_compact"]
        data["mapping_failures"] = ["formal_to_counterexample"]
        data["feedback"] = "다음 용어가 누락되었습니다: open cover, finite subcover"
        output = EvaluationOutput(**data)
        assert output.passed is False
        assert len(output.missing_elements) == 2

    def test_needs_human_review_default_false(self) -> None:
        output = EvaluationOutput(**self._valid_data())
        assert output.needs_human_review is False

    def test_needs_human_review_explicit(self) -> None:
        data = self._valid_data()
        data["needs_human_review"] = True
        output = EvaluationOutput(**data)
        assert output.needs_human_review is True

    def test_reject_score_above_1(self) -> None:
        data = self._valid_data()
        data["score"] = 1.01
        with pytest.raises(ValidationError, match="score"):
            EvaluationOutput(**data)

    def test_reject_score_below_0(self) -> None:
        data = self._valid_data()
        data["score"] = -0.01
        with pytest.raises(ValidationError, match="score"):
            EvaluationOutput(**data)

    def test_reject_invalid_mastery(self) -> None:
        data = self._valid_data()
        data["mastery"] = "excellent"
        with pytest.raises(ValidationError):
            EvaluationOutput(**data)

    def test_json_roundtrip(self) -> None:
        output = EvaluationOutput(**self._valid_data())
        json_str = output.model_dump_json()
        restored = EvaluationOutput.model_validate_json(json_str)
        assert restored == output

    def test_next_recall_trigger_default_empty(self) -> None:
        data = self._valid_data()
        del data["next_recall_trigger"]
        output = EvaluationOutput(**data)
        assert output.next_recall_trigger == ""

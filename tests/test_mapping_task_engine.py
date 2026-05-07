"""
Tests for mapping_service: task generation, evaluation, confusion map integration.

Step 7: Mapping Task Engine Service.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.services.confusion_map_service import initialize_confusion_map
from apps.api.services.mapping_service import (
    evaluate_mapping_submission,
    generate_mapping_tasks,
    update_confusion_map_from_mapping,
)
from gonghaebun.models.confusion_map import ConfusionMap
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.mapping_models import MappingResult, MappingTask, MappingTaskType
from gonghaebun.models.rubric import ConceptRubric

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"


@pytest.fixture
def card() -> GroundTruthCard:
    path = CARDS_DIR / "real_analysis" / "compactness.card.json"
    return GroundTruthCard.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def rubric() -> ConceptRubric:
    path = CARDS_DIR / "real_analysis" / "compactness.rubric.json"
    return ConceptRubric.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def tasks(card: GroundTruthCard) -> list[MappingTask]:
    return generate_mapping_tasks("sess_001", "compactness", card)


@pytest.fixture
def cmap(card: GroundTruthCard) -> ConfusionMap:
    return initialize_confusion_map("sess_001", "compactness", card)


# ---------------------------------------------------------------------------
# generate_mapping_tasks
# ---------------------------------------------------------------------------


class TestGenerateMappingTasks:
    def test_produces_three_tasks(self, tasks: list[MappingTask]) -> None:
        assert len(tasks) == 3

    def test_deterministic_task_ids(self, tasks: list[MappingTask]) -> None:
        expected_ids = {
            "sess_001_formal_to_counterexample",
            "sess_001_counterexample_to_formal",
            "sess_001_formal_counterexample_to_proof_schema",
        }
        assert {t.task_id for t in tasks} == expected_ids

    def test_task_types_complete(self, tasks: list[MappingTask]) -> None:
        types = {t.task_type for t in tasks}
        assert types == {
            MappingTaskType.FORMAL_TO_COUNTEREXAMPLE,
            MappingTaskType.COUNTEREXAMPLE_TO_FORMAL,
            MappingTaskType.FORMAL_COUNTEREXAMPLE_TO_PROOF_SCHEMA,
        }

    def test_prompts_are_korean(self, tasks: list[MappingTask]) -> None:
        for task in tasks:
            # Korean prompts contain Korean characters
            assert any("\uac00" <= ch <= "\ud7a3" for ch in task.prompt)

    def test_required_terms_populated(self, tasks: list[MappingTask]) -> None:
        for task in tasks:
            assert len(task.required_terms) > 0

    def test_source_target_representations(self, tasks: list[MappingTask]) -> None:
        task_by_type = {t.task_type: t for t in tasks}

        f2c = task_by_type[MappingTaskType.FORMAL_TO_COUNTEREXAMPLE]
        assert f2c.source_representations == ["formal"]
        assert f2c.target_representation == "counterexample"

        c2f = task_by_type[MappingTaskType.COUNTEREXAMPLE_TO_FORMAL]
        assert c2f.source_representations == ["counterexample"]
        assert c2f.target_representation == "formal"

        fc2ps = task_by_type[MappingTaskType.FORMAL_COUNTEREXAMPLE_TO_PROOF_SCHEMA]
        assert fc2ps.source_representations == ["formal", "counterexample"]
        assert fc2ps.target_representation == "proof_schema"

    def test_session_and_concept_propagated(self, tasks: list[MappingTask]) -> None:
        for task in tasks:
            assert task.session_id == "sess_001"
            assert task.concept_id == "compactness"

    def test_grounding_notes_populated(self, tasks: list[MappingTask]) -> None:
        for task in tasks:
            assert len(task.grounding_notes) > 0


# ---------------------------------------------------------------------------
# evaluate_mapping_submission
# ---------------------------------------------------------------------------


class TestEvaluateMappingSubmission:
    def test_correct_answer_passes(
        self,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(
            f2c,
            "(0,1)의 open cover {(1/n, 1)}을 생각하자. 이 열린 덮개에서 "
            "어떤 유한 부분모임을 택하더라도 (0,1)을 덮을 수 없으므로 "
            "no finite subcover가 존재하지 않는다. 따라서 compact하지 않다.",
            card,
            rubric,
        )
        assert isinstance(result, MappingResult)
        assert result.passed is True
        assert result.score >= 0.70
        assert result.task_id == f2c.task_id
        assert result.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE

    def test_incorrect_answer_fails(
        self,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(
            f2c,
            "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
            card,
            rubric,
        )
        assert result.passed is False
        assert result.score < 0.70
        assert len(result.mapping_failures) >= 1

    def test_empty_answer_scores_zero(
        self,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(f2c, "", card, rubric)
        assert result.score == 0.0
        assert result.passed is False

    def test_evaluated_at_set(
        self,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(f2c, "test", card, rubric)
        assert result.evaluated_at != ""

    def test_misconception_detected(
        self,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        # Answer that triggers "missing_open_cover_argument" misconception
        result = evaluate_mapping_submission(
            f2c,
            "(0,1)은 closed가 아니므로 not compact합니다.",
            card,
            rubric,
        )
        assert "missing_open_cover_argument" in result.misconception_tags


# ---------------------------------------------------------------------------
# update_confusion_map_from_mapping
# ---------------------------------------------------------------------------


class TestUpdateConfusionMapFromMapping:
    def test_integrates_with_confusion_map(
        self,
        cmap: ConfusionMap,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(
            f2c,
            "(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
            card,
            rubric,
        )
        updated = update_confusion_map_from_mapping(cmap, result)
        assert len(updated.mapping_edges) == 1
        assert updated.mapping_edges[0].task_type == "formal_to_counterexample"
        assert updated.last_updated_step == "mapping"

    def test_passing_result_no_evidence(
        self,
        cmap: ConfusionMap,
        tasks: list[MappingTask],
        card: GroundTruthCard,
        rubric: ConceptRubric,
    ) -> None:
        f2c = next(
            t for t in tasks
            if t.task_type == MappingTaskType.FORMAL_TO_COUNTEREXAMPLE
        )
        result = evaluate_mapping_submission(
            f2c,
            "(0,1)의 open cover {(1/n, 1)}을 생각하자. 이 열린 덮개에서 "
            "어떤 유한 부분모임을 택하더라도 (0,1)을 덮을 수 없으므로 "
            "no finite subcover가 존재하지 않는다. 따라서 compact하지 않다.",
            card,
            rubric,
        )
        updated = update_confusion_map_from_mapping(cmap, result)
        assert len(updated.evidence_snippets) == 0

"""
Tests for confusion_map_service: init, per-step updates, persistence, load.

Step 6: Confusion Map Service.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.services.confusion_map_service import (
    initialize_confusion_map,
    load_confusion_map,
    persist_confusion_map,
    update_from_diagnosis,
    update_from_mapping,
    update_from_misconceptions,
    update_from_prerequisites,
    update_from_recall,
    update_from_self_explanation,
)
from gonghaebun.models.confusion_map import ConfusionMap
from gonghaebun.models.evaluation_output import EvaluationOutput
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.mapping_models import MappingResult, MappingTaskType

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"


@pytest.fixture
def card() -> GroundTruthCard:
    path = CARDS_DIR / "real_analysis" / "compactness.card.json"
    return GroundTruthCard.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def cmap(card: GroundTruthCard) -> ConfusionMap:
    return initialize_confusion_map("sess_001", "compactness", card)


# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_creates_confusion_map(self, card: GroundTruthCard) -> None:
        cmap = initialize_confusion_map("sess_001", "compactness", card)
        assert isinstance(cmap, ConfusionMap)
        assert cmap.concept_id == "compactness"
        assert cmap.session_id == "sess_001"

    def test_prerequisite_nodes_from_card(self, card: GroundTruthCard) -> None:
        cmap = initialize_confusion_map("sess_001", "compactness", card)
        prereq_ids = [n.concept_id for n in cmap.prerequisite_nodes]
        assert "metric_space" in prereq_ids
        assert "open_cover" in prereq_ids
        assert all(n.mastery == "unknown" for n in cmap.prerequisite_nodes)

    def test_empty_collections(self, cmap: ConfusionMap) -> None:
        assert cmap.mapping_edges == []
        assert cmap.misconception_tags == []
        assert cmap.next_recall_triggers == []
        assert cmap.evidence_snippets == []

    def test_init_step(self, cmap: ConfusionMap) -> None:
        assert cmap.last_updated_step == "init"

    def test_timestamps_set(self, cmap: ConfusionMap) -> None:
        assert cmap.created_at != ""
        assert cmap.updated_at != ""


# ---------------------------------------------------------------------------
# update_from_diagnosis
# ---------------------------------------------------------------------------


class TestUpdateFromDiagnosis:
    def test_updates_mastery_estimates(self, cmap: ConfusionMap) -> None:
        diagnosis = {
            "mastery_estimates": {"metric_space": "solid", "open_cover": "partial"},
        }
        updated = update_from_diagnosis(cmap, diagnosis)
        node_map = {n.concept_id: n for n in updated.prerequisite_nodes}
        assert node_map["metric_space"].mastery == "solid"
        assert node_map["open_cover"].mastery == "partial"

    def test_adds_misconception_cues(self, cmap: ConfusionMap) -> None:
        diagnosis = {
            "misconception_cues": ["bounded_implies_compact"],
        }
        updated = update_from_diagnosis(cmap, diagnosis)
        assert "bounded_implies_compact" in updated.misconception_tags

    def test_no_duplicate_misconception_cues(self, cmap: ConfusionMap) -> None:
        cmap.misconception_tags = ["bounded_implies_compact"]
        diagnosis = {"misconception_cues": ["bounded_implies_compact"]}
        updated = update_from_diagnosis(cmap, diagnosis)
        assert updated.misconception_tags.count("bounded_implies_compact") == 1

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        updated = update_from_diagnosis(cmap, {})
        assert updated.last_updated_step == "diagnosis"


# ---------------------------------------------------------------------------
# update_from_prerequisites
# ---------------------------------------------------------------------------


class TestUpdateFromPrerequisites:
    def test_sets_self_reported(self, cmap: ConfusionMap) -> None:
        checks = [
            {"concept_id": "metric_space", "self_reported": "known"},
            {"concept_id": "open_cover", "self_reported": "unsure"},
        ]
        updated = update_from_prerequisites(cmap, checks)
        node_map = {n.concept_id: n for n in updated.prerequisite_nodes}
        assert node_map["metric_space"].self_reported == "known"
        assert node_map["open_cover"].self_reported == "unsure"

    def test_ignores_unknown_concepts(self, cmap: ConfusionMap) -> None:
        checks = [{"concept_id": "nonexistent", "self_reported": "known"}]
        updated = update_from_prerequisites(cmap, checks)
        # Should not crash, just skip
        assert updated.last_updated_step == "prerequisites"

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        updated = update_from_prerequisites(cmap, [])
        assert updated.last_updated_step == "prerequisites"


# ---------------------------------------------------------------------------
# update_from_self_explanation
# ---------------------------------------------------------------------------


class TestUpdateFromSelfExplanation:
    def test_adds_misconception_tags(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.40,
            mastery="unknown",
            passed=False,
            missing_elements=["open cover"],
            incorrect_claims=[],
            misconception_tags=["bounded_implies_compact"],
            mapping_failures=[],
            feedback="",
        )
        updated = update_from_self_explanation(cmap, "formal", evaluation)
        assert "bounded_implies_compact" in updated.misconception_tags

    def test_adds_evidence_on_failure(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.30,
            mastery="unknown",
            passed=False,
            missing_elements=["open cover", "finite subcover"],
            incorrect_claims=[],
            misconception_tags=[],
            mapping_failures=[],
            feedback="",
        )
        updated = update_from_self_explanation(cmap, "formal", evaluation)
        assert len(updated.evidence_snippets) == 1
        assert updated.evidence_snippets[0].step == "self_explanation"

    def test_no_evidence_on_pass(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.90,
            mastery="solid",
            passed=True,
            missing_elements=[],
            incorrect_claims=[],
            misconception_tags=[],
            mapping_failures=[],
            feedback="잘 설명했습니다.",
        )
        updated = update_from_self_explanation(cmap, "formal", evaluation)
        assert len(updated.evidence_snippets) == 0

    def test_adds_recall_trigger(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.30,
            mastery="unknown",
            passed=False,
            missing_elements=["open cover"],
            incorrect_claims=[],
            misconception_tags=[],
            mapping_failures=[],
            feedback="",
            next_recall_trigger="이 개념을 다시 설명하라.",
        )
        updated = update_from_self_explanation(cmap, "formal", evaluation)
        assert "이 개념을 다시 설명하라." in updated.next_recall_triggers

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.90, mastery="solid", passed=True,
            missing_elements=[], incorrect_claims=[], misconception_tags=[],
            mapping_failures=[], feedback="",
        )
        updated = update_from_self_explanation(cmap, "formal", evaluation)
        assert updated.last_updated_step == "self_explanation"


# ---------------------------------------------------------------------------
# update_from_mapping
# ---------------------------------------------------------------------------


class TestUpdateFromMapping:
    def _make_result(self, passed: bool = False, score: float = 0.30) -> MappingResult:
        return MappingResult(
            task_id="sess_001_formal_to_counterexample",
            task_type=MappingTaskType.FORMAL_TO_COUNTEREXAMPLE,
            learner_response="(0,1)은 닫혀 있지 않아서 compact하지 않습니다.",
            score=score,
            passed=passed,
            missing_elements=["open cover", "(1/n, 1)"] if not passed else [],
            incorrect_claims=["Every bounded set is compact."] if not passed else [],
            misconception_tags=["missing_open_cover_argument"] if not passed else [],
            mapping_failures=["formal_to_counterexample"] if not passed else [],
            feedback="테스트 피드백",
            next_recall_trigger="open cover로 (0,1)이 compact하지 않음을 설명하라." if not passed else "",
            evaluated_at="2026-05-08T12:00:00+09:00",
        )

    def test_adds_mapping_edge(self, cmap: ConfusionMap) -> None:
        result = self._make_result()
        updated = update_from_mapping(cmap, result)
        assert len(updated.mapping_edges) == 1
        edge = updated.mapping_edges[0]
        assert edge.from_rep == "formal"
        assert edge.to_rep == "counterexample"
        assert edge.task_type == "formal_to_counterexample"
        assert edge.passed is False

    def test_adds_misconception_tags(self, cmap: ConfusionMap) -> None:
        result = self._make_result()
        updated = update_from_mapping(cmap, result)
        assert "missing_open_cover_argument" in updated.misconception_tags

    def test_adds_evidence_on_failure(self, cmap: ConfusionMap) -> None:
        result = self._make_result()
        updated = update_from_mapping(cmap, result)
        assert len(updated.evidence_snippets) == 1
        assert updated.evidence_snippets[0].step == "mapping"

    def test_adds_recall_trigger(self, cmap: ConfusionMap) -> None:
        result = self._make_result()
        updated = update_from_mapping(cmap, result)
        assert any("open cover" in t for t in updated.next_recall_triggers)

    def test_no_evidence_on_pass(self, cmap: ConfusionMap) -> None:
        result = self._make_result(passed=True, score=0.90)
        updated = update_from_mapping(cmap, result)
        assert len(updated.evidence_snippets) == 0

    def test_retry_increments_attempt_count(self, cmap: ConfusionMap) -> None:
        result1 = self._make_result()
        updated = update_from_mapping(cmap, result1)
        assert updated.mapping_edges[0].attempt_count == 1

        result2 = self._make_result(passed=True, score=0.85)
        updated = update_from_mapping(updated, result2)
        assert len(updated.mapping_edges) == 1
        assert updated.mapping_edges[0].attempt_count == 2
        assert updated.mapping_edges[0].passed is True

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        result = self._make_result()
        updated = update_from_mapping(cmap, result)
        assert updated.last_updated_step == "mapping"


# ---------------------------------------------------------------------------
# update_from_misconceptions
# ---------------------------------------------------------------------------


class TestUpdateFromMisconceptions:
    def test_adds_wrong_misconceptions(self, cmap: ConfusionMap) -> None:
        results = [
            {"misconception_id": "bounded_implies_compact", "correct": False},
            {"misconception_id": "heine_borel_in_R", "correct": True},
        ]
        updated = update_from_misconceptions(cmap, results)
        assert "bounded_implies_compact" in updated.misconception_tags
        assert "heine_borel_in_R" not in updated.misconception_tags

    def test_no_duplicates(self, cmap: ConfusionMap) -> None:
        cmap.misconception_tags = ["bounded_implies_compact"]
        results = [
            {"misconception_id": "bounded_implies_compact", "correct": False},
        ]
        updated = update_from_misconceptions(cmap, results)
        assert updated.misconception_tags.count("bounded_implies_compact") == 1

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        updated = update_from_misconceptions(cmap, [])
        assert updated.last_updated_step == "misconceptions"


# ---------------------------------------------------------------------------
# update_from_recall
# ---------------------------------------------------------------------------


class TestUpdateFromRecall:
    def test_adds_tags_on_failure(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.30,
            mastery="unknown",
            passed=False,
            missing_elements=["open cover", "finite subcover"],
            incorrect_claims=[],
            misconception_tags=["bounded_implies_compact"],
            mapping_failures=[],
            feedback="",
        )
        updated = update_from_recall(cmap, evaluation)
        assert "bounded_implies_compact" in updated.misconception_tags
        assert len(updated.evidence_snippets) == 1
        assert updated.evidence_snippets[0].step == "recall"

    def test_no_evidence_on_pass(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.80,
            mastery="partial",
            passed=True,
            missing_elements=[],
            incorrect_claims=[],
            misconception_tags=[],
            mapping_failures=[],
            feedback="잘 설명했습니다.",
        )
        updated = update_from_recall(cmap, evaluation)
        assert len(updated.evidence_snippets) == 0

    def test_step_updated(self, cmap: ConfusionMap) -> None:
        evaluation = EvaluationOutput(
            score=0.80, mastery="partial", passed=True,
            missing_elements=[], incorrect_claims=[], misconception_tags=[],
            mapping_failures=[], feedback="",
        )
        updated = update_from_recall(cmap, evaluation)
        assert updated.last_updated_step == "recall"


# ---------------------------------------------------------------------------
# Persistence + Load roundtrip
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_persist_creates_file(self, cmap: ConfusionMap, tmp_path: Path) -> None:
        session_dir = tmp_path / "sess_001"
        persist_confusion_map(cmap, session_dir)
        assert (session_dir / "confusion_map.json").exists()

    def test_persist_load_roundtrip(self, cmap: ConfusionMap, tmp_path: Path) -> None:
        session_dir = tmp_path / "sess_001"
        persist_confusion_map(cmap, session_dir)
        loaded = load_confusion_map(session_dir)
        assert loaded is not None
        assert loaded.concept_id == cmap.concept_id
        assert loaded.session_id == cmap.session_id
        assert len(loaded.prerequisite_nodes) == len(cmap.prerequisite_nodes)

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        assert load_confusion_map(tmp_path / "nonexistent") is None

    def test_roundtrip_after_updates(self, cmap: ConfusionMap, tmp_path: Path) -> None:
        # Apply some updates
        cmap = update_from_diagnosis(cmap, {
            "mastery_estimates": {"metric_space": "solid"},
            "misconception_cues": ["bounded_implies_compact"],
        })
        result = MappingResult(
            task_id="t1",
            task_type=MappingTaskType.FORMAL_TO_COUNTEREXAMPLE,
            learner_response="test response",
            score=0.40,
            passed=False,
            missing_elements=["open cover"],
            incorrect_claims=[],
            misconception_tags=["missing_open_cover_argument"],
            mapping_failures=["formal_to_counterexample"],
            feedback="test",
            next_recall_trigger="recall trigger",
            evaluated_at="2026-05-08T12:00:00Z",
        )
        cmap = update_from_mapping(cmap, result)

        session_dir = tmp_path / "sess_001"
        persist_confusion_map(cmap, session_dir)
        loaded = load_confusion_map(session_dir)

        assert loaded is not None
        assert loaded.last_updated_step == "mapping"
        assert len(loaded.mapping_edges) == 1
        assert "bounded_implies_compact" in loaded.misconception_tags
        assert "missing_open_cover_argument" in loaded.misconception_tags
        node_map = {n.concept_id: n for n in loaded.prerequisite_nodes}
        assert node_map["metric_space"].mastery == "solid"

    def test_persist_creates_parent_dirs(self, tmp_path: Path, cmap: ConfusionMap) -> None:
        deep_dir = tmp_path / "a" / "b" / "c"
        persist_confusion_map(cmap, deep_dir)
        assert (deep_dir / "confusion_map.json").exists()

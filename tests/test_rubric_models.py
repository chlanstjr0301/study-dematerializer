"""
Tests for MVP6 rubric models: TermCheck, MisconceptionCheck, TaskRubric, ConceptRubric.

Step 2: Validate instantiation, serialization, and rejection of invalid data.
Step 3: Validate compactness.rubric.json loads and has correct structure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from gonghaebun.models.rubric import (
    ConceptRubric,
    MisconceptionCheck,
    TaskRubric,
    TermCheck,
)


# ---------------------------------------------------------------------------
# TermCheck
# ---------------------------------------------------------------------------


class TestTermCheck:
    def test_valid_term(self) -> None:
        tc = TermCheck(term="open cover")
        assert tc.weight == 1.0
        assert tc.aliases == []

    def test_with_aliases(self) -> None:
        tc = TermCheck(term="open cover", weight=2.0, aliases=["열린 덮개"])
        assert tc.weight == 2.0
        assert "열린 덮개" in tc.aliases

    def test_reject_zero_weight(self) -> None:
        with pytest.raises(ValidationError, match="weight"):
            TermCheck(term="x", weight=0.0)

    def test_reject_negative_weight(self) -> None:
        with pytest.raises(ValidationError, match="weight"):
            TermCheck(term="x", weight=-1.0)


# ---------------------------------------------------------------------------
# MisconceptionCheck
# ---------------------------------------------------------------------------


class TestMisconceptionCheck:
    def test_valid_check(self) -> None:
        mc = MisconceptionCheck(
            misconception_id="bounded_implies_compact",
            trigger_patterns=["유계.*compact", "bounded.*compact"],
        )
        assert mc.severity == "moderate"

    def test_critical_severity(self) -> None:
        mc = MisconceptionCheck(
            misconception_id="test",
            trigger_patterns=["pattern"],
            severity="critical",
        )
        assert mc.severity == "critical"

    def test_reject_empty_patterns(self) -> None:
        with pytest.raises(ValidationError, match="trigger_patterns"):
            MisconceptionCheck(
                misconception_id="test",
                trigger_patterns=[],
            )

    def test_reject_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            MisconceptionCheck(
                misconception_id="test",
                trigger_patterns=["p"],
                severity="extreme",
            )


# ---------------------------------------------------------------------------
# TaskRubric
# ---------------------------------------------------------------------------


class TestTaskRubric:
    def _valid_data(self) -> dict:
        return {
            "task_type": "self_explain_formal",
            "required_terms": [
                {"term": "open cover", "weight": 2.0, "aliases": ["열린 덮개"]},
                {"term": "finite subcover", "weight": 2.0},
            ],
            "misconception_checks": [
                {
                    "misconception_id": "bounded_implies_compact",
                    "trigger_patterns": ["bounded.*compact"],
                    "severity": "critical",
                },
            ],
            "pass_threshold": 0.70,
            "scoring_method": "term_coverage",
        }

    def test_valid_rubric(self) -> None:
        rubric = TaskRubric(**self._valid_data())
        assert rubric.task_type == "self_explain_formal"
        assert len(rubric.required_terms) == 2

    def test_default_threshold(self) -> None:
        data = self._valid_data()
        del data["pass_threshold"]
        rubric = TaskRubric(**data)
        assert rubric.pass_threshold == 0.70

    def test_default_scoring_method(self) -> None:
        data = self._valid_data()
        del data["scoring_method"]
        rubric = TaskRubric(**data)
        assert rubric.scoring_method == "term_coverage"

    def test_reject_threshold_above_1(self) -> None:
        data = self._valid_data()
        data["pass_threshold"] = 1.5
        with pytest.raises(ValidationError, match="pass_threshold"):
            TaskRubric(**data)

    def test_reject_invalid_scoring_method(self) -> None:
        data = self._valid_data()
        data["scoring_method"] = "magic"
        with pytest.raises(ValidationError):
            TaskRubric(**data)

    def test_json_roundtrip(self) -> None:
        rubric = TaskRubric(**self._valid_data())
        json_str = rubric.model_dump_json()
        restored = TaskRubric.model_validate_json(json_str)
        assert restored == rubric


# ---------------------------------------------------------------------------
# ConceptRubric
# ---------------------------------------------------------------------------


class TestConceptRubric:
    def _valid_data(self) -> dict:
        task_rubric = {
            "task_type": "self_explain_formal",
            "required_terms": [{"term": "open cover"}],
            "misconception_checks": [],
        }
        return {
            "concept_id": "compactness",
            "domain": "real_analysis",
            "task_rubrics": {
                "self_explain_formal": task_rubric,
            },
            "global_misconception_checks": [
                {
                    "misconception_id": "bounded_implies_compact",
                    "trigger_patterns": ["bounded.*compact"],
                    "severity": "critical",
                },
            ],
        }

    def test_valid_concept_rubric(self) -> None:
        rubric = ConceptRubric(**self._valid_data())
        assert rubric.concept_id == "compactness"
        assert "self_explain_formal" in rubric.task_rubrics

    def test_default_version(self) -> None:
        rubric = ConceptRubric(**self._valid_data())
        assert rubric.version == "1.0"

    def test_multiple_task_rubrics(self) -> None:
        data = self._valid_data()
        data["task_rubrics"]["mapping_formal_to_counterexample"] = {
            "task_type": "mapping_formal_to_counterexample",
            "required_terms": [{"term": "open cover"}, {"term": "(0,1)"}],
            "misconception_checks": [],
        }
        rubric = ConceptRubric(**data)
        assert len(rubric.task_rubrics) == 2

    def test_empty_global_misconceptions(self) -> None:
        data = self._valid_data()
        data["global_misconception_checks"] = []
        rubric = ConceptRubric(**data)
        assert len(rubric.global_misconception_checks) == 0

    def test_json_roundtrip(self) -> None:
        rubric = ConceptRubric(**self._valid_data())
        json_str = rubric.model_dump_json()
        restored = ConceptRubric.model_validate_json(json_str)
        assert restored.concept_id == rubric.concept_id
        assert len(restored.task_rubrics) == len(rubric.task_rubrics)


# ---------------------------------------------------------------------------
# Compactness rubric JSON load tests (Step 3)
# ---------------------------------------------------------------------------

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"
COMPACTNESS_RUBRIC_PATH = CARDS_DIR / "real_analysis" / "compactness.rubric.json"

EXPECTED_TASK_RUBRIC_KEYS = {
    "self_explain_formal",
    "self_explain_counterexample",
    "self_explain_proof_schema",
    "mapping_formal_to_counterexample",
    "mapping_counterexample_to_formal",
    "mapping_formal_counterexample_to_proof_schema",
    "recall",
    "misconception_quiz",
}


@pytest.fixture
def compactness_rubric() -> ConceptRubric:
    """Load and validate the compactness rubric from disk."""
    assert COMPACTNESS_RUBRIC_PATH.exists(), (
        f"Rubric file not found: {COMPACTNESS_RUBRIC_PATH}"
    )
    raw = json.loads(COMPACTNESS_RUBRIC_PATH.read_text(encoding="utf-8"))
    return ConceptRubric.model_validate(raw)


class TestCompactnessRubricLoad:
    """Validate the compactness.rubric.json artifact."""

    def test_rubric_loads_from_json(self, compactness_rubric: ConceptRubric) -> None:
        assert compactness_rubric.concept_id == "compactness"
        assert compactness_rubric.domain == "real_analysis"

    def test_all_eight_task_rubrics_present(self, compactness_rubric: ConceptRubric) -> None:
        assert set(compactness_rubric.task_rubrics.keys()) == EXPECTED_TASK_RUBRIC_KEYS

    def test_task_type_matches_key(self, compactness_rubric: ConceptRubric) -> None:
        for key, rubric in compactness_rubric.task_rubrics.items():
            assert rubric.task_type == key, (
                f"task_rubrics[{key!r}].task_type is {rubric.task_type!r}"
            )

    def test_scored_tasks_have_required_terms(self, compactness_rubric: ConceptRubric) -> None:
        scored_keys = EXPECTED_TASK_RUBRIC_KEYS - {"misconception_quiz"}
        for key in scored_keys:
            rubric = compactness_rubric.task_rubrics[key]
            assert len(rubric.required_terms) > 0, (
                f"task_rubrics[{key!r}] has no required_terms"
            )

    def test_misconception_quiz_has_no_required_terms(self, compactness_rubric: ConceptRubric) -> None:
        quiz = compactness_rubric.task_rubrics["misconception_quiz"]
        assert len(quiz.required_terms) == 0

    def test_recall_threshold_lower(self, compactness_rubric: ConceptRubric) -> None:
        recall = compactness_rubric.task_rubrics["recall"]
        assert recall.pass_threshold == 0.50

    def test_non_recall_thresholds_are_070(self, compactness_rubric: ConceptRubric) -> None:
        for key, rubric in compactness_rubric.task_rubrics.items():
            if key != "recall":
                assert rubric.pass_threshold == 0.70, (
                    f"task_rubrics[{key!r}].pass_threshold is {rubric.pass_threshold}"
                )

    def test_global_misconception_checks_populated(self, compactness_rubric: ConceptRubric) -> None:
        assert len(compactness_rubric.global_misconception_checks) >= 3
        ids = {mc.misconception_id for mc in compactness_rubric.global_misconception_checks}
        assert "bounded_implies_compact" in ids
        assert "misuses_heine_borel" in ids

    def test_global_misconception_trigger_patterns_valid_regex(self, compactness_rubric: ConceptRubric) -> None:
        for mc in compactness_rubric.global_misconception_checks:
            for pattern in mc.trigger_patterns:
                re.compile(pattern)  # raises re.error if invalid

    def test_task_misconception_trigger_patterns_valid_regex(self, compactness_rubric: ConceptRubric) -> None:
        for key, rubric in compactness_rubric.task_rubrics.items():
            for mc in rubric.misconception_checks:
                for pattern in mc.trigger_patterns:
                    re.compile(pattern)  # raises re.error if invalid

    def test_formal_task_has_korean_aliases(self, compactness_rubric: ConceptRubric) -> None:
        formal = compactness_rubric.task_rubrics["self_explain_formal"]
        all_aliases = []
        for tc in formal.required_terms:
            all_aliases.extend(tc.aliases)
        korean_aliases = [a for a in all_aliases if any("\uac00" <= ch <= "\ud7a3" for ch in a)]
        assert len(korean_aliases) >= 2, "Expected at least 2 Korean aliases in self_explain_formal"

    def test_json_roundtrip(self, compactness_rubric: ConceptRubric) -> None:
        json_str = compactness_rubric.model_dump_json()
        restored = ConceptRubric.model_validate_json(json_str)
        assert restored.concept_id == compactness_rubric.concept_id
        assert set(restored.task_rubrics.keys()) == set(compactness_rubric.task_rubrics.keys())

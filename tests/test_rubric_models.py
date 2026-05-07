"""
Tests for MVP6 rubric models: TermCheck, MisconceptionCheck, TaskRubric, ConceptRubric.

Step 2: Validate instantiation, serialization, and rejection of invalid data.
"""
from __future__ import annotations

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

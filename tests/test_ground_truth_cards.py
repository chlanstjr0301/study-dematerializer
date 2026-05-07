"""
Tests for Ground Truth Card schema and compactness card content.

MVP6 Step 1: Validate the Pydantic model and the first card JSON artifact.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from gonghaebun.models.ground_truth_card import (
    AllowedMappingTask,
    CounterexampleCard,
    DefinitionCard,
    GroundTruthCard,
    IntuitiveCard,
    MisconceptionCard,
    ProofSchemaCard,
    VisualCard,
)

# ---------------------------------------------------------------------------
# Path to the real compactness card
# ---------------------------------------------------------------------------

CARDS_DIR = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"
COMPACTNESS_CARD_PATH = CARDS_DIR / "real_analysis" / "compactness.card.json"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


@pytest.fixture
def compactness_card() -> GroundTruthCard:
    """Load and validate the compactness card from disk."""
    assert COMPACTNESS_CARD_PATH.exists(), (
        f"Card file not found: {COMPACTNESS_CARD_PATH}"
    )
    raw = json.loads(COMPACTNESS_CARD_PATH.read_text(encoding="utf-8"))
    return GroundTruthCard.model_validate(raw)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestGroundTruthCardSchema:
    """Test Pydantic model validation rules."""

    def test_card_loads_from_json(self, compactness_card: GroundTruthCard) -> None:
        assert compactness_card.concept_id == "compactness"

    def test_concept_id_is_slug(self, compactness_card: GroundTruthCard) -> None:
        assert _SLUG_RE.match(compactness_card.concept_id)

    def test_prerequisite_concepts_are_slugs(self, compactness_card: GroundTruthCard) -> None:
        for prereq in compactness_card.prerequisite_concepts:
            assert _SLUG_RE.match(prereq), f"Invalid slug: {prereq!r}"

    def test_exactly_three_mapping_tasks(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.allowed_mapping_tasks) == 3

    def test_mapping_task_types_complete(self, compactness_card: GroundTruthCard) -> None:
        types = {t.task_type for t in compactness_card.allowed_mapping_tasks}
        assert types == {
            "formal_to_counterexample",
            "counterexample_to_formal",
            "formal_counterexample_to_proof_schema",
        }

    def test_min_counterexample_cards(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.counterexample_cards) >= 2

    def test_min_misconception_cards(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.misconception_cards) >= 3

    def test_misconception_truth_values(self, compactness_card: GroundTruthCard) -> None:
        trues = [m for m in compactness_card.misconception_cards if m.truth_value]
        falses = [m for m in compactness_card.misconception_cards if not m.truth_value]
        assert len(trues) >= 1, "Need at least one correct statement"
        assert len(falses) >= 2, "Need at least two misconceptions"

    def test_global_required_terms_nonempty(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.required_terms) > 0

    def test_definition_card_required_terms_nonempty(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.definition_card.required_terms) > 0

    def test_proof_schema_required_terms_nonempty(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.proof_schema_card.required_terms) > 0

    def test_proof_schema_steps_nonempty(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.proof_schema_card.proof_steps) > 0

    def test_each_counterexample_has_required_terms(self, compactness_card: GroundTruthCard) -> None:
        for ce in compactness_card.counterexample_cards:
            assert len(ce.required_terms) > 0, (
                f"Counterexample {ce.example_id} has empty required_terms"
            )

    def test_each_mapping_task_has_required_terms(self, compactness_card: GroundTruthCard) -> None:
        for task in compactness_card.allowed_mapping_tasks:
            assert len(task.required_terms) > 0, (
                f"Mapping task {task.task_type} has empty required_terms"
            )


# ---------------------------------------------------------------------------
# Rejection tests (invalid cards should fail validation)
# ---------------------------------------------------------------------------


class TestGroundTruthCardRejection:
    """Test that invalid data is rejected by the model."""

    def _base_data(self) -> dict:
        """Minimal valid card data for mutation testing."""
        return json.loads(COMPACTNESS_CARD_PATH.read_text(encoding="utf-8"))

    def test_reject_empty_concept_id(self) -> None:
        data = self._base_data()
        data["concept_id"] = ""
        with pytest.raises(ValidationError, match="concept_id"):
            GroundTruthCard.model_validate(data)

    def test_reject_concept_id_with_dots(self) -> None:
        data = self._base_data()
        data["concept_id"] = "compact.ness"
        with pytest.raises(ValidationError, match="concept_id"):
            GroundTruthCard.model_validate(data)

    def test_reject_prerequisite_with_slash(self) -> None:
        data = self._base_data()
        data["prerequisite_concepts"] = ["metric/space"]
        with pytest.raises(ValidationError, match="prerequisite_concepts"):
            GroundTruthCard.model_validate(data)

    def test_reject_fewer_than_two_counterexamples(self) -> None:
        data = self._base_data()
        data["counterexample_cards"] = data["counterexample_cards"][:1]
        with pytest.raises(ValidationError, match="counterexample_cards"):
            GroundTruthCard.model_validate(data)

    def test_reject_fewer_than_three_misconceptions(self) -> None:
        data = self._base_data()
        data["misconception_cards"] = data["misconception_cards"][:2]
        with pytest.raises(ValidationError, match="misconception_cards"):
            GroundTruthCard.model_validate(data)

    def test_reject_wrong_mapping_task_count(self) -> None:
        data = self._base_data()
        data["allowed_mapping_tasks"] = data["allowed_mapping_tasks"][:2]
        with pytest.raises(ValidationError, match="allowed_mapping_tasks"):
            GroundTruthCard.model_validate(data)

    def test_reject_empty_required_terms(self) -> None:
        data = self._base_data()
        data["required_terms"] = []
        with pytest.raises(ValidationError, match="required_terms"):
            GroundTruthCard.model_validate(data)

    def test_reject_no_true_misconceptions(self) -> None:
        data = self._base_data()
        # Set all truth_values to False
        for m in data["misconception_cards"]:
            m["truth_value"] = False
        with pytest.raises(ValidationError, match="True"):
            GroundTruthCard.model_validate(data)

    def test_reject_fewer_than_two_false_misconceptions(self) -> None:
        data = self._base_data()
        # Set all truth_values to True except one
        for m in data["misconception_cards"]:
            m["truth_value"] = True
        data["misconception_cards"][0]["truth_value"] = False
        with pytest.raises(ValidationError, match="False"):
            GroundTruthCard.model_validate(data)

    def test_reject_duplicate_mapping_task_types(self) -> None:
        data = self._base_data()
        # Make all 3 the same type
        for task in data["allowed_mapping_tasks"]:
            task["task_type"] = "formal_to_counterexample"
        with pytest.raises(ValidationError, match="mapping_tasks"):
            GroundTruthCard.model_validate(data)


# ---------------------------------------------------------------------------
# Compactness content tests (vertical-slice validation)
# ---------------------------------------------------------------------------


class TestCompactnessCardContent:
    """Validate the mathematical content of the compactness card."""

    def test_domain_is_real_analysis(self, compactness_card: GroundTruthCard) -> None:
        assert compactness_card.domain == "real_analysis"

    def test_has_source_refs(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.source_refs) >= 1
        assert any("Rudin" in ref for ref in compactness_card.source_refs)

    def test_definition_mentions_open_cover(self, compactness_card: GroundTruthCard) -> None:
        defn = compactness_card.definition_card
        assert "open cover" in defn.statement.lower() or "open cover" in " ".join(defn.required_terms).lower()

    def test_definition_mentions_finite_subcover(self, compactness_card: GroundTruthCard) -> None:
        defn = compactness_card.definition_card
        assert "finite subcover" in defn.statement.lower()

    def test_definition_has_korean_translation(self, compactness_card: GroundTruthCard) -> None:
        defn = compactness_card.definition_card
        assert len(defn.statement_kr) > 0
        # Check for at least one Korean character
        assert any("\uac00" <= ch <= "\ud7a3" for ch in defn.statement_kr)

    def test_counterexample_includes_open_unit_interval(self, compactness_card: GroundTruthCard) -> None:
        ids = {ce.example_id for ce in compactness_card.counterexample_cards}
        assert "open_unit_interval" in ids

    def test_counterexample_open_interval_mentions_cover(self, compactness_card: GroundTruthCard) -> None:
        ce = next(c for c in compactness_card.counterexample_cards if c.example_id == "open_unit_interval")
        explanation_lower = ce.explanation.lower()
        assert "open cover" in explanation_lower or "(1/n" in explanation_lower

    def test_proof_schema_is_heine_borel(self, compactness_card: GroundTruthCard) -> None:
        ps = compactness_card.proof_schema_card
        assert "heine" in ps.theorem.lower() and "borel" in ps.theorem.lower()

    def test_proof_schema_has_multiple_steps(self, compactness_card: GroundTruthCard) -> None:
        assert len(compactness_card.proof_schema_card.proof_steps) >= 4

    def test_misconception_bounded_implies_compact(self, compactness_card: GroundTruthCard) -> None:
        ids = {m.misconception_id for m in compactness_card.misconception_cards}
        assert "bounded_implies_compact" in ids
        m = next(m for m in compactness_card.misconception_cards if m.misconception_id == "bounded_implies_compact")
        assert m.truth_value is False

    def test_misconception_misuses_heine_borel(self, compactness_card: GroundTruthCard) -> None:
        ids = {m.misconception_id for m in compactness_card.misconception_cards}
        assert "misuses_heine_borel" in ids
        m = next(m for m in compactness_card.misconception_cards if m.misconception_id == "misuses_heine_borel")
        assert m.truth_value is False

    def test_has_correct_statements_in_misconceptions(self, compactness_card: GroundTruthCard) -> None:
        true_ones = [m for m in compactness_card.misconception_cards if m.truth_value]
        assert len(true_ones) >= 1
        # At least one correct statement should reference Heine-Borel or open cover
        true_claims = " ".join(m.claim.lower() for m in true_ones)
        assert "compact" in true_claims

    def test_prerequisite_concepts_match_knowledge_base(self, compactness_card: GroundTruthCard) -> None:
        expected_prereqs = {"metric_space", "open_set", "open_cover", "heine_borel", "sequential_compactness"}
        actual = set(compactness_card.prerequisite_concepts)
        assert actual == expected_prereqs

    def test_mapping_task_formal_to_counterexample_prompt(self, compactness_card: GroundTruthCard) -> None:
        task = next(t for t in compactness_card.allowed_mapping_tasks if t.task_type == "formal_to_counterexample")
        assert "(0,1)" in task.prompt or "(0,1)" in task.prompt_kr
        assert len(task.prompt_kr) > 0

    def test_version_and_created_at_present(self, compactness_card: GroundTruthCard) -> None:
        assert compactness_card.version == "1.0"
        assert len(compactness_card.created_at) > 0


# ---------------------------------------------------------------------------
# Serialization roundtrip
# ---------------------------------------------------------------------------


class TestCardSerialization:
    """Verify JSON roundtrip."""

    def test_json_roundtrip(self, compactness_card: GroundTruthCard) -> None:
        exported = compactness_card.model_dump()
        roundtripped = GroundTruthCard.model_validate(exported)
        assert roundtripped.concept_id == compactness_card.concept_id
        assert len(roundtripped.counterexample_cards) == len(compactness_card.counterexample_cards)
        assert len(roundtripped.misconception_cards) == len(compactness_card.misconception_cards)

    def test_json_string_roundtrip(self, compactness_card: GroundTruthCard) -> None:
        json_str = compactness_card.model_dump_json()
        roundtripped = GroundTruthCard.model_validate_json(json_str)
        assert roundtripped == compactness_card

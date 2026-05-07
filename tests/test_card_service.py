"""
Tests for card_service: load card, load rubric, not found, cache, config.

Step 5: Card + Rubric Loader Service.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.services.card_service import (
    CardNotFoundError,
    card_exists,
    clear_cache,
    load_ground_truth_card,
    load_rubric,
)
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.rubric import ConceptRubric

# Real card/rubric for load-from-tracked-source tests
CARDS_SRC = Path(__file__).resolve().parent.parent / "src" / "gonghaebun" / "cards"


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear module caches before each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def card_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up CARDS_DIR in tmp_path with a copy of the compactness card + rubric."""
    cards_dir = tmp_path / "cards"
    domain_dir = cards_dir / "real_analysis"
    domain_dir.mkdir(parents=True)

    # Copy real card + rubric
    src_card = CARDS_SRC / "real_analysis" / "compactness.card.json"
    src_rubric = CARDS_SRC / "real_analysis" / "compactness.rubric.json"
    (domain_dir / "compactness.card.json").write_text(
        src_card.read_text(encoding="utf-8"), encoding="utf-8",
    )
    (domain_dir / "compactness.rubric.json").write_text(
        src_rubric.read_text(encoding="utf-8"), encoding="utf-8",
    )

    monkeypatch.setattr("apps.api.services.card_service.config.CARDS_DIR", cards_dir)
    return cards_dir


# ---------------------------------------------------------------------------
# Load card
# ---------------------------------------------------------------------------


class TestLoadCard:
    def test_loads_valid_card(self, card_dir: Path) -> None:
        card = load_ground_truth_card("compactness", use_cache=False)
        assert isinstance(card, GroundTruthCard)
        assert card.concept_id == "compactness"
        assert card.domain == "real_analysis"

    def test_card_has_required_fields(self, card_dir: Path) -> None:
        card = load_ground_truth_card("compactness", use_cache=False)
        assert card.definition_card is not None
        assert len(card.counterexample_cards) >= 2
        assert len(card.misconception_cards) >= 3
        assert len(card.allowed_mapping_tasks) == 3

    def test_card_not_found(self, card_dir: Path) -> None:
        with pytest.raises(CardNotFoundError, match="nonexistent"):
            load_ground_truth_card("nonexistent", use_cache=False)

    def test_card_not_found_has_attributes(self, card_dir: Path) -> None:
        with pytest.raises(CardNotFoundError) as exc_info:
            load_ground_truth_card("missing", use_cache=False)
        assert exc_info.value.concept_id == "missing"
        assert exc_info.value.artifact == "card"


# ---------------------------------------------------------------------------
# Load rubric
# ---------------------------------------------------------------------------


class TestLoadRubric:
    def test_loads_valid_rubric(self, card_dir: Path) -> None:
        rubric = load_rubric("compactness", use_cache=False)
        assert isinstance(rubric, ConceptRubric)
        assert rubric.concept_id == "compactness"

    def test_rubric_has_all_task_rubrics(self, card_dir: Path) -> None:
        rubric = load_rubric("compactness", use_cache=False)
        assert len(rubric.task_rubrics) == 8

    def test_rubric_not_found(self, card_dir: Path) -> None:
        with pytest.raises(CardNotFoundError, match="nonexistent"):
            load_rubric("nonexistent", use_cache=False)

    def test_rubric_not_found_has_attributes(self, card_dir: Path) -> None:
        with pytest.raises(CardNotFoundError) as exc_info:
            load_rubric("missing", use_cache=False)
        assert exc_info.value.artifact == "rubric"


# ---------------------------------------------------------------------------
# card_exists
# ---------------------------------------------------------------------------


class TestCardExists:
    def test_exists_for_compactness(self, card_dir: Path) -> None:
        assert card_exists("compactness") is True

    def test_not_exists_for_unknown(self, card_dir: Path) -> None:
        assert card_exists("unknown_concept") is False


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


class TestCaching:
    def test_card_cached_on_second_call(self, card_dir: Path) -> None:
        card1 = load_ground_truth_card("compactness")
        card2 = load_ground_truth_card("compactness")
        assert card1 is card2  # Same object reference

    def test_rubric_cached_on_second_call(self, card_dir: Path) -> None:
        rubric1 = load_rubric("compactness")
        rubric2 = load_rubric("compactness")
        assert rubric1 is rubric2

    def test_cache_bypass(self, card_dir: Path) -> None:
        card1 = load_ground_truth_card("compactness", use_cache=True)
        card2 = load_ground_truth_card("compactness", use_cache=False)
        assert card1 is not card2  # Different object
        assert card1.concept_id == card2.concept_id

    def test_clear_cache_works(self, card_dir: Path) -> None:
        card1 = load_ground_truth_card("compactness")
        clear_cache()
        card2 = load_ground_truth_card("compactness")
        assert card1 is not card2


# ---------------------------------------------------------------------------
# Config respected
# ---------------------------------------------------------------------------


class TestDefaultCardsDir:
    """Default CARDS_DIR points to tracked src/gonghaebun/cards/ — no monkeypatch."""

    def test_default_cards_dir_is_tracked_source(self) -> None:
        from apps.api import config
        assert config.CARDS_DIR == CARDS_SRC

    def test_load_card_without_monkeypatch(self) -> None:
        card = load_ground_truth_card("compactness", use_cache=False)
        assert isinstance(card, GroundTruthCard)
        assert card.concept_id == "compactness"

    def test_load_rubric_without_monkeypatch(self) -> None:
        rubric = load_rubric("compactness", use_cache=False)
        assert isinstance(rubric, ConceptRubric)
        assert rubric.concept_id == "compactness"


class TestConfigDirOverride:
    def test_custom_cards_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GONGHAEBUN_CARDS_DIR override is respected."""
        custom_dir = tmp_path / "custom_cards"
        domain_dir = custom_dir / "real_analysis"
        domain_dir.mkdir(parents=True)

        src_card = CARDS_SRC / "real_analysis" / "compactness.card.json"
        (domain_dir / "compactness.card.json").write_text(
            src_card.read_text(encoding="utf-8"), encoding="utf-8",
        )

        monkeypatch.setattr("apps.api.services.card_service.config.CARDS_DIR", custom_dir)
        card = load_ground_truth_card("compactness", use_cache=False)
        assert card.concept_id == "compactness"

    def test_missing_dir_raises_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent CARDS_DIR → CardNotFoundError."""
        monkeypatch.setattr(
            "apps.api.services.card_service.config.CARDS_DIR",
            tmp_path / "nonexistent",
        )
        with pytest.raises(CardNotFoundError):
            load_ground_truth_card("compactness", use_cache=False)

"""
Card and rubric loader service for MVP6.

Loads Ground Truth Cards and ConceptRubrics from CARDS_DIR, validates against
Pydantic models, and caches results (cards are static, loaded once).
"""
from __future__ import annotations

from pathlib import Path

from apps.api import config
from gonghaebun.models.ground_truth_card import GroundTruthCard
from gonghaebun.models.rubric import ConceptRubric

# Module-level caches (cards are static data, safe to cache for process lifetime)
_card_cache: dict[str, GroundTruthCard] = {}
_rubric_cache: dict[str, ConceptRubric] = {}

# All current concepts belong to this domain
_DEFAULT_DOMAIN = "real_analysis"


class CardNotFoundError(Exception):
    """Raised when a card or rubric JSON is not found on disk."""

    def __init__(self, concept_id: str, artifact: str = "card") -> None:
        self.concept_id = concept_id
        self.artifact = artifact
        super().__init__(
            f"{artifact} not found for concept '{concept_id}'"
        )


def _resolve_card_path(concept_id: str, domain: str = _DEFAULT_DOMAIN) -> Path:
    return config.CARDS_DIR / domain / f"{concept_id}.card.json"


def _resolve_rubric_path(concept_id: str, domain: str = _DEFAULT_DOMAIN) -> Path:
    return config.CARDS_DIR / domain / f"{concept_id}.rubric.json"


def load_ground_truth_card(
    concept_id: str,
    *,
    domain: str = _DEFAULT_DOMAIN,
    use_cache: bool = True,
) -> GroundTruthCard:
    """Load and validate a Ground Truth Card from CARDS_DIR.

    Raises CardNotFoundError if the file does not exist.
    """
    if use_cache and concept_id in _card_cache:
        return _card_cache[concept_id]

    path = _resolve_card_path(concept_id, domain)
    if not path.exists():
        raise CardNotFoundError(concept_id, "card")

    card = GroundTruthCard.model_validate_json(path.read_text(encoding="utf-8"))
    if use_cache:
        _card_cache[concept_id] = card
    return card


def load_rubric(
    concept_id: str,
    *,
    domain: str = _DEFAULT_DOMAIN,
    use_cache: bool = True,
) -> ConceptRubric:
    """Load and validate a ConceptRubric from CARDS_DIR.

    Raises CardNotFoundError if the file does not exist.
    """
    if use_cache and concept_id in _rubric_cache:
        return _rubric_cache[concept_id]

    path = _resolve_rubric_path(concept_id, domain)
    if not path.exists():
        raise CardNotFoundError(concept_id, "rubric")

    rubric = ConceptRubric.model_validate_json(path.read_text(encoding="utf-8"))
    if use_cache:
        _rubric_cache[concept_id] = rubric
    return rubric


def card_exists(concept_id: str, domain: str = _DEFAULT_DOMAIN) -> bool:
    """Check if a card JSON exists on disk."""
    return _resolve_card_path(concept_id, domain).exists()


def clear_cache() -> None:
    """Clear both caches (useful for testing)."""
    _card_cache.clear()
    _rubric_cache.clear()

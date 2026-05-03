"""
Stage 1: Concept Resolver.

Validates and normalizes the user-provided concept input against the
knowledge base. In MVP 1 this is a pure dictionary lookup — no LLM.

Raises ConceptNotFoundError for unrecognized or out-of-scope input.
"""
from __future__ import annotations

from gonghaebun.knowledge.real_analysis import CONCEPTS, normalize_concept_id
from gonghaebun.models.concept import Concept


class ConceptNotFoundError(ValueError):
    """Raised when the requested concept is not in the knowledge base."""


def resolve_concept(raw_input: str) -> Concept:
    """
    Return the canonical Concept for the given user input string.

    Accepts concept_id directly or any registered alias (case-insensitive).
    Raises ConceptNotFoundError if not recognized.
    """
    concept_id = normalize_concept_id(raw_input)
    if concept_id is None or concept_id not in CONCEPTS:
        known = sorted(
            cid for cid, c in CONCEPTS.items()
            if c.prerequisites or cid == "compactness"
        )
        raise ConceptNotFoundError(
            f"Unknown concept: {raw_input!r}. "
            f"MVP 1 supports: {', '.join(sorted(CONCEPTS))}."
        )
    return CONCEPTS[concept_id]

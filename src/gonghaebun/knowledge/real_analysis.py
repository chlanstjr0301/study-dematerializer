"""
Hardcoded knowledge base for Real Analysis — MVP 1 (compactness only).

Future concepts (connectedness, uniform_continuity) are listed as stubs
in PREREQUISITE_EDGES but have no Concept entries yet.
"""
from __future__ import annotations
from gonghaebun.models.concept import Concept

# ---------------------------------------------------------------------------
# Concept registry
# ---------------------------------------------------------------------------

CONCEPTS: dict[str, Concept] = {
    "compactness": Concept(
        concept_id="compactness",
        canonical_name="Compactness",
        domain="real_analysis",
        aliases=["compact", "compact set", "옹골성", "콤팩트", "compactness"],
        prerequisites=[
            "metric_space",
            "open_set",
            "open_cover",
            "heine_borel",
            "sequential_compactness",
        ],
    ),
    # Prerequisite stubs (no full Concept entry — used only for graph nodes)
    "metric_space": Concept(
        concept_id="metric_space",
        canonical_name="Metric Space",
        domain="real_analysis",
        aliases=["거리 공간", "metric"],
    ),
    "open_set": Concept(
        concept_id="open_set",
        canonical_name="Open Set",
        domain="real_analysis",
        aliases=["열린 집합", "open"],
    ),
    "open_cover": Concept(
        concept_id="open_cover",
        canonical_name="Open Cover",
        domain="real_analysis",
        aliases=["열린 덮개", "open covering"],
    ),
    "heine_borel": Concept(
        concept_id="heine_borel",
        canonical_name="Heine-Borel Theorem",
        domain="real_analysis",
        aliases=["Heine-Borel", "하이네-보렐"],
    ),
    "sequential_compactness": Concept(
        concept_id="sequential_compactness",
        canonical_name="Sequential Compactness",
        domain="real_analysis",
        aliases=["수열 옹골성", "sequentially compact"],
    ),
}

# ---------------------------------------------------------------------------
# Prerequisite edges: concept_id → list of direct prerequisite concept_ids
# ---------------------------------------------------------------------------

PREREQUISITE_EDGES: dict[str, list[str]] = {
    "compactness": [
        "metric_space",
        "open_set",
        "open_cover",
        "heine_borel",
        "sequential_compactness",
    ],
    "open_cover": ["open_set"],
    "heine_borel": ["open_cover", "metric_space"],
    "sequential_compactness": ["metric_space"],
    "open_set": ["metric_space"],
    # Future
    # "connectedness": ["open_set"],
    # "uniform_continuity": ["compactness", "pointwise_continuity"],
}

# ---------------------------------------------------------------------------
# Keyword lists for Stage 0 source extraction
# ---------------------------------------------------------------------------

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "compactness": [
        "compact",
        "compactness",
        "open cover",
        "finite subcover",
        "Heine-Borel",
        "closed and bounded",
        "limit point",
        "perfect",
        "connected",
        "cover",
    ],
}

# ---------------------------------------------------------------------------
# Alias normalizer
# ---------------------------------------------------------------------------

_ALIAS_MAP: dict[str, str] = {}
for _cid, _concept in CONCEPTS.items():
    for _alias in _concept.aliases:
        _ALIAS_MAP[_alias.lower()] = _cid
    _ALIAS_MAP[_cid.lower()] = _cid


def normalize_concept_id(raw: str) -> str | None:
    """Return canonical concept_id for a user-provided string, or None."""
    return _ALIAS_MAP.get(raw.strip().lower())

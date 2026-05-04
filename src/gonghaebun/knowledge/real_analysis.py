"""
Hardcoded knowledge base for Real Analysis — MVP4-G0 (3 seed concepts).

Seed concepts: compactness, connectedness, uniform_continuity.
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
    # ---------------------------------------------------------------------------
    # Seed concept: connectedness
    # ---------------------------------------------------------------------------
    "connectedness": Concept(
        concept_id="connectedness",
        canonical_name="Connectedness",
        domain="real_analysis",
        aliases=["connected", "connected set", "연결성", "connectedness"],
        prerequisites=["open_set", "metric_space"],
    ),
    # ---------------------------------------------------------------------------
    # Seed concept: uniform_continuity
    # ---------------------------------------------------------------------------
    "uniform_continuity": Concept(
        concept_id="uniform_continuity",
        canonical_name="Uniform Continuity",
        domain="real_analysis",
        aliases=["uniformly continuous", "균등 연속", "uniform_continuity"],
        prerequisites=["continuity", "metric_space", "compactness"],
    ),
    # ---------------------------------------------------------------------------
    # Prerequisite stubs (used only for graph nodes)
    # ---------------------------------------------------------------------------
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
    "continuity": Concept(
        concept_id="continuity",
        canonical_name="Continuity",
        domain="real_analysis",
        aliases=["continuous", "연속", "continuity"],
    ),
    "path_connected": Concept(
        concept_id="path_connected",
        canonical_name="Path Connectedness",
        domain="real_analysis",
        aliases=["path-connected", "경로 연결"],
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
    "connectedness": ["open_set", "metric_space"],
    "uniform_continuity": ["continuity", "metric_space", "compactness"],
    "open_cover": ["open_set"],
    "heine_borel": ["open_cover", "metric_space"],
    "sequential_compactness": ["metric_space"],
    "open_set": ["metric_space"],
    "continuity": ["metric_space"],
    "path_connected": ["connectedness"],
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
    "connectedness": [
        "connected",
        "connectedness",
        "path-connected",
        "separated",
        "disconnected",
        "path",
        "component",
        "clopen",
        "intermediate value",
        "separation",
    ],
    "uniform_continuity": [
        "uniform continuity",
        "uniformly continuous",
        "modulus of continuity",
        "Cantor theorem",
        "epsilon",
        "delta",
        "equicontinuous",
        "compact",
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

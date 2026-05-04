"""Tests for gonghaebun.knowledge.real_analysis."""
from __future__ import annotations

import pytest

from gonghaebun.knowledge.real_analysis import (
    CONCEPT_KEYWORDS,
    CONCEPTS,
    PREREQUISITE_EDGES,
    normalize_concept_id,
)


class TestConceptRegistry:
    def test_compactness_present(self):
        assert "compactness" in CONCEPTS

    def test_compactness_has_prerequisites(self):
        c = CONCEPTS["compactness"]
        assert len(c.prerequisites) > 0

    def test_connectedness_in_concepts(self):
        assert "connectedness" in CONCEPTS

    def test_uniform_continuity_in_concepts(self):
        assert "uniform_continuity" in CONCEPTS

    def test_connectedness_prerequisites(self):
        c = CONCEPTS["connectedness"]
        assert "open_set" in c.prerequisites
        assert "metric_space" in c.prerequisites

    def test_uniform_continuity_prerequisites(self):
        c = CONCEPTS["uniform_continuity"]
        assert "continuity" in c.prerequisites
        assert "metric_space" in c.prerequisites
        assert "compactness" in c.prerequisites

    def test_all_concepts_have_canonical_name(self):
        for cid, concept in CONCEPTS.items():
            assert concept.canonical_name, f"{cid} has no canonical_name"


class TestPrerequisiteEdges:
    def test_compactness_edges_exist(self):
        assert "compactness" in PREREQUISITE_EDGES
        assert len(PREREQUISITE_EDGES["compactness"]) > 0

    def test_connectedness_prereq_edges_present(self):
        assert "connectedness" in PREREQUISITE_EDGES
        edges = PREREQUISITE_EDGES["connectedness"]
        assert "open_set" in edges
        assert "metric_space" in edges

    def test_uniform_continuity_prereq_edges_present(self):
        assert "uniform_continuity" in PREREQUISITE_EDGES
        edges = PREREQUISITE_EDGES["uniform_continuity"]
        assert "continuity" in edges
        assert "metric_space" in edges
        assert "compactness" in edges

    def test_no_self_loops(self):
        for cid, deps in PREREQUISITE_EDGES.items():
            assert cid not in deps, f"{cid} has self-loop"

    def test_all_edge_targets_in_concepts(self):
        for cid, deps in PREREQUISITE_EDGES.items():
            for dep in deps:
                assert dep in CONCEPTS, f"Edge target {dep!r} not in CONCEPTS"


class TestConceptKeywords:
    def test_compactness_keywords_present(self):
        assert "compactness" in CONCEPT_KEYWORDS
        assert len(CONCEPT_KEYWORDS["compactness"]) >= 4

    def test_connectedness_keywords_non_empty(self):
        assert "connectedness" in CONCEPT_KEYWORDS
        assert len(CONCEPT_KEYWORDS["connectedness"]) >= 4

    def test_uniform_continuity_keywords_non_empty(self):
        assert "uniform_continuity" in CONCEPT_KEYWORDS
        assert len(CONCEPT_KEYWORDS["uniform_continuity"]) >= 4

    def test_keywords_are_strings(self):
        for cid, kws in CONCEPT_KEYWORDS.items():
            for kw in kws:
                assert isinstance(kw, str)


class TestNormalizeConceptId:
    def test_direct_id(self):
        assert normalize_concept_id("compactness") == "compactness"

    def test_alias(self):
        assert normalize_concept_id("compact") == "compactness"

    def test_case_insensitive(self):
        assert normalize_concept_id("Compactness") == "compactness"
        assert normalize_concept_id("COMPACT SET") == "compactness"

    def test_unknown_returns_none(self):
        assert normalize_concept_id("banana") is None

    def test_korean_alias(self):
        assert normalize_concept_id("옹골성") == "compactness"

    def test_connectedness_alias(self):
        assert normalize_concept_id("connected set") == "connectedness"
        assert normalize_concept_id("연결성") == "connectedness"

    def test_uniform_continuity_alias(self):
        assert normalize_concept_id("uniformly continuous") == "uniform_continuity"
        assert normalize_concept_id("균등 연속") == "uniform_continuity"

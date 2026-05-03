"""Tests for gonghaebun.models."""
from __future__ import annotations

import pytest

from gonghaebun.models.concept import Concept, MasteryLevel
from gonghaebun.models.graph import PrerequisiteEdge, PrerequisiteGraph, PrerequisiteNode
from gonghaebun.models.representations import Representation, RepresentationSet
from gonghaebun.models.session_models import (
    MasteryUpdate,
    RecallAttempt,
    RecallEvaluation,
    StudySession,
)
from gonghaebun.models.source_models import SourceManifest, SourceWindow


class TestConcept:
    def test_defaults(self):
        c = Concept(concept_id="x", canonical_name="X", domain="math")
        assert c.aliases == []
        assert c.prerequisites == []

    def test_mastery_level_values(self):
        levels: list[MasteryLevel] = ["unknown", "partial", "solid"]
        assert len(levels) == 3


class TestPrerequisiteGraph:
    def _make_graph(self, edges: list[tuple[str, str]]) -> PrerequisiteGraph:
        graph_edges = [PrerequisiteEdge(from_concept=a, to_concept=b) for a, b in edges]
        all_ids = {n for e in edges for n in e}
        nodes = [PrerequisiteNode(concept_id=cid, canonical_name=cid, depth=0) for cid in all_ids]
        return PrerequisiteGraph(root_concept_id="root", nodes=nodes, edges=graph_edges)

    def test_no_cycle_returns_false(self):
        g = self._make_graph([("a", "b"), ("b", "c")])
        assert g.has_cycle() is False

    def test_cycle_returns_true(self):
        g = self._make_graph([("a", "b"), ("b", "c"), ("c", "a")])
        assert g.has_cycle() is True

    def test_empty_graph_no_cycle(self):
        g = PrerequisiteGraph(root_concept_id="x", nodes=[], edges=[])
        assert g.has_cycle() is False


class TestRepresentationSet:
    def test_as_list_returns_five(self):
        rs = RepresentationSet(concept_id="compactness")
        reps = rs.as_list()
        assert len(reps) == 5
        types = {r.type for r in reps}
        assert types == {"formal", "intuitive", "visual", "counterexample", "proof_schema"}


class TestStudySession:
    def test_defaults(self):
        s = StudySession(
            session_id="s1",
            session_type="new_concept",
            concept_ids=["compactness"],
            started_at="2026-01-01T00:00:00Z",
        )
        assert s.mastery_updates == []
        assert s.recall_attempts == []
        assert s.grounding_mode == "local_private_source"


class TestSourceModels:
    def test_source_window(self):
        w = SourceWindow(start_char=0, end_char=100, text="hello")
        assert w.start_char == 0

    def test_source_manifest_defaults(self):
        m = SourceManifest(
            source_path="/tmp/f.md",
            source_hash="sha256:abc",
            source_size_chars=1000,
            concept_id="compactness",
            keywords_searched=["compact"],
            keywords_found=["compact"],
            windows_extracted=1,
            source_coverage="sufficient",
            excerpt_chars=500,
            excerpt_capped=False,
            grounding_mode="local_private_source",
            extracted_at="2026-01-01T00:00:00Z",
        )
        assert m.grounding_mode == "local_private_source"

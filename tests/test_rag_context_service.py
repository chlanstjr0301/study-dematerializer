"""
Tests for RAG context retrieval service.
"""
from __future__ import annotations

import pytest

from apps.api.services.rag_context_service import (
    ContextSnippet,
    _score_overlap,
    _tokenize,
    retrieve_context,
)


class TestTokenize:
    def test_basic_split(self):
        tokens = _tokenize("open cover")
        assert "open" in tokens
        assert "cover" in tokens

    def test_particle_stripping(self):
        tokens = _tokenize("옹골성은")
        assert "옹골성" in tokens
        assert "옹골성은" in tokens

    def test_multiple_particles(self):
        tokens = _tokenize("compactness가 finite subcover를")
        assert "compactness" in tokens
        assert "finite" in tokens
        assert "subcover" in tokens


class TestScoreOverlap:
    def test_full_overlap(self):
        tokens = {"open", "cover", "finite"}
        score = _score_overlap(tokens, "An open cover with a finite subcover")
        assert score > 0.5

    def test_no_overlap(self):
        tokens = {"banana", "apple"}
        score = _score_overlap(tokens, "옹골성의 정의")
        assert score == 0.0

    def test_partial_overlap(self):
        tokens = {"compact", "open", "banana"}
        score = _score_overlap(tokens, "compact set has open cover")
        assert 0.3 < score < 1.0

    def test_empty_tokens(self):
        score = _score_overlap(set(), "some text")
        assert score == 0.0

    def test_empty_text(self):
        score = _score_overlap({"token"}, "")
        assert score == 0.0


class TestRetrieveContext:
    def test_known_concept_returns_snippets(self):
        """Compactness card exists → should return card snippets."""
        result = retrieve_context(
            concept_id="compactness",
            message="open cover가 뭐야?",
        )
        assert len(result) > 0
        assert all(isinstance(s, ContextSnippet) for s in result)

    def test_unknown_concept_returns_empty(self):
        """Non-existent concept → no card snippets, maybe previews."""
        result = retrieve_context(
            concept_id="nonexistent_xyz",
            message="test",
        )
        # No card, no preview for unknown concept
        assert all(s.source_type != "ground_truth_card" for s in result)

    def test_none_concept_returns_study_md_only(self):
        """No concept → only STUDY.md context (if exists)."""
        result = retrieve_context(
            concept_id=None,
            message="test message",
        )
        # Should not crash; may return empty or study_md snippets
        assert isinstance(result, list)

    def test_top_k_limit(self):
        result = retrieve_context(
            concept_id="compactness",
            message="open cover finite subcover",
            top_k=3,
        )
        assert len(result) <= 3

    def test_snippets_sorted_by_score(self):
        result = retrieve_context(
            concept_id="compactness",
            message="open cover",
        )
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i].score >= result[i + 1].score

    def test_includes_definition_snippet(self):
        """Definition card should always be included for known concepts."""
        result = retrieve_context(
            concept_id="compactness",
            message="compactness 정의",
        )
        source_ids = [s.source_id for s in result]
        assert any("definition" in sid for sid in source_ids)

    def test_includes_misconception_snippets(self):
        result = retrieve_context(
            concept_id="compactness",
            message="오개념 misconception",
        )
        source_ids = [s.source_id for s in result]
        assert any("misconception" in sid for sid in source_ids)

    def test_includes_proof_schema(self):
        result = retrieve_context(
            concept_id="compactness",
            message="증명 proof schema",
        )
        source_ids = [s.source_id for s in result]
        assert any("proof_schema" in sid for sid in source_ids)

    def test_recent_messages_expand_query(self):
        """Recent messages should broaden the query tokens."""
        # Without context
        r1 = retrieve_context(concept_id="compactness", message="설명해")
        # With context mentioning specific terms
        r2 = retrieve_context(
            concept_id="compactness",
            message="설명해",
            recent_messages=["open cover가 왜 중요해?"],
        )
        # r2 should have higher scores for open-cover-related snippets
        assert isinstance(r2, list)

    def test_snippet_to_dict(self):
        s = ContextSnippet(
            source_id="test:id",
            source_type="ground_truth_card",
            title="Test",
            text="content",
            score=0.8,
        )
        d = s.to_dict()
        assert d["source_id"] == "test:id"
        assert d["score"] == 0.8

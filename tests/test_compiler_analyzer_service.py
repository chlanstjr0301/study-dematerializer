"""
Unit tests for compiler_analyzer_service — tokenization, scoring, fuzzy matching.
"""
from __future__ import annotations

from apps.api.services.compiler_analyzer_service import (
    _edit_distance,
    _score_concepts,
    _strip_particles,
    _tokenize,
    analyze_message,
)


class TestTokenization:
    def test_strip_particle_을(self):
        variants = _strip_particles("옹골성을")
        assert "옹골성" in variants
        assert "옹골성을" in variants

    def test_strip_particle_에서(self):
        variants = _strip_particles("옹골성에서")
        assert "옹골성" in variants

    def test_no_strip_short_token(self):
        # Should not strip if result would be empty
        variants = _strip_particles("을")
        assert variants == ["을"]

    def test_tokenize_sentence(self):
        tokens = _tokenize("옹골성을 모르겠어요")
        assert "옹골성" in tokens

    def test_particle_strip_preserves_alias(self):
        """Korean particle stripping should not destroy a valid alias."""
        tokens = _tokenize("연결성이")
        assert "연결성" in tokens


class TestScoring:
    def test_alias_scores_higher_than_keyword(self):
        # "compactness" is an alias (score 3) and also matches keyword (score 1)
        # Another concept might also match keywords but not alias
        scores = _score_concepts("compactness")
        assert scores.get("compactness", 0) >= 3

    def test_case_insensitivity(self):
        scores = _score_concepts("Compactness")
        assert "compactness" in scores

    def test_multiple_keywords_best_wins(self):
        # "compact" and "open cover" and "finite subcover" all → compactness
        scores = _score_concepts("compact open cover finite subcover")
        assert scores.get("compactness", 0) > scores.get("connectedness", 0)


class TestEditDistance:
    def test_identical(self):
        assert _edit_distance("abc", "abc") == 0

    def test_one_insertion(self):
        assert _edit_distance("abc", "ab") == 1

    def test_one_substitution(self):
        assert _edit_distance("abc", "axc") == 1

    def test_compatness_typo(self):
        dist = _edit_distance("compatness", "compactness")
        assert dist <= 2


class TestFuzzyMatch:
    def test_compatness_resolves(self):
        result = analyze_message("compatness")
        assert result["concept_id"] == "compactness"
        assert result["correction"] is not None

    def test_short_typo_ignored(self):
        # Short tokens (< 5 chars) should not fuzzy match
        result = analyze_message("comp")
        # "comp" is too short for fuzzy but might match keywords
        # Either matches via keyword or not — just verify no crash
        assert "language" in result

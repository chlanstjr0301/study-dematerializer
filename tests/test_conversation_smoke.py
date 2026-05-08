"""
Smoke tests for the conversation layer fix.

Tests the full analyze_message path for:
1. Greeting → bubble response
2. Definition with "뭐임" → bubble with direct answer
3. Definition with "뭐냐고" (concept in message) → bubble
4. Followup "뭐냐고" with context → bubble with concept answer
5. Followup "설명을 해봐" with context → bubble
6. Study start intent → card
7. Gibberish → unsupported, card
8. Active concept resolution from recent messages
"""
from __future__ import annotations

import pytest

from apps.api.services.compiler_analyzer_service import analyze_message


class TestGreeting:
    """Greetings must return bubble-only responses."""

    def test_안녕(self):
        result = analyze_message("안녕")
        assert result["intent"] == "greeting"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None
        assert "공해분" in result["direct_answer"]

    def test_하이(self):
        result = analyze_message("하이")
        assert result["intent"] == "greeting"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None

    def test_안녕하세요(self):
        result = analyze_message("안녕하세요")
        assert result["intent"] == "greeting"
        assert result["render_mode"] == "bubble"


class TestDefinitionQuestion:
    """Definition questions must return bubble with direct_answer."""

    def test_compactness가_뭐임(self):
        result = analyze_message("compactness가 뭐임")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None
        assert "열린 덮개" in result["direct_answer"]

    def test_compactness가_뭐냐고(self):
        result = analyze_message("compactness가 뭐냐고")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None

    def test_옹골성이_뭐임(self):
        result = analyze_message("옹골성이 뭐임")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "bubble"


class TestFollowupRepair:
    """Followups with context must resolve active concept and produce bubble."""

    def test_뭐냐고_with_compactness_context(self):
        result = analyze_message("뭐냐고", recent_messages=["compactness 알려줘"])
        assert result["intent"] == "followup_repair"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None

    def test_설명을_해봐_with_context(self):
        result = analyze_message("설명을 해봐", recent_messages=["compactness"])
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "bubble"
        assert result["direct_answer"] is not None

    def test_다시_설명_with_context(self):
        result = analyze_message("다시 설명해봐", recent_messages=["연결성이 뭐야?"])
        assert result["intent"] == "followup_repair"
        assert result["concept_id"] == "connectedness"
        assert result["render_mode"] == "bubble"


class TestConceptLookup:
    """Pure concept lookups still produce card mode."""

    def test_bare_alias_card_mode(self):
        result = analyze_message("옹골성")
        assert result["intent"] == "concept_lookup"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "card"
        assert result["direct_answer"] is None
        assert result["representations"] is not None

    def test_study_start_card_mode(self):
        """'compactness를 공부해보자' → start_study_session, card."""
        result = analyze_message("그래 compactness를 공부 시작")
        assert result["intent"] == "start_study_session"
        assert result["concept_id"] == "compactness"
        assert result["render_mode"] == "card"


class TestUnsupported:
    """Gibberish/unsupported input."""

    def test_gibberish(self):
        result = analyze_message("asdfghjkl")
        assert result["intent"] == "unsupported"
        assert result["concept_id"] is None
        # No direct answer for unsupported → card (shows NoMatchCard)
        assert result["render_mode"] == "card"

    def test_unrelated_question(self):
        result = analyze_message("오늘 날씨 어때?")
        assert result["intent"] == "unsupported"
        assert result["render_mode"] == "card"


class TestRenderModeBackwardCompat:
    """Existing concept_lookup behavior unchanged."""

    def test_concept_lookup_still_has_all_fields(self):
        result = analyze_message("옹골성")
        # All existing fields still present
        assert "language" in result
        assert "prerequisite_checks" in result
        assert "recommended_actions" in result
        assert "representations" in result
        assert result["representations"] is not None

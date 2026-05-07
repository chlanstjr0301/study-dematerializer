"""
Tests for MVP6-Hotfix: Intent router — conversation-first concept entry.
"""
from __future__ import annotations

import pytest

from apps.api.services.intent_router import classify_intent, generate_direct_answer


class TestClassifyIntent:
    """Test deterministic intent classification."""

    def test_alias_equivalence_korean_english(self):
        """'compactness가 옹골성이야?' → alias_equivalence_question."""
        result = classify_intent("compactness가 옹골성이야?")
        assert result["intent"] == "alias_equivalence_question"
        assert result["concept_id"] == "compactness"

    def test_alias_equivalence_with_question_mark(self):
        result = classify_intent("옹골성이 compactness인가요?")
        assert result["intent"] == "alias_equivalence_question"
        assert result["concept_id"] == "compactness"

    def test_definition_question_korean(self):
        """'옹골성이 뭐야?' → definition_question."""
        result = classify_intent("옹골성이 뭐야?")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"

    def test_definition_question_what_is(self):
        result = classify_intent("what is compactness?")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"

    def test_definition_question_explain(self):
        result = classify_intent("옹골성 설명해줘")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"

    def test_followup_repair_with_context(self):
        """'물어보잖아' after alias question → followup_repair."""
        recent = ["compactness가 옹골성이야?"]
        result = classify_intent("물어보잖아", recent_messages=recent)
        assert result["intent"] == "followup_repair"
        assert result["concept_id"] == "compactness"

    def test_followup_repair_다시_설명(self):
        recent = ["연결성이 뭐야?"]
        result = classify_intent("다시 설명해봐", recent_messages=recent)
        assert result["intent"] == "followup_repair"
        assert result["concept_id"] == "connectedness"

    def test_unsupported_random_input(self):
        """Random unsupported input with no context → unsupported."""
        result = classify_intent("오늘 날씨 어때?")
        assert result["intent"] == "unsupported"
        assert result["concept_id"] is None

    def test_unsupported_no_context(self):
        result = classify_intent("물어보잖아")
        assert result["intent"] in ("unsupported", "followup_repair")
        # Without recent_messages, followup won't have concept context
        if result["intent"] == "followup_repair":
            assert result["concept_id"] is None

    def test_concept_lookup_bare_alias(self):
        """Pure alias without special intent → concept_lookup."""
        result = classify_intent("옹골성")
        assert result["intent"] == "concept_lookup"
        assert result["concept_id"] == "compactness"

    def test_concept_lookup_with_gap_cue(self):
        """Alias + gap cue but not definition pattern → concept_lookup."""
        result = classify_intent("옹골성에서 finite subcover가 왜 중요한지 모르겠어")
        # This has both concept alias and cue words but no definition/equivalence pattern
        assert result["concept_id"] == "compactness"

    def test_difference_question(self):
        result = classify_intent("연결성과 옹골성의 차이가 뭐야?")
        assert result["intent"] == "difference_question"
        assert len(result["all_concepts"]) >= 2

    def test_start_study_session(self):
        result = classify_intent("옹골성 공부 시작")
        assert result["intent"] == "start_study_session"
        assert result["concept_id"] == "compactness"

    def test_start_recall(self):
        result = classify_intent("연결성 인출 연습")
        assert result["intent"] == "start_recall"
        assert result["concept_id"] == "connectedness"

    def test_extra_alias_컴팩트성(self):
        result = classify_intent("컴팩트성이 뭐야?")
        assert result["concept_id"] == "compactness"

    def test_extra_alias_균등연속(self):
        result = classify_intent("균등연속이 뭐야?")
        assert result["concept_id"] == "uniform_continuity"


class TestGenerateDirectAnswer:
    """Test Korean direct answer generation."""

    def test_alias_equivalence_answer(self):
        answer = generate_direct_answer(
            "alias_equivalence_question", "compactness",
            "compactness가 옹골성이야?",
        )
        assert answer is not None
        assert "옹골성" in answer
        assert "열린 덮개" in answer or "유한 부분덮개" in answer

    def test_definition_answer_contains_key_terms(self):
        """Definition answer for compactness must contain 열린 덮개 and 유한 부분덮개."""
        answer = generate_direct_answer(
            "definition_question", "compactness",
            "옹골성이 뭐야?",
        )
        assert answer is not None
        assert "열린 덮개" in answer
        assert "유한 부분덮개" in answer

    def test_followup_repair_with_concept(self):
        answer = generate_direct_answer(
            "followup_repair", "compactness",
            "물어보잖아",
            recent_messages=["compactness가 옹골성이야?"],
        )
        assert answer is not None
        assert "죄송" in answer or "답변" in answer

    def test_followup_repair_no_concept(self):
        answer = generate_direct_answer(
            "followup_repair", None,
            "물어보잖아",
        )
        assert answer is not None
        assert "다시" in answer or "질문" in answer

    def test_concept_lookup_returns_none(self):
        answer = generate_direct_answer(
            "concept_lookup", "compactness",
            "옹골성",
        )
        assert answer is None

    def test_unsupported_returns_none(self):
        answer = generate_direct_answer(
            "unsupported", None,
            "오늘 날씨 어때?",
        )
        assert answer is None


class TestIntentRouterIntegration:
    """Test integration via analyze_message."""

    def test_alias_equivalence_via_analyze(self):
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message("compactness가 옹골성이야?")
        assert result["intent"] == "alias_equivalence_question"
        assert result["concept_id"] == "compactness"
        assert result["direct_answer"] is not None
        assert "옹골성" in result["direct_answer"]

    def test_definition_via_analyze(self):
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message("옹골성이 뭐야?")
        assert result["intent"] == "definition_question"
        assert result["concept_id"] == "compactness"
        assert result["direct_answer"] is not None
        assert "열린 덮개" in result["direct_answer"]
        assert "유한 부분덮개" in result["direct_answer"]

    def test_followup_via_analyze(self):
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message(
            "물어보잖아",
            recent_messages=["compactness가 옹골성이야?"],
        )
        assert result["intent"] == "followup_repair"
        assert result["direct_answer"] is not None

    def test_unsupported_via_analyze(self):
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message("오늘 날씨 어때?")
        assert result["intent"] == "unsupported"

    def test_concept_lookup_backward_compat(self):
        """Plain alias still works as concept_lookup (existing behavior)."""
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message("옹골성")
        assert result["intent"] == "concept_lookup"
        assert result["concept_id"] == "compactness"
        assert result["direct_answer"] is None  # No direct answer for lookup
        # Existing fields still present
        assert result["representations"] is not None
        assert result["prerequisite_checks"] is not None

    def test_no_unsupported_for_known_alias_in_sentence(self):
        """'compactness가 옹골성이야?' must NOT return unsupported."""
        from apps.api.services.compiler_analyzer_service import analyze_message

        result = analyze_message("compactness가 옹골성이야?")
        assert result["intent"] != "unsupported"
        assert result["concept_id"] == "compactness"

"""
Tests for MVP6-Hotfix: Gibberish/blank answer guard and grader provenance.
"""
from __future__ import annotations

import pytest

from apps.api.services.study_session_service import _is_gibberish


class TestIsGibberish:
    """Test the gibberish detection utility."""

    def test_empty_string(self):
        assert _is_gibberish("") is True

    def test_whitespace_only(self):
        assert _is_gibberish("   \t\n  ") is True

    def test_punctuation_only(self):
        assert _is_gibberish("!@#$%^&*()") is True

    def test_symbols_only(self):
        assert _is_gibberish("□■○●◆◇★☆") is True

    def test_jamo_only(self):
        """Korean consonants/vowels without forming syllables."""
        assert _is_gibberish("ㄴㅇㄹㅇㄹㅇㄹ") is True

    def test_keyboard_smash(self):
        """Repetitive characters = keyboard smash."""
        assert _is_gibberish("aaaaaaaaa") is True

    def test_too_short(self):
        assert _is_gibberish("ab") is True
        assert _is_gibberish("옹골") is True  # 2 chars

    def test_valid_korean_math(self):
        assert _is_gibberish("옹골 집합은 모든 열린 덮개가 유한 부분덮개를 가진다") is False

    def test_valid_english_math(self):
        assert _is_gibberish("A compact set has finite subcover for every open cover") is False

    def test_valid_short_but_meaningful(self):
        """5+ chars with enough variety should pass."""
        assert _is_gibberish("열린 덮개") is False

    def test_mixed_gibberish(self):
        assert _is_gibberish("□ ㄴㅇㄹㅇㄹㅇㄹ...") is True

    def test_numbers_only(self):
        assert _is_gibberish("123456") is True

    def test_digits_with_punctuation(self):
        assert _is_gibberish("1.2.3.4.5") is True


class TestGibberishGuardIntegration:
    """Test gibberish guard through study session API endpoints."""

    @pytest.fixture
    def session_env(self, tmp_path, monkeypatch):
        """Set up a minimal study session environment."""
        import apps.api.services.study_session_service as svc
        import apps.api.config as config
        import json

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        bank_root = tmp_path / "banks"
        bank_root.mkdir()
        study_md = tmp_path / "STUDY.md"
        study_md.write_text("# STUDY\n", encoding="utf-8")

        monkeypatch.setattr(config, "RUNS_DIR", runs_dir)
        monkeypatch.setattr(config, "BANK_ROOT", bank_root)
        monkeypatch.setattr(config, "STUDY_MD", study_md)
        monkeypatch.setattr(config, "SOURCES_DIR", tmp_path / "sources")
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path)

        # Force mock LLM
        monkeypatch.setenv("GONGHAEBUN_LLM_DISABLED", "1")

        return tmp_path, runs_dir

    def _create_session(self, session_env):
        """Create a session and return session_id."""
        import apps.api.services.study_session_service as svc
        import json

        tmp_path, runs_dir = session_env
        result = svc.create_study_session(
            concept_id="compactness",
            runs_dir=runs_dir,
            sources_dir=tmp_path / "sources",
            bank_root=tmp_path / "banks",
            study_md_path=tmp_path / "STUDY.md",
            data_root=tmp_path,
        )
        return result["session_id"]

    def _advance_to_recall(self, session_id, runs_dir):
        """Advance session to recall step, handling mapping tasks."""
        import apps.api.services.study_session_service as svc
        import json

        svc.submit_diagnosis(session_id, "", "", runs_dir=runs_dir)
        svc.advance_step(session_id, "prerequisites", runs_dir=runs_dir)
        svc.advance_step(session_id, "representations", runs_dir=runs_dir)

        # Submit mapping tasks if they exist (required to advance past mapping)
        session_dir = runs_dir / session_id
        tasks_path = session_dir / "mapping_tasks.json"
        if tasks_path.exists():
            tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
            results = []
            for t in tasks:
                results.append({
                    "task_id": t["task_id"],
                    "score": 0.8,
                    "passed": True,
                    "missing_elements": [],
                    "misconception_tags": [],
                    "mapping_failures": [],
                    "feedback": "test",
                    "next_recall_trigger": "",
                })
            results_path = session_dir / "mapping_results.json"
            results_path.write_text(json.dumps(results), encoding="utf-8")

        svc.advance_step(session_id, "mapping", runs_dir=runs_dir)
        svc.advance_step(session_id, "misconceptions", runs_dir=runs_dir)

    def test_gibberish_recall_scores_zero(self, session_env):
        """Gibberish recall answer → score 0.0, grader_source=invalid_answer."""
        import apps.api.services.study_session_service as svc

        session_id = self._create_session(session_env)
        _, runs_dir = session_env
        self._advance_to_recall(session_id, runs_dir)

        # Submit gibberish recall
        result = svc.submit_recall(
            session_id=session_id,
            learner_response="□ ㄴㅇㄹㅇㄹㅇㄹ...",
            runs_dir=runs_dir,
        )
        assert result["accuracy_score"] == 0.0
        assert result["grader_source"] == "invalid_answer"
        assert "의미 있는" in result["feedback"] or "비어 있거나" in result["feedback"]

    def test_gibberish_self_explain_scores_zero(self, session_env):
        """Gibberish self-explanation → score 0.0, grader_source=invalid_answer."""
        import apps.api.services.study_session_service as svc

        session_id = self._create_session(session_env)
        _, runs_dir = session_env

        result = svc.submit_self_explanation(
            session_id=session_id,
            representation_type="formal",
            learner_explanation="ㅋㅋㅋㅋㅋㅋ",
            runs_dir=runs_dir,
        )
        assert result["accuracy_score"] == 0.0
        assert result["grader_source"] == "invalid_answer"

    def test_gibberish_no_positive_feedback(self, session_env):
        """Gibberish must not receive content-specific positive feedback."""
        import apps.api.services.study_session_service as svc

        session_id = self._create_session(session_env)
        _, runs_dir = session_env
        self._advance_to_recall(session_id, runs_dir)

        result = svc.submit_recall(
            session_id=session_id,
            learner_response="aaaaaa",
            runs_dir=runs_dir,
        )
        # No positive content-specific feedback
        feedback = result["feedback"]
        assert "잘" not in feedback
        assert "good" not in feedback.lower()
        assert "정의" not in feedback or "비어" in feedback

    def test_valid_recall_has_grader_source(self, session_env):
        """Valid recall answer must include grader_source field."""
        import apps.api.services.study_session_service as svc

        session_id = self._create_session(session_env)
        _, runs_dir = session_env
        self._advance_to_recall(session_id, runs_dir)

        result = svc.submit_recall(
            session_id=session_id,
            learner_response="옹골 집합은 모든 열린 덮개가 유한 부분덮개를 가지는 집합이다. Heine-Borel에 의해 R^n에서 닫히고 유계이면 옹골이다.",
            runs_dir=runs_dir,
        )
        assert "grader_source" in result
        assert result["grader_source"] in ("mock", "llm", "deterministic", "invalid_answer")

    def test_valid_self_explain_has_grader_source(self, session_env):
        """Valid self-explanation must include grader_source."""
        import apps.api.services.study_session_service as svc

        session_id = self._create_session(session_env)
        _, runs_dir = session_env

        result = svc.submit_self_explanation(
            session_id=session_id,
            representation_type="formal",
            learner_explanation="옹골 집합은 모든 열린 덮개가 유한 부분덮개를 가지는 집합이다.",
            runs_dir=runs_dir,
        )
        assert "grader_source" in result
        assert result["grader_source"] in ("mock", "llm")

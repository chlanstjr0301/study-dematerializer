"""Tests for grading/trace_models.py (MVP4-J0)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gonghaebun.grading.trace_models import (
    LLMAttemptRecord,
    LLMTraceRecord,
    write_trace_artifacts,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = "2026-05-05T12:00:00+00:00"
_SENTINEL = object()  # distinct from None for optional dict params


def _attempt(
    call_index: int = 0,
    parsed_ok: bool = True,
    fallback: bool = False,
    llm_output: dict | None | object = _SENTINEL,
    error_message: str | None = None,
) -> LLMAttemptRecord:
    if llm_output is _SENTINEL:
        llm_output = {"accuracy_score": 0.75}
    return LLMAttemptRecord(
        call_index=call_index,
        prompt_hash="sha256:abc123",
        parsed_ok=parsed_ok,
        fallback=fallback,
        duration_ms=300.0,
        structured_output_used=True,
        llm_output=llm_output,  # type: ignore[arg-type]
        error_message=error_message,
        created_at=_NOW,
    )


def _trace(
    question_id: str = "q_001",
    attempts: list[LLMAttemptRecord] | None = None,
) -> LLMTraceRecord:
    return LLMTraceRecord(
        question_id=question_id,
        concept_id="compactness",
        representation_type="formal",
        model="gpt-5.4-mini",
        attempts=attempts or [_attempt()],
    )


# ---------------------------------------------------------------------------
# TestLLMAttemptRecord
# ---------------------------------------------------------------------------


class TestLLMAttemptRecord:
    def test_valid_instantiation(self):
        rec = _attempt()
        assert rec.call_index == 0
        assert rec.parsed_ok is True
        assert rec.fallback is False

    def test_structured_output_used_can_be_true(self):
        rec = _attempt()
        assert rec.structured_output_used is True

    def test_structured_output_used_can_be_false(self):
        rec = LLMAttemptRecord(
            call_index=0,
            prompt_hash="sha256:x",
            parsed_ok=False,
            fallback=True,
            duration_ms=None,
            structured_output_used=False,
            llm_output=None,
            error_message="timeout",
            created_at=_NOW,
        )
        assert rec.structured_output_used is False

    def test_duration_ms_can_be_none(self):
        rec = LLMAttemptRecord(
            call_index=0,
            prompt_hash="sha256:x",
            parsed_ok=False,
            fallback=True,
            duration_ms=None,
            structured_output_used=True,
            llm_output=None,
            error_message="no call made",
            created_at=_NOW,
        )
        assert rec.duration_ms is None

    def test_llm_output_can_be_none(self):
        rec = _attempt(parsed_ok=False, llm_output=None, error_message="bad schema")
        assert rec.llm_output is None

    def test_error_message_can_be_none(self):
        rec = _attempt(parsed_ok=True, error_message=None)
        assert rec.error_message is None


# ---------------------------------------------------------------------------
# TestLLMTraceRecord
# ---------------------------------------------------------------------------


class TestLLMTraceRecord:
    def test_valid_instantiation(self):
        tr = _trace()
        assert tr.question_id == "q_001"
        assert tr.concept_id == "compactness"
        assert tr.representation_type == "formal"
        assert tr.model == "gpt-5.4-mini"

    def test_attempts_is_list(self):
        tr = _trace()
        assert isinstance(tr.attempts, list)

    def test_single_attempt(self):
        tr = _trace(attempts=[_attempt(call_index=0)])
        assert len(tr.attempts) == 1

    def test_two_attempts_retry(self):
        tr = _trace(attempts=[
            _attempt(call_index=0, parsed_ok=False, error_message="bad schema"),
            _attempt(call_index=1, parsed_ok=True),
        ])
        assert len(tr.attempts) == 2
        assert tr.attempts[0].call_index == 0
        assert tr.attempts[1].call_index == 1


# ---------------------------------------------------------------------------
# TestWriteTraceArtifacts
# ---------------------------------------------------------------------------


class TestWriteTraceArtifacts:
    def test_empty_traces_creates_no_dir(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([], traces_dir)
        assert not traces_dir.exists()

    def test_creates_traces_dir(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_001")], traces_dir)
        assert traces_dir.is_dir()

    def test_one_file_per_question(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        traces = [_trace("q_001"), _trace("q_002"), _trace("q_003")]
        write_trace_artifacts(traces, traces_dir)
        files = list(traces_dir.iterdir())
        assert len(files) == 3

    def test_file_named_by_question_id(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_my_question")], traces_dir)
        assert (traces_dir / "q_my_question.json").exists()

    def test_file_contains_attempts_key(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_001")], traces_dir)
        data = json.loads((traces_dir / "q_001.json").read_text("utf-8"))
        assert "attempts" in data
        assert isinstance(data["attempts"], list)

    def test_file_with_two_attempts_has_both(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        trace = _trace("q_retry", attempts=[
            _attempt(call_index=0, parsed_ok=False, error_message="bad schema"),
            _attempt(call_index=1, parsed_ok=True),
        ])
        write_trace_artifacts([trace], traces_dir)
        data = json.loads((traces_dir / "q_retry.json").read_text("utf-8"))
        assert len(data["attempts"]) == 2
        assert data["attempts"][0]["call_index"] == 0
        assert data["attempts"][0]["parsed_ok"] is False
        assert data["attempts"][1]["call_index"] == 1
        assert data["attempts"][1]["parsed_ok"] is True

    def test_prompt_hash_in_file_not_raw_prompt(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_001")], traces_dir)
        raw = (traces_dir / "q_001.json").read_text("utf-8")
        assert "prompt_hash" in raw
        assert "sha256:" in raw
        # No raw prompt text should appear
        assert "__fixture__" not in raw

    def test_raw_response_not_in_file(self, tmp_path):
        """raw_response must NEVER be written to disk."""
        traces_dir = tmp_path / "llm_traces"
        trace = _trace("q_001")
        write_trace_artifacts([trace], traces_dir)
        raw = (traces_dir / "q_001.json").read_text("utf-8")
        assert "raw_response" not in raw

    def test_three_questions_three_files(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        traces = [_trace(f"q_{i}") for i in range(3)]
        write_trace_artifacts(traces, traces_dir)
        for i in range(3):
            assert (traces_dir / f"q_{i}.json").exists()

    def test_file_contains_question_id_field(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("my_q_id")], traces_dir)
        data = json.loads((traces_dir / "my_q_id.json").read_text("utf-8"))
        assert data["question_id"] == "my_q_id"

    def test_file_contains_concept_id(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_001")], traces_dir)
        data = json.loads((traces_dir / "q_001.json").read_text("utf-8"))
        assert data["concept_id"] == "compactness"

    def test_structured_output_used_in_file(self, tmp_path):
        traces_dir = tmp_path / "llm_traces"
        write_trace_artifacts([_trace("q_001")], traces_dir)
        data = json.loads((traces_dir / "q_001.json").read_text("utf-8"))
        assert data["attempts"][0]["structured_output_used"] is True

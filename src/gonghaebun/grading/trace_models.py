"""
LLM trace models: in-memory records + artifact writer.

One LLMTraceRecord is created per question graded with the LLM grader.
Each record holds an `attempts` list (1 entry on success, 2 entries on retry).

Artifacts are written as one JSON file per question under llm_traces/.
File name: {question_id}.json

Design constraints:
- raw_response is NEVER written to disk.
- API keys are NEVER written to disk.
- Prompt text is NEVER written to disk; only prompt_hash is stored.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LLMAttemptRecord:
    """Record of one LLM API call for a single question."""

    call_index: int               # 0 = first attempt, 1 = retry
    prompt_hash: str              # "sha256:..." of (system + user); NOT raw prompt text
    parsed_ok: bool               # True if structured output passed schema validation
    fallback: bool                # True if needs_human_review was forced by failure
    duration_ms: float | None     # wall-clock ms for the LLM call; None if no call made
    structured_output_used: bool  # True if provider-level JSON schema was sent
    llm_output: dict | None       # serialized LLMGradingOutput if parsed_ok, else None
    error_message: str | None     # description if parsed_ok=False
    created_at: str               # ISO 8601 timestamp


@dataclass
class LLMTraceRecord:
    """Trace for one question's grading (1 or 2 attempts)."""

    question_id: str
    concept_id: str
    representation_type: str
    model: str
    attempts: list[LLMAttemptRecord]


def write_trace_artifacts(
    traces: list[LLMTraceRecord],
    traces_dir: Path,
) -> None:
    """
    Write one JSON file per question under traces_dir/.

    Each file is named {question_id}.json and contains the full trace record
    including all attempt records in an "attempts" array.

    raw_response, API keys, and prompt text are NEVER written.
    Empty traces list → traces_dir is not created.
    """
    if not traces:
        return

    traces_dir.mkdir(parents=True, exist_ok=True)

    for trace in traces:
        record = {
            "question_id": trace.question_id,
            "concept_id": trace.concept_id,
            "representation_type": trace.representation_type,
            "model": trace.model,
            "attempts": [
                {
                    "call_index": a.call_index,
                    "prompt_hash": a.prompt_hash,
                    "parsed_ok": a.parsed_ok,
                    "fallback": a.fallback,
                    "duration_ms": a.duration_ms,
                    "structured_output_used": a.structured_output_used,
                    "llm_output": a.llm_output,
                    "error_message": a.error_message,
                    "created_at": a.created_at,
                }
                for a in trace.attempts
            ],
        }
        out_path = traces_dir / f"{trace.question_id}.json"
        out_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

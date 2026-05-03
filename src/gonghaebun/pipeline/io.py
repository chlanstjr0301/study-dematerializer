"""
MVP2 I/O layer: save and load question-bank artifacts as JSON.

All helpers write UTF-8 JSON with indent=2 and ensure_ascii=False.
Parent directories are created automatically.
Records are sorted by stable id before writing; input lists are not mutated.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from gonghaebun.models.question_bank import Question, ReviewRecord, SourceBlock

# ---------------------------------------------------------------------------
# SourceBlock
# ---------------------------------------------------------------------------


def save_blocks(path: Path, blocks: list[SourceBlock]) -> None:
    """Write blocks to path as a JSON array, sorted by block_id."""
    sorted_blocks = sorted(blocks, key=lambda b: b.block_id)
    _write_json(path, [dataclasses.asdict(b) for b in sorted_blocks])


def load_blocks(path: Path) -> list[SourceBlock]:
    """Load SourceBlocks from a JSON array. Raises ValueError if not a list."""
    data = _read_json(path, label="blocks")
    return [SourceBlock(**item) for item in data]


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------


def save_questions(path: Path, questions: list[Question]) -> None:
    """Write questions to path as a JSON array, sorted by question_id."""
    sorted_questions = sorted(questions, key=lambda q: q.question_id)
    _write_json(path, [dataclasses.asdict(q) for q in sorted_questions])


def load_questions(path: Path) -> list[Question]:
    """Load Questions from a JSON array. Raises ValueError if not a list.

    Question.__post_init__ automatically converts the evidence dict → Evidence.
    """
    data = _read_json(path, label="questions")
    return [Question(**item) for item in data]


# ---------------------------------------------------------------------------
# ReviewRecord
# ---------------------------------------------------------------------------


def save_review_records(path: Path, records: list[ReviewRecord]) -> None:
    """Write review records to path as a JSON array, sorted by review_id."""
    sorted_records = sorted(records, key=lambda r: r.review_id)
    _write_json(path, [dataclasses.asdict(r) for r in sorted_records])


def load_review_records(path: Path) -> list[ReviewRecord]:
    """Load ReviewRecords from a JSON array. Raises ValueError if not a list."""
    data = _read_json(path, label="review_records")
    return [ReviewRecord(**item) for item in data]


# ---------------------------------------------------------------------------
# Export accepted
# ---------------------------------------------------------------------------


def export_accepted(questions: list[Question], out_path: Path) -> list[Question]:
    """Write only accepted questions to out_path. Returns the accepted list."""
    accepted = [q for q in questions if q.status == "accepted"]
    save_questions(out_path, accepted)
    return accepted


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _read_json(path: Path, label: str) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected a JSON list for {label} at {path!s}, "
            f"got {type(raw).__name__}"
        )
    return raw

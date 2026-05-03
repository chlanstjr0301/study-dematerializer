"""
MVP 2 data models: SourceBlock, Evidence, Question, Rule, ReviewRecord.

All dataclasses include __post_init__ validation that raises ValueError for
invalid Literal field values. typing.Literal does not enforce values at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Valid value sets (used in __post_init__ validation)
# ---------------------------------------------------------------------------

BLOCK_TYPES: frozenset[str] = frozenset({
    "definition", "theorem", "proof", "example", "paragraph", "exercise", "unknown"
})
QUESTION_STATUSES: frozenset[str] = frozenset({
    "candidate", "accepted", "rejected", "edited", "skipped"
})
REVIEW_ACTIONS: frozenset[str] = frozenset({"accept", "reject", "edit", "skip"})
DIFFICULTIES: frozenset[str] = frozenset({"easy", "medium", "hard"})

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

BlockType = Literal[
    "definition", "theorem", "proof", "example",
    "paragraph", "exercise", "unknown"
]
QuestionStatus = Literal["candidate", "accepted", "rejected", "edited", "skipped"]
ReviewAction = Literal["accept", "reject", "edit", "skip"]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    """Structured source traceability attached to every Question."""

    source_text: str        # Full SourceBlock text (preserves traceability)
    source_file: str        # Relative path from project root
    start_line: int | None
    end_line: int | None
    text_hash: str          # sha256 hex digest of source_text

    def __post_init__(self) -> None:
        if not self.source_text:
            raise ValueError("Evidence.source_text must not be empty")


# ---------------------------------------------------------------------------
# SourceBlock
# ---------------------------------------------------------------------------

@dataclass
class SourceBlock:
    """
    A structured text block extracted from a source document.

    block_id is positional: f"{document_id}_b{index:06d}".
    Use text_hash for content-identity across runs.
    """

    block_id: str           # "{document_id}_b{index:06d}"
    document_id: str        # Slug of source filename (no extension)
    source_file: str        # Relative path from project root
    section_title: str      # Nearest Markdown heading above this block, or ""
    block_type: BlockType
    start_line: int | None
    end_line: int | None
    text: str
    text_hash: str          # sha256 hex digest of text

    def __post_init__(self) -> None:
        if self.block_type not in BLOCK_TYPES:
            raise ValueError(
                f"Invalid block_type: {self.block_type!r}. "
                f"Valid values: {sorted(BLOCK_TYPES)}"
            )
        if not self.text.strip():
            raise ValueError("SourceBlock.text must not be empty")


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """Describes a question-generation template."""

    rule_id: str
    target_block_type: str  # block_type from BLOCK_TYPES, or "any"
    question_type: str
    difficulty: str
    generator_name: str     # Name of the template/function that produces the question
    version: str

    def __post_init__(self) -> None:
        valid_targets = BLOCK_TYPES | {"any"}
        if self.target_block_type not in valid_targets:
            raise ValueError(
                f"Invalid target_block_type: {self.target_block_type!r}. "
                f"Valid values: {sorted(valid_targets)}"
            )
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty: {self.difficulty!r}. "
                f"Valid values: {sorted(DIFFICULTIES)}"
            )


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

@dataclass
class Question:
    """
    A generated question with full source traceability.

    question_id is deterministic: f"q_{source_block_id}_{rule_id}".
    expected_answer is source-grounded (SourceBlock text, ≤ 800 chars).
    Limitation: expected_answer is not a model-generated answer; it is the
    source passage that the question was derived from.
    """

    question_id: str        # f"q_{source_block_id}_{rule_id}"
    document_id: str
    source_block_id: str
    question_type: str
    difficulty: str
    question: str
    expected_answer: str    # Source-grounded; ≤ 800 chars of SourceBlock.text
    evidence: Evidence      # Structured source traceability (not a plain string)
    rule_id: str
    status: QuestionStatus = "candidate"
    created_at: str = ""    # ISO 8601
    updated_at: str = ""    # ISO 8601

    def __post_init__(self) -> None:
        # Auto-convert evidence dict → Evidence (enables JSON roundtrip via dataclasses.asdict)
        if isinstance(self.evidence, dict):
            self.evidence = Evidence(**self.evidence)
        if self.status not in QUESTION_STATUSES:
            raise ValueError(
                f"Invalid status: {self.status!r}. "
                f"Valid values: {sorted(QUESTION_STATUSES)}"
            )
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty: {self.difficulty!r}. "
                f"Valid values: {sorted(DIFFICULTIES)}"
            )


# ---------------------------------------------------------------------------
# ReviewRecord
# ---------------------------------------------------------------------------

@dataclass
class ReviewRecord:
    """Records one human review action on a Question."""

    review_id: str              # f"rev_{question_id}_{index}"
    question_id: str
    action: ReviewAction
    before_question: str
    after_question: str | None  # Set only when action == "edit"
    before_expected_answer: str
    after_expected_answer: str | None  # Set only when action == "edit"
    reviewed_at: str            # ISO 8601

    def __post_init__(self) -> None:
        if self.action not in REVIEW_ACTIONS:
            raise ValueError(
                f"Invalid action: {self.action!r}. "
                f"Valid values: {sorted(REVIEW_ACTIONS)}"
            )

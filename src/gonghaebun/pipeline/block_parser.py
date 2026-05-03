"""
Stage A (MVP2): Markdown Block Parser.

Parses a Markdown/text source file into a list of SourceBlock objects.
Fully deterministic — no LLM calls.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from gonghaebun.models.question_bank import BlockType, SourceBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_NON_WS: int = 50  # Minimum non-whitespace characters for a block to be kept

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^#{1,6}\s+")

# All pattern checks are applied via re.match() to the FIRST non-empty line
# of each block after stripping leading bold/italic markers (^\*+).
# Using match() (start-anchored) avoids false positives from words like
# "definition" or "theorem" appearing as common prose inside a block.

# Proof: first non-empty line (stripped) starts with Proof / 증명
_PROOF_BARE_RE = re.compile(r"(Proof|증명)\b", re.IGNORECASE)

# Theorem-family: first line starts with Theorem, Lemma, Proposition, Corollary, or Korean equivalents
_THEOREM_START_RE = re.compile(
    r"(Theorem|Lemma|Proposition|Corollary)\b|정리|보조정리|명제|따름정리",
    re.IGNORECASE,
)
# Definition: first line starts with Definition, Def., or Korean equivalent
_DEFINITION_START_RE = re.compile(r"(Definition|Def\.)\b|정의", re.IGNORECASE)
_EXAMPLE_START_RE = re.compile(r"Example\b|예제", re.IGNORECASE)
_EXERCISE_START_RE = re.compile(r"(Exercise|Problem)\b|연습문제|문제", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_blocks(source_path: Path, document_id: str) -> list[SourceBlock]:
    """
    Parse a Markdown/text source file into SourceBlock objects.

    Splitting rules:
    - Blank lines delimit blocks.
    - Markdown headings (^#{1,6}\\s+) update the running section_title and are
      NOT emitted as blocks themselves.
    - Blocks with < 50 non-whitespace characters are discarded.

    Block IDs are positional and deterministic:
      block_id = f"{document_id}_b{index:06d}"  (index starts at 1)

    source_file is the relative path from CWD when possible, else the filename.
    """
    text = source_path.read_text(encoding="utf-8")
    source_file = _relative_path(source_path)
    return _parse(text, document_id, source_file)


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _parse(text: str, document_id: str, source_file: str) -> list[SourceBlock]:
    lines = text.splitlines()

    blocks: list[SourceBlock] = []
    current_section: str = ""
    current_lines: list[str] = []
    current_start: int | None = None
    last_content_line: int | None = None
    block_index: int = 0

    def _emit() -> None:
        nonlocal block_index
        if not current_lines:
            return
        block_text = "\n".join(current_lines)
        non_ws = sum(1 for c in block_text if not c.isspace())
        if non_ws < _MIN_NON_WS:
            return
        block_index += 1
        blocks.append(
            SourceBlock(
                block_id=f"{document_id}_b{block_index:06d}",
                document_id=document_id,
                source_file=source_file,
                section_title=current_section,
                block_type=_classify(block_text),
                start_line=current_start,
                end_line=last_content_line,
                text=block_text,
                text_hash=hashlib.sha256(block_text.encode("utf-8")).hexdigest(),
            )
        )

    for line_num, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            # Emit any pending block, then update section title
            _emit()
            current_lines = []
            current_start = None
            last_content_line = None
            current_section = line[m.end() :].strip()
        elif not line.strip():
            # Blank line — separator
            _emit()
            current_lines = []
            current_start = None
            last_content_line = None
        else:
            # Content line
            if not current_lines:
                current_start = line_num
            current_lines.append(line)
            last_content_line = line_num

    # Emit trailing block (file does not end with blank line)
    _emit()
    return blocks


def _classify(text: str) -> BlockType:
    """
    Infer block_type from block text.

    Priority order (first match wins):
      proof      → first non-empty line starts with "Proof" / "증명"
      definition → first non-empty line contains "Definition" / "Def." / "정의"
      theorem    → first non-empty line contains "Theorem" / "Lemma" / "Proposition" / "Corollary" / …
      example    → first non-empty line contains "Example" / "예제"
      exercise   → first non-empty line contains "Exercise" / "Problem" / …
      paragraph  → default

    Only the first non-empty line is examined for structural markers (the
    "leading marker" of the block). This prevents common words like "definition"
    appearing in prose from triggering a false classification.
    """
    first_nonempty = next((l for l in text.splitlines() if l.strip()), "")
    # Strip leading bold/italic markers before bare proof check
    first_stripped = re.sub(r"^\*+", "", first_nonempty.lstrip())

    if _PROOF_BARE_RE.match(first_stripped):
        return "proof"
    if _THEOREM_START_RE.match(first_stripped):
        return "theorem"
    if _DEFINITION_START_RE.match(first_stripped):
        return "definition"
    if _EXAMPLE_START_RE.match(first_stripped):
        return "example"
    if _EXERCISE_START_RE.match(first_stripped):
        return "exercise"
    return "paragraph"


def _relative_path(source_path: Path) -> str:
    """Return path relative to CWD (POSIX separators), or fall back to filename."""
    try:
        return (
            Path(source_path).resolve().relative_to(Path.cwd().resolve()).as_posix()
        )
    except ValueError:
        return Path(source_path).name

"""Tests for pipeline/block_parser.py (MVP2 Step 2)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from gonghaebun.models.question_bank import SourceBlock
from gonghaebun.pipeline.block_parser import parse_blocks

# ---------------------------------------------------------------------------
# Test fixture (inline markdown, exact line numbers documented)
# ---------------------------------------------------------------------------

# Line 1 : # Introduction
# Line 2 : (blank)
# Line 3 : "This is a paragraph ..."           ← block 1 start+end
# Line 4 : (blank)
# Line 5 : ## Definitions and Theorems
# Line 6 : (blank)
# Line 7 : "**Definition 2.1.**..."            ← block 2 start
# Line 8 : "cover of K..."                     ← block 2 end
# Line 9 : (blank)
# Line 10: "**Theorem 2.2 (Heine-Borel).**..." ← block 3 start
# Line 11: "closed and bounded..."              ← block 3 end
# Line 12: (blank)
# Line 13: "Proof. Let K..."                   ← block 4 start
# Line 14: "Consider any open cover..."         ← block 4 end
# Line 15: (blank)
# Line 16: ## Examples and Exercises
# Line 17: (blank)
# Line 18: "Example 2.3...."                   ← block 5 start
# Line 19: "in [0, 1]..."                      ← block 5 end
# Line 20: (blank)
# Line 21: "Exercise 2.4...."                  ← block 6 start
# Line 22: "intersection..."                   ← block 6 end
# Line 23: (blank)
# Line 24: "Short."                            ← SKIPPED (6 non-ws chars)

FIXTURE_MD = """\
# Introduction

This is a paragraph about the introduction with more than fifty non-whitespace characters total.

## Definitions and Theorems

**Definition 2.1.** A subset K of a metric space X is called compact if every open
cover of K has a finite subcover. This is the standard topological definition used in analysis.

**Theorem 2.2 (Heine-Borel).** A subset of R^n is compact if and only if it is
closed and bounded. This is one of the most important theorems in real analysis.

Proof. Let K be a closed and bounded subset of R^n. We construct a finite subcover.
Consider any open cover and apply the nested intervals property to extract the subcover.

## Examples and Exercises

Example 2.3. The closed interval [0, 1] is compact by Heine-Borel. Every sequence
in [0, 1] has a convergent subsequence whose limit remains in [0, 1].

Exercise 2.4. Show that the union of finitely many compact sets is compact. Is the
intersection of two compact sets necessarily compact? Provide a proof or counterexample.

Short.
"""

DOCUMENT_ID = "testdoc"


@pytest.fixture
def md_file(tmp_path: Path) -> Path:
    """Write FIXTURE_MD to a temporary file and return its path."""
    p = tmp_path / "testdoc.md"
    p.write_text(FIXTURE_MD, encoding="utf-8")
    return p


@pytest.fixture
def blocks(md_file: Path) -> list[SourceBlock]:
    """Return parsed blocks from FIXTURE_MD."""
    return parse_blocks(md_file, DOCUMENT_ID)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


class TestBasicStructure:
    def test_returns_list_of_source_blocks(self, blocks):
        assert isinstance(blocks, list)
        assert all(isinstance(b, SourceBlock) for b in blocks)

    def test_correct_block_count(self, blocks):
        # 6 blocks pass the 50-char filter; "Short." is skipped
        assert len(blocks) == 6

    def test_block_ids_start_at_one(self, blocks):
        assert blocks[0].block_id == f"{DOCUMENT_ID}_b000001"

    def test_block_ids_are_sequential(self, blocks):
        expected = [f"{DOCUMENT_ID}_b{i:06d}" for i in range(1, 7)]
        assert [b.block_id for b in blocks] == expected

    def test_document_id_in_every_block_id(self, blocks):
        for b in blocks:
            assert b.document_id == DOCUMENT_ID
            assert b.block_id.startswith(DOCUMENT_ID)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_block_id_is_deterministic(self, md_file):
        blocks_a = parse_blocks(md_file, DOCUMENT_ID)
        blocks_b = parse_blocks(md_file, DOCUMENT_ID)
        assert [b.block_id for b in blocks_a] == [b.block_id for b in blocks_b]

    def test_text_hash_is_deterministic(self, md_file):
        blocks_a = parse_blocks(md_file, DOCUMENT_ID)
        blocks_b = parse_blocks(md_file, DOCUMENT_ID)
        assert [b.text_hash for b in blocks_a] == [b.text_hash for b in blocks_b]


# ---------------------------------------------------------------------------
# Section title propagation
# ---------------------------------------------------------------------------


class TestSectionTitle:
    def test_first_block_has_first_heading_title(self, blocks):
        assert blocks[0].section_title == "Introduction"

    def test_blocks_under_definitions_heading(self, blocks):
        # blocks 1–3 (index 1, 2, 3) are under "Definitions and Theorems"
        for b in blocks[1:4]:
            assert b.section_title == "Definitions and Theorems", (
                f"block {b.block_id} has wrong section_title: {b.section_title!r}"
            )

    def test_blocks_under_examples_heading(self, blocks):
        # blocks 4 and 5 (index 4, 5) are under "Examples and Exercises"
        for b in blocks[4:]:
            assert b.section_title == "Examples and Exercises"

    def test_heading_line_not_in_block_text(self, blocks):
        for b in blocks:
            for line in b.text.splitlines():
                assert not line.startswith("#"), (
                    f"Heading marker found in block {b.block_id}: {line!r}"
                )


# ---------------------------------------------------------------------------
# Block type classification
# ---------------------------------------------------------------------------


class TestBlockType:
    def test_paragraph_block(self, blocks):
        # Block 0: "This is a paragraph..." — no special markers
        assert blocks[0].block_type == "paragraph"

    def test_definition_block(self, blocks):
        # Block 1: starts with "**Definition 2.1.**"
        assert blocks[1].block_type == "definition"

    def test_theorem_block(self, blocks):
        # Block 2: starts with "**Theorem 2.2 (Heine-Borel).**"
        assert blocks[2].block_type == "theorem"

    def test_proof_block(self, blocks):
        # Block 3: starts with "Proof."
        assert blocks[3].block_type == "proof"

    def test_example_block(self, blocks):
        # Block 4: starts with "Example 2.3."
        assert blocks[4].block_type == "example"

    def test_exercise_block(self, blocks):
        # Block 5: starts with "Exercise 2.4."
        assert blocks[5].block_type == "exercise"


class TestBlockTypeEdgeCases:
    def _make_block(self, tmp_path: Path, content: str) -> list[SourceBlock]:
        p = tmp_path / "edge.md"
        p.write_text(content, encoding="utf-8")
        return parse_blocks(p, "edge")

    def test_bold_proof_marker(self, tmp_path):
        content = (
            "**Proof.** Let K be compact. Then every open cover has a finite "
            "subcover by definition. This gives us what we need to conclude. QED.\n"
        )
        blocks = self._make_block(tmp_path, content)
        assert len(blocks) == 1
        assert blocks[0].block_type == "proof"

    def test_lemma_is_theorem(self, tmp_path):
        content = (
            "Lemma 3.1. Every closed subset of a compact set is compact. "
            "This follows directly from the open cover definition and the fact "
            "that complements of closed sets are open.\n"
        )
        blocks = self._make_block(tmp_path, content)
        assert len(blocks) == 1
        assert blocks[0].block_type == "theorem"

    def test_corollary_is_theorem(self, tmp_path):
        content = (
            "Corollary 2.5. A continuous image of a compact set is compact. "
            "Proof follows from the fact that preimages of open sets under "
            "continuous functions are open, so we can pull back any open cover.\n"
        )
        blocks = self._make_block(tmp_path, content)
        assert len(blocks) == 1
        # corollary contains "Proof" but it's not the first word → definition/theorem wins
        assert blocks[0].block_type == "theorem"

    def test_proposition_is_theorem(self, tmp_path):
        content = (
            "Proposition 4.1. The intersection of compact sets is compact if "
            "at least one of them is compact. This holds in any Hausdorff space "
            "and is a standard result in point-set topology.\n"
        )
        blocks = self._make_block(tmp_path, content)
        assert blocks[0].block_type == "theorem"

    def test_plain_paragraph_no_markers(self, tmp_path):
        content = (
            "This is a plain paragraph with no mathematical markers. "
            "It discusses some ideas informally without any structural keywords. "
            "Sufficient content to pass the minimum length filter.\n"
        )
        blocks = self._make_block(tmp_path, content)
        assert blocks[0].block_type == "paragraph"


# ---------------------------------------------------------------------------
# Short block filtering
# ---------------------------------------------------------------------------


class TestShortBlockFiltering:
    def test_short_block_is_skipped(self, blocks):
        # "Short." has 6 non-ws chars; should not appear
        texts = [b.text for b in blocks]
        assert not any("Short." in t for t in texts)

    def test_exactly_49_non_ws_skipped(self, tmp_path):
        # 49 non-whitespace chars: "a" * 49 (with spaces to separate)
        content = "a " * 49 + "\n"  # 49 'a' chars, rest spaces
        p = tmp_path / "short.md"
        p.write_text(content, encoding="utf-8")
        assert parse_blocks(p, "doc") == []

    def test_exactly_50_non_ws_included(self, tmp_path):
        content = "a " * 50 + "\n"  # 50 'a' chars
        p = tmp_path / "long.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blocks(p, "doc")
        assert len(result) == 1

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "empty.md"
        p.write_text("", encoding="utf-8")
        assert parse_blocks(p, "doc") == []

    def test_only_headings_returns_empty(self, tmp_path):
        content = "# Title\n## Subtitle\n### Section\n"
        p = tmp_path / "headings.md"
        p.write_text(content, encoding="utf-8")
        assert parse_blocks(p, "doc") == []


# ---------------------------------------------------------------------------
# Line numbers
# ---------------------------------------------------------------------------


class TestLineNumbers:
    def test_start_line_populated(self, blocks):
        assert all(b.start_line is not None for b in blocks)

    def test_end_line_populated(self, blocks):
        assert all(b.end_line is not None for b in blocks)

    def test_end_line_gte_start_line(self, blocks):
        for b in blocks:
            assert b.end_line >= b.start_line

    def test_first_block_line_numbers(self, blocks):
        # Paragraph "This is a paragraph..." is on line 3 only
        assert blocks[0].start_line == 3
        assert blocks[0].end_line == 3

    def test_definition_block_line_numbers(self, blocks):
        # Definition block spans lines 7–8
        assert blocks[1].start_line == 7
        assert blocks[1].end_line == 8

    def test_proof_block_line_numbers(self, blocks):
        # Proof block spans lines 13–14
        assert blocks[3].start_line == 13
        assert blocks[3].end_line == 14


# ---------------------------------------------------------------------------
# Text hash
# ---------------------------------------------------------------------------


class TestTextHash:
    def test_text_hash_matches_sha256(self, blocks):
        for b in blocks:
            expected = hashlib.sha256(b.text.encode("utf-8")).hexdigest()
            assert b.text_hash == expected, (
                f"block {b.block_id}: hash mismatch"
            )

    def test_text_hash_is_full_hex_digest(self, blocks):
        # sha256 hex digest is always 64 chars
        for b in blocks:
            assert len(b.text_hash) == 64
            assert all(c in "0123456789abcdef" for c in b.text_hash)

    def test_different_blocks_different_hashes(self, blocks):
        hashes = [b.text_hash for b in blocks]
        assert len(hashes) == len(set(hashes)), "Hash collision between blocks"


# ---------------------------------------------------------------------------
# Source file path
# ---------------------------------------------------------------------------


class TestSourceFile:
    def test_source_file_is_nonempty_string(self, blocks):
        for b in blocks:
            assert isinstance(b.source_file, str)
            assert b.source_file

    def test_source_file_consistent_across_blocks(self, blocks):
        # All blocks from the same file share the same source_file value
        paths = {b.source_file for b in blocks}
        assert len(paths) == 1

    def test_source_file_uses_forward_slashes(self, blocks):
        for b in blocks:
            assert "\\" not in b.source_file, (
                f"Backslash in source_file: {b.source_file!r}"
            )

    def test_source_file_fallback_when_absolute(self, tmp_path):
        """source_file falls back to filename when relative_to(cwd) raises."""
        # Use an absolute path that may not be relative to CWD
        p = tmp_path / "outside.md"
        content = "a " * 60 + "\n"
        p.write_text(content, encoding="utf-8")
        result = parse_blocks(p.resolve(), "outside")
        # Either a relative path or just the filename — never empty
        assert result[0].source_file  # nonempty
        assert "\\" not in result[0].source_file


# ---------------------------------------------------------------------------
# Smoke test: real sample_source.md
# ---------------------------------------------------------------------------


SAMPLE_SOURCE = Path(__file__).parent / "data" / "sample_source.md"


class TestSampleSource:
    def test_parses_sample_source_without_error(self):
        assert SAMPLE_SOURCE.exists()
        blocks = parse_blocks(SAMPLE_SOURCE, "sample_source")
        assert isinstance(blocks, list)

    def test_sample_source_produces_blocks(self):
        blocks = parse_blocks(SAMPLE_SOURCE, "sample_source")
        assert len(blocks) > 0

    def test_sample_source_block_ids_sequential(self):
        blocks = parse_blocks(SAMPLE_SOURCE, "sample_source")
        for i, b in enumerate(blocks, start=1):
            assert b.block_id == f"sample_source_b{i:06d}"

    def test_sample_source_section_title_compactness(self):
        blocks = parse_blocks(SAMPLE_SOURCE, "sample_source")
        # First heading is "Compactness"; blocks after it should have that title
        compactness_blocks = [b for b in blocks if b.section_title == "Compactness"]
        assert len(compactness_blocks) >= 1

    def test_sample_source_all_blocks_valid(self):
        blocks = parse_blocks(SAMPLE_SOURCE, "sample_source")
        for b in blocks:
            # All blocks have 50+ non-ws chars (filter was applied)
            non_ws = sum(1 for c in b.text if not c.isspace())
            assert non_ws >= 50

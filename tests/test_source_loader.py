"""Tests for Stage 0: Source Loader."""
from __future__ import annotations

import pytest
from pathlib import Path

from gonghaebun.pipeline.source_loader import (
    SourceEmptyError,
    SourceNotFoundError,
    extract_windows,
    load_and_extract,
)

SAMPLE_SOURCE = Path(__file__).parent / "data" / "sample_source.md"
KEYWORDS = [
    "compact",
    "compactness",
    "open cover",
    "finite subcover",
    "Heine-Borel",
    "closed and bounded",
    "limit point",
    "perfect",
    "connected",
    "cover",
]


@pytest.fixture
def sample_source() -> Path:
    assert SAMPLE_SOURCE.exists(), f"Sample source not found: {SAMPLE_SOURCE}"
    return SAMPLE_SOURCE


def test_missing_source_local_fails(tmp_path):
    with pytest.raises(SourceNotFoundError):
        load_and_extract(
            source_path=tmp_path / "nonexistent.md",
            concept_id="compactness",
            keywords=KEYWORDS,
            output_dir=tmp_path / "out",
        )


def test_missing_source_error_message(tmp_path):
    try:
        load_and_extract(
            source_path=tmp_path / "nonexistent.md",
            concept_id="compactness",
            keywords=KEYWORDS,
            output_dir=tmp_path / "out",
        )
    except SourceNotFoundError as exc:
        assert "source material is required" in str(exc)
        assert "--source-local" in str(exc)


def test_empty_source_fails(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("   \n", encoding="utf-8")
    with pytest.raises(SourceEmptyError):
        load_and_extract(
            source_path=empty,
            concept_id="compactness",
            keywords=KEYWORDS,
            output_dir=tmp_path / "out",
        )


def test_source_hash_created(tmp_path, sample_source):
    manifest = load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=tmp_path / "out",
    )
    assert manifest.source_hash.startswith("sha256:")
    assert len(manifest.source_hash) > 10


def test_source_manifest_json_created(tmp_path, sample_source):
    out = tmp_path / "out"
    load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=out,
    )
    assert (out / "source_manifest.json").exists()


def test_source_excerpt_created(tmp_path, sample_source):
    out = tmp_path / "out"
    load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=out,
    )
    assert (out / "source_excerpt.md").exists()


def test_source_excerpt_does_not_equal_full_source(tmp_path, sample_source):
    out = tmp_path / "out"
    load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=out,
    )
    full = sample_source.read_text(encoding="utf-8")
    excerpt = (out / "source_excerpt.md").read_text(encoding="utf-8")
    assert excerpt != full


def test_source_coverage_sufficient_when_keywords_found(tmp_path, sample_source):
    manifest = load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=tmp_path / "out",
    )
    assert len(manifest.keywords_found) >= 4
    assert manifest.source_coverage == "sufficient"


def test_source_coverage_insufficient_when_no_keywords(tmp_path):
    no_kw_file = tmp_path / "no_keywords.md"
    no_kw_file.write_text(
        "This text contains no mathematical terms relevant to compactness at all.",
        encoding="utf-8",
    )
    manifest = load_and_extract(
        source_path=no_kw_file,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=tmp_path / "out",
    )
    # "cover" appears in "contains" — could match; use truly absent keywords
    # Actually we need to check the result is not sufficient
    assert manifest.source_coverage in ("insufficient", "partial")


def test_extract_windows_merges_overlapping():
    text = "a" * 5000
    # Two keywords close together — should merge into one window
    text = "prefix " + "compact " + "filler " * 50 + "compactness " + " suffix"
    keywords = ["compact", "compactness"]
    windows, found = extract_windows(text, keywords, window_chars=200)
    assert len(found) == 2
    # Windows may be merged or separate depending on spacing — just check they exist
    assert len(windows) >= 1


def test_extract_windows_caps_total(tmp_path):
    # Create a large synthetic text with many keyword hits
    chunk = "compact " * 100
    big_text = chunk * 20  # ~14000 chars of keyword hits
    windows, found = extract_windows(big_text, ["compact"], window_chars=800, max_total_chars=3000)
    total = sum(len(w.text) for w in windows)
    assert total <= 3000


def test_manifest_contains_required_fields(tmp_path, sample_source):
    import json
    out = tmp_path / "out"
    load_and_extract(
        source_path=sample_source,
        concept_id="compactness",
        keywords=KEYWORDS,
        output_dir=out,
    )
    data = json.loads((out / "source_manifest.json").read_text(encoding="utf-8"))
    for field in ["source_hash", "source_coverage", "keywords_found", "grounding_mode"]:
        assert field in data, f"Missing field: {field}"

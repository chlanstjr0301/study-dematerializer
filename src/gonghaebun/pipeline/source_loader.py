"""
Stage 0: Source Loader

Responsibilities:
- Load and validate the --source-local file.
- Compute SHA-256 hash.
- Detect concept-relevant keywords.
- Extract bounded keyword-in-context windows (deterministic, no LLM).
- Write source_manifest.json and source_excerpt.md to output_dir.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from gonghaebun.models.source_models import SourceManifest, SourceWindow


class SourceNotFoundError(FileNotFoundError):
    pass


class SourceEmptyError(ValueError):
    pass


def load_and_extract(
    source_path: Path,
    concept_id: str,
    keywords: list[str],
    output_dir: Path,
    window_chars: int = 800,
    max_total_chars: int = 8000,
) -> SourceManifest:
    """
    Main entry for Stage 0.

    Loads the source file, extracts keyword windows, writes artifacts,
    and returns a SourceManifest.

    Raises:
        SourceNotFoundError: if source_path does not exist.
        SourceEmptyError: if source file is empty.
    """
    if not source_path.exists():
        raise SourceNotFoundError(
            f"source material is required; Gonghaebun does not generate "
            f"study sessions from model prior alone. "
            f"Provide --source-local <path>. "
            f"(Path not found: {source_path})"
        )

    text = source_path.read_text(encoding="utf-8")
    if not text.strip():
        raise SourceEmptyError(f"Source file is empty: {source_path}")

    source_hash = _sha256(text)
    windows, keywords_found = extract_windows(text, keywords, window_chars, max_total_chars)
    excerpt_text = _render_excerpt(concept_id, source_hash, windows)
    excerpt_capped = _total_chars(windows) >= max_total_chars

    coverage = _compute_coverage(keywords_found)

    manifest = SourceManifest(
        source_path=str(source_path),
        source_hash=source_hash,
        source_size_chars=len(text),
        concept_id=concept_id,
        keywords_searched=keywords,
        keywords_found=sorted(keywords_found),
        windows_extracted=len(windows),
        source_coverage=coverage,
        excerpt_chars=len(excerpt_text),
        excerpt_capped=excerpt_capped,
        grounding_mode="local_private_source",
        extracted_at=_now_iso(),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(output_dir / "source_manifest.json", manifest)
    (output_dir / "source_excerpt.md").write_text(excerpt_text, encoding="utf-8")

    return manifest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def extract_windows(
    text: str,
    keywords: list[str],
    window_chars: int = 800,
    max_total_chars: int = 8000,
) -> tuple[list[SourceWindow], set[str]]:
    """
    For each keyword hit, capture a window of ±window_chars characters.
    Overlapping/adjacent windows (gap < 200 chars) are merged.
    Total excerpt is capped at max_total_chars.

    Returns (windows, keywords_found).
    """
    # Find all hit positions sorted by position
    hits: list[tuple[int, str]] = []  # (position, keyword)
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for m in pattern.finditer(text):
            hits.append((m.start(), kw))

    hits.sort(key=lambda x: x[0])

    if not hits:
        return [], set()

    keywords_found: set[str] = {kw for _, kw in hits}

    # Build raw windows
    raw: list[tuple[int, int]] = []
    for pos, _ in hits:
        start = max(0, pos - window_chars)
        end = min(len(text), pos + window_chars)
        raw.append((start, end))

    # Merge overlapping/adjacent windows (gap < 200 chars)
    merged: list[tuple[int, int]] = []
    for start, end in raw:
        if merged and start - merged[-1][1] < 200:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Cap total chars
    windows: list[SourceWindow] = []
    total = 0
    for start, end in merged:
        chunk = text[start:end]
        if total + len(chunk) > max_total_chars:
            remaining = max_total_chars - total
            if remaining > 0:
                windows.append(SourceWindow(start, start + remaining, chunk[:remaining]))
            break
        windows.append(SourceWindow(start, end, chunk))
        total += len(chunk)

    return windows, keywords_found


def _sha256(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _total_chars(windows: list[SourceWindow]) -> int:
    return sum(len(w.text) for w in windows)


def _compute_coverage(keywords_found: set[str]) -> str:
    n = len(keywords_found)
    if n >= 4:
        return "sufficient"
    if n >= 2:
        return "partial"
    return "insufficient"


def _render_excerpt(concept_id: str, source_hash: str, windows: list[SourceWindow]) -> str:
    lines = [
        f"# Source Excerpt — {concept_id}",
        f"_Grounded on local private source. {source_hash}_",
        "_Full source not stored. Excerpts are bounded windows only._",
        "",
    ]
    for i, w in enumerate(windows, 1):
        lines.append("---")
        lines.append(f"[Window {i} — chars {w.start_char}–{w.end_char}]")
        lines.append("")
        lines.append(w.text.strip())
        lines.append("")
    if not windows:
        lines.append("_(No keyword matches found in source.)_")
    return "\n".join(lines)


def _write_manifest(path: Path, manifest: SourceManifest) -> None:
    data = {
        "source_path": manifest.source_path,
        "source_hash": manifest.source_hash,
        "source_size_chars": manifest.source_size_chars,
        "concept_id": manifest.concept_id,
        "keywords_searched": manifest.keywords_searched,
        "keywords_found": manifest.keywords_found,
        "windows_extracted": manifest.windows_extracted,
        "source_coverage": manifest.source_coverage,
        "excerpt_chars": manifest.excerpt_chars,
        "excerpt_capped": manifest.excerpt_capped,
        "grounding_mode": manifest.grounding_mode,
        "extracted_at": manifest.extracted_at,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

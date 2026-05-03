"""
common.py -- Shared utilities for the paper-corpus pipeline.

Import-only module: no side effects on import other than ensuring
stdout/stderr use UTF-8 on Windows (where the default console encoding
may be cp949 or cp1252).
"""

import sys

# Ensure UTF-8 output on Windows consoles (cp949/cp1252 default).
# This is intentional: the pipeline writes Unicode content (paper titles,
# special characters) and must not crash on non-ASCII output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

# ── Path constants ────────────────────────────────────────────────────────────

ROOT           = Path(__file__).parent.parent
PAPERS_DIR     = ROOT / "papers"
EXTRACTED_DIR  = ROOT / "extracted"
NORMALIZED_DIR = ROOT / "normalized"
CORPUS_DIR     = ROOT / "corpus"
DERIVED_DIR    = ROOT / "derived"
REPORTS_DIR    = ROOT / "reports"

# ── Pilot paper topics (used by --pilot flag) ─────────────────────────────────

# One clean born-digital paper + one older multi-column paper
PILOT_TOPICS = {"cognitive-load-theory", "scaffolding"}

# ── Tokenizer (lazy-loaded to avoid startup cost) ─────────────────────────────

_ENC = None


def _get_enc():
    global _ENC
    if _ENC is None:
        import tiktoken
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding (GPT-4 / Claude approximation)."""
    return len(_get_enc().encode(text))


# ── paper_id helpers ──────────────────────────────────────────────────────────

def slug(text: str, max_len: int = 80) -> str:
    """
    Convert text to a filesystem-safe slug.
    Lowercase, spaces/special→hyphen, strip non-alnum-except-dash, cap at max_len.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len]


def make_paper_id(topic: str, stem: str) -> str:
    """
    Derive a stable, filesystem-safe paper ID: {topic_slug}_{stem_slug}.
    Topic slug capped at 40 chars, stem slug at 75 chars, total at 120.

    Examples:
        cognitive-load-theory_s10648-019-09465-5
        scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tuto
    """
    t = slug(topic, max_len=40)
    s = slug(stem, max_len=75)
    combined = f"{t}_{s}"
    return combined[:120]


def iter_papers() -> List[Dict]:
    """
    Scan papers/, return sorted list of paper dicts.
    Each dict: {paper_id, topic, stem, path (Path object)}
    """
    papers = []
    for pdf in sorted(PAPERS_DIR.rglob("*.pdf")):
        topic = pdf.parent.name
        stem = pdf.stem
        paper_id = make_paper_id(topic, stem)
        papers.append(
            {
                "paper_id": paper_id,
                "topic": topic,
                "stem": stem,
                "path": pdf,
            }
        )
    return papers


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()

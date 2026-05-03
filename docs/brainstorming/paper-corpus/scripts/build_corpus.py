"""
build_corpus.py — Stage 3: sections → JSONL corpus files.

Reads normalized/{paper_id}/sections.json and extracted/{paper_id}/metadata.json
for each paper and produces:
  corpus/
    papers.jsonl          — one record per paper (metadata + stats)
    chunks.jsonl          — one source-grounded chunk per line
    references.jsonl      — extracted reference entries per paper
    figures_tables.jsonl  — figure and table records with paper_id
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict

from common import (
    CORPUS_DIR,
    EXTRACTED_DIR,
    NORMALIZED_DIR,
    PILOT_TOPICS,
    count_tokens,
    iter_papers,
)

# ── Theory / math section detection ──────────────────────────────────────────

THEORY_WORDS = {
    "theory", "theoretical", "framework", "model", "formalism",
    "proof", "derivation", "mathematical", "equation", "analysis",
}


def is_theory_heavy(section_title: str, section_text: str) -> bool:
    title_lower = section_title.lower()
    if any(w in title_lower for w in THEORY_WORDS):
        return True
    # Block equations present
    if re.search(r"\$\$.+?\$\$", section_text, re.DOTALL):
        return True
    return False


# ── Content type classification ───────────────────────────────────────────────

def classify_content_type(section_title: str) -> str:
    t = section_title.lower()
    if "abstract" in t:
        return "abstract"
    if "reference" in t or "bibliography" in t:
        return "references"
    if "appendix" in t:
        return "appendix"
    if "acknowledgement" in t or "acknowledgment" in t:
        return "acknowledgements"
    if any(w in t for w in THEORY_WORDS):
        return "theory"
    return "body"


# ── Citation extraction ───────────────────────────────────────────────────────

# APA: (Author, Year) or (Author et al., Year; Author2, Year2)
_APA_RE = re.compile(
    r"\(([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s+\d{4}[a-z]?"
    r"(?:;\s*[A-Z][a-z]+(?:\s+et\s+al\.?)?,\s+\d{4}[a-z]?)*)\)"
)
# Numbered: [1], [2,3], [1; 2]
_NUM_RE = re.compile(r"\[(\d+(?:[,;\s]\s*\d+)*)\]")
# Inline: Author & Author, Year or Author, Year
_INLINE_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?,\s+\d{4}[a-z]?)\b"
)


def extract_citations(text: str) -> List[str]:
    found = set()
    for m in _APA_RE.finditer(text):
        for part in re.split(r";\s*", m.group(1)):
            found.add(part.strip())
    for m in _NUM_RE.finditer(text):
        for num in re.split(r"[,;\s]+", m.group(1)):
            if num.strip():
                found.add(f"[{num.strip()}]")
    for m in _INLINE_RE.finditer(text):
        found.add(m.group(1))
    return sorted(found)


# ── Reference list extraction ─────────────────────────────────────────────────

_REF_NUMBERED  = re.compile(r"(?m)^\s*\[(\d+)\]\s*(.+)")
_REF_DOT       = re.compile(r"(?m)^\s*(\d+)\.\s+(.+)")
_YEAR_IN_REF   = re.compile(r"\b((?:19|20)\d{2})\b")
_DOI_IN_REF    = re.compile(r"10\.\d{4,}/\S+")


def extract_references(paper_id: str, sections: List[dict]) -> List[dict]:
    refs_section = next(
        (
            s for s in sections
            if "reference" in s["title"].lower() or "bibliography" in s["title"].lower()
        ),
        None,
    )
    if not refs_section:
        return []

    text = refs_section["text"]
    matches = list(_REF_NUMBERED.finditer(text)) or list(_REF_DOT.finditer(text))

    refs = []
    for i, m in enumerate(matches):
        # Collect text up to next match
        start = m.start(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        ref_text = text[start:end].strip().replace("\n", " ")

        year_m = _YEAR_IN_REF.search(ref_text)
        doi_m  = _DOI_IN_REF.search(ref_text)

        refs.append(
            {
                "paper_id":    paper_id,
                "ref_id":      f"ref-{i + 1:03d}",
                "text":        ref_text[:600],
                "likely_year": year_m.group(1) if year_m else "",
                "likely_doi":  doi_m.group(0)  if doi_m  else "",
            }
        )
    return refs


# ── Paper metadata extraction ─────────────────────────────────────────────────

def extract_paper_metadata(paper_id: str, sections: List[dict], pdf_meta: dict) -> dict:
    """Combine PDF header metadata with heuristically extracted fields."""
    raw_pdf = pdf_meta.get("pdf_metadata", {})

    title  = (raw_pdf.get("title") or "").strip()
    author = (raw_pdf.get("author") or "").strip()
    authors = (
        [a.strip() for a in re.split(r"[;,]", author) if a.strip()]
        if author else []
    )

    # Try to find a year in the first page text
    year = ""
    if sections:
        first_text = sections[0]["text"][:600]
        ym = re.search(r"\b((?:19|20)\d{2})\b", first_text)
        if ym:
            year = ym.group(1)

    # Abstract text
    abstract = ""
    for s in sections:
        if "abstract" in s["title"].lower():
            abstract = s["text"][:2000]
            break

    return {
        "paper_id":     paper_id,
        "title":        title or f"[{paper_id}]",
        "authors":      authors,
        "year":         year,
        "topic_folder": pdf_meta.get("topic_folder", ""),
        "source_pdf":   pdf_meta.get("source_pdf", ""),
        "page_count":   pdf_meta.get("page_count", 0),
        "abstract":     abstract,
    }


# ── Section-aware chunking ────────────────────────────────────────────────────

HARD_MAX_TOKENS = 1500  # absolute ceiling; overlap is dropped rather than exceed this

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\'])")


def _split_sentences(text: str) -> List[str]:
    """Split text at sentence boundaries."""
    sents = _SENT_SPLIT_RE.split(text)
    return [s.strip() for s in sents if s.strip()]


def _split_at_words(text: str, max_tokens: int) -> List[str]:
    """Split text into parts each <= max_tokens by word boundaries (last-resort hard cap)."""
    words = text.split()
    parts: List[str] = []
    current: List[str] = []
    current_tok = 0
    for word in words:
        wt = count_tokens(word + " ")
        if current and current_tok + wt > max_tokens:
            parts.append(" ".join(current))
            current = [word]
            current_tok = wt
        else:
            current.append(word)
            current_tok += wt
    if current:
        parts.append(" ".join(current))
    return parts or [text]  # never return empty


def _chunk_contains(text: str) -> dict:
    return {
        "contains_equation":       bool(re.search(r"\$\$.+?\$\$|\$.+?\$", text, re.DOTALL)),
        "contains_table":          bool(re.search(r"\bTable\s+\d+", text, re.IGNORECASE)),
        "contains_figure_caption": bool(re.search(r"\bFig(?:ure|\.)?\.?\s*\d+", text, re.IGNORECASE)),
    }


def split_into_chunks(section: dict, paper_meta: dict) -> List[dict]:
    """
    Split a section into one or more chunks respecting token budgets.
    Returns empty list for empty sections. Never emits a chunk >HARD_MAX_TOKENS.
    """
    text  = section["text"]
    title = section["title"]

    # Skip empty sections entirely
    if not text or not text.strip():
        return []

    max_tokens   = 1200 if is_theory_heavy(title, text) else 900
    total_tokens = count_tokens(text)

    if total_tokens == 0:
        return []

    paper_id   = paper_meta["paper_id"]
    chunk_base = f"{paper_id}_{section['section_id']}"

    base_fields = {
        "paper_id":     paper_id,
        "title":        paper_meta.get("title", ""),
        "authors":      paper_meta.get("authors", []),
        "year":         paper_meta.get("year", ""),
        "topic_folder": paper_meta.get("topic_folder", ""),
        "section_path": [title],
        "page_start":   section["page_start"],
        "page_end":     section["page_end"],
        "content_type": classify_content_type(title),
        "source_pdf":   paper_meta.get("source_pdf", ""),
    }

    def _make_chunk(idx: int, body: str, overlap: str = "") -> dict:
        """Build a chunk dict. Drops overlap if it would push over HARD_MAX_TOKENS."""
        candidate = (overlap + " " + body).strip() if overlap else body.strip()
        if count_tokens(candidate) > HARD_MAX_TOKENS:
            candidate = body.strip()
        tok = count_tokens(candidate)
        return {
            "chunk_id":          f"{chunk_base}_c{idx:02d}",
            **base_fields,
            "text":              candidate,
            "citations_in_text": extract_citations(candidate),
            **_chunk_contains(candidate),
            "token_count":       tok,
            "quality":           "ok",
        }

    # ── Single chunk ──────────────────────────────────────────────────────────
    if total_tokens <= max_tokens:
        return [_make_chunk(1, text)]

    # ── Multi-chunk split ─────────────────────────────────────────────────────
    sentences    = _split_sentences(text)
    chunks       = []
    current      = []
    current_tok  = 0
    chunk_idx    = 1
    overlap_text = ""

    def _emit_current():
        nonlocal chunk_idx, overlap_text
        chunks.append(_make_chunk(chunk_idx, " ".join(current), overlap_text))
        chunk_idx += 1
        overlap_sents, overlap_tok = [], 0
        for s in reversed(current):
            t = count_tokens(s)
            if overlap_tok + t <= 150:
                overlap_sents.insert(0, s)
                overlap_tok += t
            else:
                break
        overlap_text = " ".join(overlap_sents) if overlap_sents else ""

    for sent in sentences:
        sent_tok = count_tokens(sent)

        if current and current_tok + sent_tok > max_tokens:
            _emit_current()
            # If this sentence alone exceeds HARD_MAX, word-split it immediately
            if sent_tok > HARD_MAX_TOKENS:
                for part in _split_at_words(sent, HARD_MAX_TOKENS):
                    chunks.append(_make_chunk(chunk_idx, part))
                    chunk_idx += 1
                current, current_tok, overlap_text = [], 0, ""
            else:
                current, current_tok = [sent], sent_tok
        elif not current and sent_tok > HARD_MAX_TOKENS:
            # First sentence in a fresh accumulator is already too long
            for part in _split_at_words(sent, HARD_MAX_TOKENS):
                chunks.append(_make_chunk(chunk_idx, part))
                chunk_idx += 1
            overlap_text = ""
        else:
            current.append(sent)
            current_tok += sent_tok

    # Emit final chunk; if it would exceed HARD_MAX even without overlap, word-split it
    if current:
        body = " ".join(current)
        if count_tokens(body) > HARD_MAX_TOKENS:
            for part in _split_at_words(body, HARD_MAX_TOKENS):
                chunks.append(_make_chunk(chunk_idx, part))
                chunk_idx += 1
        else:
            chunks.append(_make_chunk(chunk_idx, body, overlap_text))

    return chunks


# ── Per-paper builder ─────────────────────────────────────────────────────────

def build_paper(
    paper_id: str,
    all_chunks: list,
    all_papers: list,
    all_refs: list,
    all_figs_tbls: list,
) -> bool:
    norm_dir = NORMALIZED_DIR / paper_id
    ext_dir  = EXTRACTED_DIR  / paper_id

    sections_file = norm_dir / "sections.json"
    meta_file     = ext_dir  / "metadata.json"

    if not sections_file.exists():
        print(f"  SKIP {paper_id}: sections.json missing -- run normalize first")
        return False
    if not meta_file.exists():
        print(f"  SKIP {paper_id}: metadata.json missing -- run extract first")
        return False

    sections = json.loads(sections_file.read_text(encoding="utf-8"))
    pdf_meta = json.loads(meta_file.read_text(encoding="utf-8"))
    paper_meta = extract_paper_metadata(paper_id, sections, pdf_meta)

    # ── Non-extractable PDF: record in papers.jsonl but emit no chunks ────────
    if pdf_meta.get("needs_ocr") or pdf_meta.get("extraction_status") == "no_text":
        paper_meta["section_count"] = 0
        paper_meta["chunk_count"]   = 0
        paper_meta["total_tokens"]  = 0
        paper_meta["quality"]       = "needs_ocr"
        all_papers.append(paper_meta)
        print(f"  NEEDS_OCR {paper_id}: no chunks emitted")
        return True

    # ── Chunks ────────────────────────────────────────────────────────────────
    paper_chunks = []
    for sec in sections:
        paper_chunks.extend(split_into_chunks(sec, paper_meta))

    # Guard: never emit 0-token chunks
    paper_chunks = [c for c in paper_chunks if c.get("token_count", 0) > 0]

    paper_meta["section_count"] = len(sections)
    paper_meta["chunk_count"]   = len(paper_chunks)
    paper_meta["total_tokens"]  = sum(c["token_count"] for c in paper_chunks)

    all_chunks.extend(paper_chunks)
    all_papers.append(paper_meta)

    # ── References ────────────────────────────────────────────────────────────
    all_refs.extend(extract_references(paper_id, sections))

    # ── Figures + Tables ──────────────────────────────────────────────────────
    for fname, item_type in [("figures.json", "figure"), ("tables.json", "table")]:
        fpath = ext_dir / fname
        if fpath.exists():
            items = json.loads(fpath.read_text(encoding="utf-8"))
            for item in items:
                item_id = item.get("figure_id") or item.get("table_id", "")
                all_figs_tbls.append(
                    {
                        "paper_id":     paper_id,
                        "item_type":    item_type,
                        "item_id":      item_id,
                        "page":         item.get("page", 0),
                        "label":        item.get("label", ""),
                        "caption":      item.get("caption", ""),
                        "needs_review": item.get("needs_review", False),
                    }
                )

    print(
        f"  OK  {paper_id}: "
        f"{len(paper_chunks)} chunks, "
        f"{paper_meta['total_tokens']:,} tokens"
    )
    return True


# ── Batch runner ──────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, records: list):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run(force: bool = False, paper_ids: Optional[set] = None) -> dict:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    papers_file = CORPUS_DIR / "papers.jsonl"
    chunks_file = CORPUS_DIR / "chunks.jsonl"
    refs_file   = CORPUS_DIR / "references.jsonl"
    figs_file   = CORPUS_DIR / "figures_tables.jsonl"

    # ── Load existing corpus data (for incremental runs) ──────────────────────
    all_chunks, all_papers, all_refs, all_figs_tbls = [], [], [], []
    existing_ids: set = set()

    if not force:
        for fpath, lst in [
            (chunks_file, all_chunks),
            (papers_file, all_papers),
            (refs_file,   all_refs),
            (figs_file,   all_figs_tbls),
        ]:
            if fpath.exists():
                with open(fpath, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            lst.append(json.loads(line))
        existing_ids = {c.get("paper_id", "") for c in all_chunks}
        existing_ids |= {p.get("paper_id", "") for p in all_papers}

    # ── Process papers ────────────────────────────────────────────────────────
    papers = iter_papers()
    processed = 0

    for p in papers:
        pid = p["paper_id"]
        if paper_ids is not None and pid not in paper_ids:
            continue
        if pid in existing_ids and not force:
            print(f"  SKIP {pid} (already in corpus)")
            continue

        # Remove stale records for this paper before re-adding
        all_chunks    = [c for c in all_chunks    if c.get("paper_id") != pid]
        all_papers    = [x for x in all_papers    if x.get("paper_id") != pid]
        all_refs      = [r for r in all_refs      if r.get("paper_id") != pid]
        all_figs_tbls = [f for f in all_figs_tbls if f.get("paper_id") != pid]

        if build_paper(pid, all_chunks, all_papers, all_refs, all_figs_tbls):
            processed += 1

    # ── Write JSONL files ─────────────────────────────────────────────────────
    _write_jsonl(chunks_file, all_chunks)
    _write_jsonl(papers_file, all_papers)
    _write_jsonl(refs_file,   all_refs)
    _write_jsonl(figs_file,   all_figs_tbls)

    total_tokens = sum(c.get("token_count", 0) for c in all_chunks)
    return {
        "processed":     processed,
        "total_papers":  len(all_papers),
        "total_chunks":  len(all_chunks),
        "total_tokens":  total_tokens,
        "total_refs":    len(all_refs),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage 3: Build corpus JSONL files")
    parser.add_argument("--force", action="store_true", help="Reprocess all, overwrite corpus")
    parser.add_argument("--pilot", action="store_true", help="Run on pilot papers only")
    args = parser.parse_args()

    ids = None
    if args.pilot:
        ids = {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}

    print("=== Stage 3: Build Corpus ===")
    s = run(force=args.force, paper_ids=ids)
    print(f"\nDone: {s['processed']} papers newly processed")
    print(f"  Total papers in corpus : {s['total_papers']}")
    print(f"  Total chunks           : {s['total_chunks']}")
    print(f"  Total tokens           : {s['total_tokens']:,}")
    print(f"  Total references       : {s['total_refs']}")

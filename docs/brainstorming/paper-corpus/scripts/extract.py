"""
extract.py — Stage 1: PDF → raw extraction artifacts.

For each PDF, produces:
  extracted/{paper_id}/
    full_text.txt         — all pages joined with PAGE markers
    pages/page_NNN.txt    — one file per page (001-indexed)
    metadata.json         — PDF metadata + file provenance
    figures.json          — detected figure captions + nearby text
    tables.json           — detected tables (text or needs_review)
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

from common import (
    EXTRACTED_DIR,
    PAPERS_DIR,
    PILOT_TOPICS,
    iter_papers,
    make_paper_id,
    now_iso,
)

# ── Figure / Table detection patterns ────────────────────────────────────────

FIG_RE   = re.compile(r"(?:Fig(?:ure|\.)?)\s*\.?\s*(\d+)", re.IGNORECASE)
TABLE_RE = re.compile(r"Table\s+(\d+)", re.IGNORECASE)

# ── Extraction quality thresholds ─────────────────────────────────────────────

NO_TEXT_CHAR_THRESHOLD = 200   # body_text_chars below this → no_text
PARTIAL_PAGE_THRESHOLD = 0.5   # fraction of extractable pages below this → partial
EXTRACTABLE_PAGE_CHARS = 50    # chars needed per page to count as extractable


# ── PyMuPDF import (fail with clear message) ─────────────────────────────────

def _fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
        sys.exit(1)


# ── Figure / Table detection ─────────────────────────────────────────────────

def _detect_figures_tables(pages_text: list) -> tuple:
    """
    Scan page text for Figure/Table labels.
    Returns (figures_list, tables_list).
    """
    figures, tables = [], []
    fig_seen, tbl_seen = set(), set()

    for page_no, text in enumerate(pages_text, start=1):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            # ── Figures ──
            m = FIG_RE.search(line)
            if m and m.group(1) not in fig_seen:
                num = m.group(1)
                fig_seen.add(num)
                caption_lines = lines[i : i + 4]
                caption = " ".join(l.strip() for l in caption_lines if l.strip())
                nearby = " ".join(
                    l.strip() for l in lines[max(0, i - 2) : i] if l.strip()
                )
                figures.append(
                    {
                        "figure_id":   f"fig-{len(figures)+1:03d}",
                        "page":        page_no,
                        "label":       f"Figure {num}",
                        "caption":     caption[:500],
                        "nearby_text": nearby[:300],
                        "bbox":        None,
                    }
                )

            # ── Tables ──
            m = TABLE_RE.search(line)
            if m and m.group(1) not in tbl_seen:
                num = m.group(1)
                tbl_seen.add(num)
                caption_lines = lines[i : i + 4]
                caption = " ".join(l.strip() for l in caption_lines if l.strip())
                tables.append(
                    {
                        "table_id":    f"tbl-{len(tables)+1:03d}",
                        "page":        page_no,
                        "label":       f"Table {num}",
                        "caption":     caption[:500],
                        "rows_text":   None,
                        "needs_review": True,
                        "bbox":        None,
                    }
                )

    return figures, tables


def _try_reconstruct_tables(doc, tables: list) -> list:
    """
    Attempt grid-based table reconstruction using PyMuPDF find_tables() (v1.23+).
    Updates tables in-place where possible.
    """
    fitz = _fitz()
    if not hasattr(fitz.Page, "find_tables"):
        return tables  # older pymupdf version

    for page in doc:
        page_no = page.number + 1
        try:
            tab_finder = page.find_tables()
            for tab in tab_finder.tables:
                grid = tab.extract()  # list[list[str|None]]
                if not grid:
                    continue
                # Match to a table record on this page (first unreconstructed match)
                for t in tables:
                    if t["page"] == page_no and t["needs_review"]:
                        t["rows_text"] = [
                            " | ".join(
                                str(cell).strip() if cell else "" for cell in row
                            )
                            for row in grid
                        ]
                        t["needs_review"] = False
                        break
        except Exception:
            pass  # find_tables may not work on all page types

    return tables


# ── Extraction quality analysis ──────────────────────────────────────────────

def _compute_extraction_stats(pages_text: list, page_count: int) -> dict:
    """
    Analyse per-page text to determine extraction quality.
    Returns dict with body_text_chars, extractable_pages, empty_pages,
    extraction_status ('ok'|'partial'|'no_text'), and needs_ocr.
    """
    body_text_chars   = 0
    extractable_pages = 0

    for text in pages_text:
        stripped = text.strip()
        if len(stripped) >= EXTRACTABLE_PAGE_CHARS:
            extractable_pages += 1
        body_text_chars += len(stripped)

    empty_pages = page_count - extractable_pages

    if page_count == 0:
        extraction_status = "ok"
    elif body_text_chars < NO_TEXT_CHAR_THRESHOLD:
        extraction_status = "no_text"
    elif extractable_pages / page_count < PARTIAL_PAGE_THRESHOLD:
        extraction_status = "partial"
    else:
        extraction_status = "ok"

    return {
        "body_text_chars":   body_text_chars,
        "extractable_pages": extractable_pages,
        "empty_pages":       empty_pages,
        "extraction_status": extraction_status,
        "needs_ocr":         extraction_status == "no_text",
    }


# ── Main extraction function ─────────────────────────────────────────────────

def extract_paper(pdf_path: Path, out_dir: Path, force: bool = False) -> dict:
    """
    Extract one PDF into out_dir.
    Returns a stats dict; sets "skipped": True if output exists and not force.
    """
    fitz = _fitz()

    full_txt = out_dir / "full_text.txt"
    if full_txt.exists() and not force:
        return {"skipped": True}

    out_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(exist_ok=True)

    doc = fitz.open(str(pdf_path))
    page_count = len(doc)

    pages_text = []
    full_parts = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages_text.append(text)

        # Per-page file
        (pages_dir / f"page_{i:03d}.txt").write_text(text, encoding="utf-8")

        full_parts.append(f"\n--- PAGE {i} ---\n{text}")

    full_txt.write_text("\n".join(full_parts), encoding="utf-8")

    # ── Extraction quality stats ───────────────────────────────────────────────
    ext_stats = _compute_extraction_stats(pages_text, page_count)

    # ── metadata.json ─────────────────────────────────────────────────────────
    pdf_meta = doc.metadata or {}
    topic = pdf_path.parent.name
    paper_id = make_paper_id(topic, pdf_path.stem)
    # source_pdf relative to ROOT (papers/topic/filename.pdf)
    try:
        rel_path = pdf_path.relative_to(PAPERS_DIR.parent)
        source_pdf = str(rel_path).replace("\\", "/")
    except ValueError:
        source_pdf = str(pdf_path)

    metadata = {
        "paper_id":        paper_id,
        "source_pdf":      source_pdf,
        "topic_folder":    topic,
        "filename":        pdf_path.name,
        "file_size_bytes": pdf_path.stat().st_size,
        "page_count":      page_count,
        "pdf_metadata": {
            "title":    (pdf_meta.get("title")    or "").strip(),
            "author":   (pdf_meta.get("author")   or "").strip(),
            "subject":  (pdf_meta.get("subject")  or "").strip(),
            "keywords": (pdf_meta.get("keywords") or "").strip(),
            "producer": (pdf_meta.get("producer") or "").strip(),
        },
        "extracted_at":      now_iso(),
        "body_text_chars":   ext_stats["body_text_chars"],
        "extractable_pages": ext_stats["extractable_pages"],
        "empty_pages":       ext_stats["empty_pages"],
        "extraction_status": ext_stats["extraction_status"],
        "needs_ocr":         ext_stats["needs_ocr"],
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── figures.json + tables.json ────────────────────────────────────────────
    figures, tables = _detect_figures_tables(pages_text)
    tables = _try_reconstruct_tables(doc, tables)

    (out_dir / "figures.json").write_text(
        json.dumps(figures, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "tables.json").write_text(
        json.dumps(tables, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    doc.close()

    return {
        "skipped":         False,
        "page_count":      page_count,
        "figure_count":    len(figures),
        "table_count":     len(tables),
        "tables_reviewed": sum(1 for t in tables if not t["needs_review"]),
        **ext_stats,
    }


# ── Batch runner ─────────────────────────────────────────────────────────────

def run(force: bool = False, paper_ids: Optional[set] = None) -> dict:
    papers = iter_papers()
    stats = {"processed": 0, "skipped": 0, "total_pages": 0}

    for p in papers:
        if paper_ids is not None and p["paper_id"] not in paper_ids:
            continue

        out_dir = EXTRACTED_DIR / p["paper_id"]
        print(f"  [{p['paper_id']}]", end=" ", flush=True)
        result = extract_paper(p["path"], out_dir, force=force)

        if result.get("skipped"):
            print("SKIP (already extracted)")
            stats["skipped"] += 1
        else:
            if result.get("needs_ocr"):
                print(
                    f"NEEDS_OCR  {result['page_count']}p, "
                    f"{result['body_text_chars']} body chars, "
                    f"{result['empty_pages']} empty pages"
                )
            else:
                reviewed = result["tables_reviewed"]
                total_t  = result["table_count"]
                print(
                    f"OK  {result['page_count']}p, "
                    f"{result['figure_count']} figs, "
                    f"{reviewed}/{total_t} tables reconstructed"
                )
            stats["processed"]   += 1
            stats["total_pages"] += result["page_count"]

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage 1: Extract PDFs")
    parser.add_argument("--force", action="store_true", help="Re-extract even if output exists")
    parser.add_argument("--pilot", action="store_true", help="Run on pilot papers only")
    args = parser.parse_args()

    ids = None
    if args.pilot:
        ids = {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}

    print("=== Stage 1: Extract ===")
    s = run(force=args.force, paper_ids=ids)
    print(
        f"\nDone: {s['processed']} extracted, "
        f"{s['skipped']} skipped, "
        f"{s['total_pages']} total pages"
    )

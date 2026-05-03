"""
validate.py — Stage 5: validate corpus integrity and write reports.

Reads corpus/chunks.jsonl, corpus/papers.jsonl, and normalized/{paper_id}/
to run a suite of checks. Writes:
  reports/batch_status.md  — per-paper pipeline status table
  reports/needs_review.md  — issues grouped by severity
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional

from common import (
    CORPUS_DIR,
    DERIVED_DIR,
    EXTRACTED_DIR,
    NORMALIZED_DIR,
    REPORTS_DIR,
    iter_papers,
    count_tokens,
)

# ── Issue severity levels ─────────────────────────────────────────────────────

ERROR   = "error"
WARNING = "warning"
INFO    = "info"

REQUIRED_CHUNK_FIELDS = [
    "chunk_id", "paper_id", "title", "authors", "year", "topic_folder",
    "section_path", "page_start", "page_end", "content_type", "text",
    "citations_in_text", "contains_equation", "contains_table",
    "contains_figure_caption", "token_count", "source_pdf", "quality",
]

REQUIRED_PAPER_FIELDS = ["paper_id", "title", "authors", "year", "topic_folder", "source_pdf"]


# ── Issue collector ───────────────────────────────────────────────────────────

class IssueCollector:
    def __init__(self):
        self.issues: List[dict] = []

    def add(self, severity: str, paper_id: str, location: str, message: str):
        self.issues.append(
            {
                "severity": severity,
                "paper_id": paper_id,
                "location": location,
                "message":  message,
            }
        )

    def for_paper(self, paper_id: str) -> List[dict]:
        return [i for i in self.issues if i["paper_id"] == paper_id]

    def count(self, severity: str) -> int:
        return sum(1 for i in self.issues if i["severity"] == severity)


# ── Load corpus data ──────────────────────────────────────────────────────────

def _load_jsonl(path: Path) -> List[dict]:
    records = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        pass  # will be caught by other checks
    return records


# ── Individual checks ─────────────────────────────────────────────────────────

def check_chunks(chunks: List[dict], col: IssueCollector):
    """Run all chunk-level checks."""
    for chunk in chunks:
        pid = chunk.get("paper_id", "UNKNOWN")
        cid = chunk.get("chunk_id", "?")
        loc = f"corpus/chunks.jsonl [{cid}]"

        # Required fields
        for field in REQUIRED_CHUNK_FIELDS:
            if field not in chunk:
                col.add(ERROR, pid, loc, f"Missing required field: `{field}`")

        text       = chunk.get("text", "")
        tok_count  = chunk.get("token_count", 0)
        source_pdf = chunk.get("source_pdf", "")
        section_path = chunk.get("section_path", [])

        # Zero-token chunks should never appear in corpus
        if tok_count == 0:
            col.add(ERROR, pid, loc, "Chunk has 0 tokens -- likely from non-extractable PDF")

        # Token outliers
        if 0 < tok_count < 50:
            col.add(WARNING, pid, loc, f"Chunk is very short: {tok_count} tokens")
        if tok_count > 1500:
            col.add(ERROR, pid, loc, f"Chunk exceeds 1500 tokens: {tok_count}")

        # Missing source_pdf
        if not source_pdf:
            col.add(ERROR, pid, loc, "Missing `source_pdf`")

        # Missing section_path
        if not section_path:
            col.add(WARNING, pid, loc, "Empty `section_path`")

        # Malformed MathJax delimiters (unmatched $ or $$)
        dollar_count = text.count("$")
        if dollar_count % 2 != 0:
            col.add(WARNING, pid, loc, f"Unmatched `$` delimiter in chunk text")

        # Unmatched $$ pairs
        dbl_open  = len(re.findall(r"\$\$", text))
        if dbl_open % 2 != 0:
            col.add(WARNING, pid, loc, "Unmatched `$$` block delimiter in chunk text")

        # TODO markers leaked into chunks
        if "<!-- TODO:" in text:
            col.add(INFO, pid, loc, "TODO marker present in chunk text")


def check_papers(papers: List[dict], col: IssueCollector):
    """Run paper-level checks."""
    for paper in papers:
        pid = paper.get("paper_id", "UNKNOWN")
        loc = f"corpus/papers.jsonl [{pid}]"

        # Needs-OCR papers: skip content checks (extraction check handles the error)
        if paper.get("quality") == "needs_ocr":
            continue

        # Required fields
        for field in REQUIRED_PAPER_FIELDS:
            val = paper.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                col.add(
                    ERROR if field in ("paper_id", "source_pdf") else WARNING,
                    pid, loc, f"Missing or empty field: `{field}`"
                )

        # Content integrity
        if paper.get("total_tokens", -1) == 0:
            col.add(ERROR, pid, loc, "Paper has 0 total tokens")
        if paper.get("chunk_count", -1) == 0:
            col.add(ERROR, pid, loc, "Paper has 0 chunks")


def check_normalized(paper_id: str, col: IssueCollector):
    """Check normalized output for a single paper."""
    norm_dir = NORMALIZED_DIR / paper_id

    paper_md = norm_dir / "paper.md"
    sections_f = norm_dir / "sections.json"

    if not paper_md.exists():
        return  # not yet normalized — batch_status will show this

    # TODO markers in paper.md
    md_text = paper_md.read_text(encoding="utf-8")
    todo_count = len(re.findall(r"<!-- TODO:", md_text))
    if todo_count > 0:
        col.add(INFO, paper_id, f"normalized/{paper_id}/paper.md",
                f"{todo_count} TODO marker(s) -- review math and uncertain content")

    if not sections_f.exists():
        col.add(ERROR, paper_id, f"normalized/{paper_id}/",
                "sections.json missing despite paper.md existing")
        return

    sections = json.loads(sections_f.read_text(encoding="utf-8"))

    # Non-extractable papers: skip content checks silently (check_extraction reports the error)
    if any(s.get("quality") == "needs_ocr" for s in sections):
        return

    # Abstract check
    has_abstract = any("abstract" in s["title"].lower() for s in sections)
    if not has_abstract:
        col.add(WARNING, paper_id, f"normalized/{paper_id}/sections.json",
                "Abstract section not detected")

    # References check
    has_refs = any(
        "reference" in s["title"].lower() or "bibliography" in s["title"].lower()
        for s in sections
    )
    if not has_refs:
        col.add(WARNING, paper_id, f"normalized/{paper_id}/sections.json",
                "References section not detected")

    # Raw-to-normalized ratio from conversion_report.md
    report_f = norm_dir / "conversion_report.md"
    if report_f.exists():
        report = report_f.read_text(encoding="utf-8")
        ratio_m = re.search(r"Ratio \(normalized/raw\):\s*([\d.]+)", report)
        if ratio_m:
            ratio = float(ratio_m.group(1))
            if ratio < 0.5:
                col.add(WARNING, paper_id, f"normalized/{paper_id}/conversion_report.md",
                        f"Normalized/raw ratio is {ratio:.2f} -- possible over-stripping")
            elif ratio > 1.1:
                col.add(ERROR, paper_id, f"normalized/{paper_id}/conversion_report.md",
                        f"Normalized/raw ratio is {ratio:.2f} -- check cleaning logic")


def check_extraction(paper_id: str, col: IssueCollector):
    """Check extraction quality from metadata.json."""
    meta_file = EXTRACTED_DIR / paper_id / "metadata.json"
    if not meta_file.exists():
        return  # not yet extracted
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return

    if meta.get("needs_ocr") or meta.get("extraction_status") == "no_text":
        col.add(
            ERROR, paper_id,
            f"extracted/{paper_id}/metadata.json",
            f"PDF has no extractable text "
            f"(body_text_chars={meta.get('body_text_chars', '?')}, "
            f"empty_pages={meta.get('empty_pages', '?')}); "
            "OCR required or remove from corpus",
        )


def check_derived(paper_id: str, col: IssueCollector):
    """Check derived stubs for a single paper."""
    der_dir = DERIVED_DIR / paper_id
    if not der_dir.exists():
        return  # not yet derived

    for fname in ["key_claims.json", "concepts.json", "limitations.json"]:
        fpath = der_dir / fname
        if not fpath.exists():
            col.add(INFO, paper_id, f"derived/{paper_id}/{fname}",
                    "Stub file missing")
            continue

        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            col.add(ERROR, paper_id, f"derived/{paper_id}/{fname}",
                    "Invalid JSON")
            continue

        # If not a stub but has claims/concepts/limitations with no evidence, flag
        if data.get("_status") != "stub":
            items = data.get("claims") or data.get("concepts") or data.get("limitations") or []
            for item in items:
                if not item.get("evidence_chunk_ids"):
                    col.add(
                        INFO, paper_id, f"derived/{paper_id}/{fname}",
                        f"Entry '{item.get('statement') or item.get('term') or '?'}' "
                        "has no evidence_chunk_ids"
                    )


# ── Report writing ────────────────────────────────────────────────────────────

def _pipeline_status(paper_id: str, chunked_ids: set) -> dict:
    return {
        "extracted":  (EXTRACTED_DIR  / paper_id / "full_text.txt").exists(),
        "normalized": (NORMALIZED_DIR / paper_id / "paper.md").exists(),
        "chunked":    paper_id in chunked_ids,
        "derived":    (DERIVED_DIR    / paper_id / "paper_card.md").exists(),
    }


def write_batch_status(papers: list, chunked_ids: set, col: IssueCollector):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Batch Status",
        "",
        "| paper_id | extracted | normalized | chunked | derived | errors | warnings |",
        "|---|:---:|:---:|:---:|:---:|---:|---:|",
    ]

    def tick(v):
        return "✓" if v else "—"

    for p in papers:
        pid = p["paper_id"]
        st  = _pipeline_status(pid, chunked_ids)
        issues = col.for_paper(pid)
        errors   = sum(1 for i in issues if i["severity"] == ERROR)
        warnings = sum(1 for i in issues if i["severity"] == WARNING)
        lines.append(
            f"| `{pid}` "
            f"| {tick(st['extracted'])} "
            f"| {tick(st['normalized'])} "
            f"| {tick(st['chunked'])} "
            f"| {tick(st['derived'])} "
            f"| {errors} "
            f"| {warnings} |"
        )

    total_e = col.count(ERROR)
    total_w = col.count(WARNING)
    total_i = col.count(INFO)
    lines += [
        "",
        f"**Total errors:** {total_e}  ",
        f"**Total warnings:** {total_w}  ",
        f"**Total info:** {total_i}",
    ]

    out = REPORTS_DIR / "batch_status.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote: {out}")


def write_needs_review(col: IssueCollector):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Needs Review",
        "",
        f"**Errors:** {col.count(ERROR)}  "
        f"**Warnings:** {col.count(WARNING)}  "
        f"**Info:** {col.count(INFO)}",
        "",
    ]

    for severity, label in [(ERROR, "Errors"), (WARNING, "Warnings"), (INFO, "Info")]:
        group = [i for i in col.issues if i["severity"] == severity]
        if not group:
            continue
        lines.append(f"## {label} ({len(group)})")
        lines.append("")
        for issue in group:
            lines.append(
                f"- **{issue['paper_id']}** -- `{issue['location']}`  \n"
                f"  {issue['message']}"
            )
        lines.append("")

    out = REPORTS_DIR / "needs_review.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote: {out}")


# ── Main runner ───────────────────────────────────────────────────────────────

def run(paper_ids: Optional[set] = None) -> dict:
    papers_list = iter_papers()
    col = IssueCollector()

    # Load corpus data
    chunks = _load_jsonl(CORPUS_DIR / "chunks.jsonl")
    papers = _load_jsonl(CORPUS_DIR / "papers.jsonl")
    chunked_ids = {c.get("paper_id", "") for c in chunks}

    # Filter if specific paper_ids requested
    if paper_ids is not None:
        chunks = [c for c in chunks if c.get("paper_id") in paper_ids]
        papers = [p for p in papers if p.get("paper_id") in paper_ids]
        papers_list = [p for p in papers_list if p["paper_id"] in paper_ids]

    print("  Running chunk checks...", flush=True)
    check_chunks(chunks, col)

    print("  Running paper metadata checks...", flush=True)
    check_papers(papers, col)

    print("  Running per-paper extraction/normalized/derived checks...", flush=True)
    for p in papers_list:
        check_extraction(p["paper_id"], col)
        check_normalized(p["paper_id"], col)
        check_derived(p["paper_id"], col)

    write_batch_status(papers_list, chunked_ids, col)
    write_needs_review(col)

    return {
        "errors":   col.count(ERROR),
        "warnings": col.count(WARNING),
        "info":     col.count(INFO),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage 5: Validate corpus")
    parser.add_argument("--pilot", action="store_true", help="Validate pilot papers only")
    args = parser.parse_args()

    ids = None
    if args.pilot:
        ids = {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}

    print("=== Stage 5: Validate ===")
    s = run(paper_ids=ids)
    print(
        f"\nResults: {s['errors']} errors, "
        f"{s['warnings']} warnings, "
        f"{s['info']} info"
    )

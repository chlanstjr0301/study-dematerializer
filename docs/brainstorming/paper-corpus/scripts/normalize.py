"""
normalize.py — Stage 2: raw extracted text → structured markdown.

For each paper, reads extracted/{paper_id}/full_text.txt and produces:
  normalized/{paper_id}/
    paper.md              — clean markdown with ## section headers and TODO markers
    sections.json         — structured section list with text and annotations
    conversion_report.md  — summary of what was cleaned and what is uncertain
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict

from common import (
    EXTRACTED_DIR,
    NORMALIZED_DIR,
    PILOT_TOPICS,
    iter_papers,
    count_tokens,
)

# ── Constants ─────────────────────────────────────────────────────────────────

PAGE_MARKER_RE = re.compile(r"\n?--- PAGE (\d+) ---\n?")

LIGATURE_MAP = {
    "\ufb01": "fi",   # ﬁ
    "\ufb02": "fl",   # ﬂ
    "\ufb00": "ff",   # ﬀ
    "\ufb03": "ffi",  # ﬃ
    "\ufb04": "ffl",  # ﬄ
    "\ufb05": "st",   # ﬅ
    "\ufb06": "st",   # ﬆ
    "\u2019": "'",    # right single quotation mark
    "\u2018": "'",    # left single quotation mark
    "\u201c": '"',    # left double quotation mark
    "\u201d": '"',    # right double quotation mark
    "\u2013": "-",    # en dash
    "\u2014": "--",   # em dash
    "\u00ad": "",     # soft hyphen (remove)
    "\u2026": "...",  # ellipsis
}

KNOWN_SECTIONS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "related works",
    "literature review",
    "method",
    "methods",
    "methodology",
    "materials and methods",
    "experimental setup",
    "experimental design",
    "experiments",
    "experiment",
    "study",
    "study design",
    "study 1",
    "study 2",
    "study 3",
    "results",
    "findings",
    "discussion",
    "general discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "future work",
    "future directions",
    "acknowledgements",
    "acknowledgments",
    "references",
    "bibliography",
    "appendix",
    "supplementary",
}

NUMBERED_HEADING_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)*)\s*\.?\s+([A-Z][^\n]{2,80})$"
)
ALLCAPS_HEADING_RE = re.compile(r"^([A-Z][A-Z\s\-]{3,60})$")

# Greek letters and math symbols for equation detection
GREEK_CHARS = set("αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ")
MATH_SYMBOLS = set("∑∏∫∂∇∆±≤≥≠≈∞→←↔⊂⊃∪∩∈∉")


# ── Page splitting ────────────────────────────────────────────────────────────

def split_pages(full_text: str) -> List[str]:
    """Split full_text into list of per-page strings (without markers)."""
    parts = PAGE_MARKER_RE.split(full_text)
    # parts: [pre, page_no, page_text, page_no, page_text, ...]
    pages = []
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                pages.append(parts[i + 1])
    return pages if pages else [full_text]


# ── Cleaning passes ───────────────────────────────────────────────────────────

def detect_repeated_lines(pages: List[str]) -> set:
    """Find short lines appearing on 3+ distinct pages → headers/footers."""
    line_pages: Dict[str, set] = {}
    for page_no, page_text in enumerate(pages):
        for line in page_text.splitlines():
            stripped = line.strip()
            word_count = len(stripped.split())
            if stripped and 1 <= word_count <= 12:
                line_pages.setdefault(stripped, set()).add(page_no)
    return {line for line, seen in line_pages.items() if len(seen) >= 3}


def clean_page(page_text: str, repeated_lines: set) -> str:
    """Remove repeated header/footer lines from a single page."""
    lines = []
    for line in page_text.splitlines():
        if line.strip() not in repeated_lines:
            lines.append(line)
    return "\n".join(lines)


def remove_page_numbers(text: str) -> str:
    """Remove standalone page-number lines."""
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    text = re.sub(r"(?m)^\s*[Pp]age\s+\d+\s+of\s+\d+\s*$", "", text)
    return text


def rejoin_hyphenated(text: str) -> str:
    """Rejoin words split across lines by end-of-line hyphenation."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def repair_two_column(text: str) -> str:
    """
    Heuristic repair for two-column layout artifacts.
    A line that ends abruptly (<40 chars, no sentence-ending punctuation)
    followed by a continuation starting with a lowercase letter is merged.
    """
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if (
            i + 1 < len(lines)
            and 0 < len(stripped) < 40
            and stripped
            and not stripped[-1] in ".!?:;,"
            and lines[i + 1].strip()
            and lines[i + 1].strip()[0].islower()
        ):
            result.append(stripped + " " + lines[i + 1].strip())
            i += 2
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def normalize_unicode_text(text: str) -> str:
    """NFKC normalization + ligature and punctuation substitutions."""
    text = unicodedata.normalize("NFKC", text)
    for src, dst in LIGATURE_MAP.items():
        text = text.replace(src, dst)
    return text


def collapse_whitespace(text: str) -> str:
    """Collapse 3+ consecutive blank lines to 2; strip trailing whitespace."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


# ── Math marking ──────────────────────────────────────────────────────────────

def _is_math_heavy(line: str) -> bool:
    """Check if a line contains a high density of math/Greek characters."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    math_chars = sum(1 for c in stripped if c in GREEK_CHARS or c in MATH_SYMBOLS)
    return math_chars >= 2 and math_chars / len(stripped) > 0.15


def mark_math(text: str) -> tuple:
    """
    Detect math patterns and wrap in MathJax delimiters.
    Uncertain cases get a TODO comment instead of wrapping.
    Returns (marked_text, todo_count, substitution_count).
    """
    lines = text.splitlines()
    result = []
    todo_count = 0
    sub_count = 0
    current_page = 1

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track current page number
        pm = PAGE_MARKER_RE.match(line)
        if pm:
            current_page = int(pm.group(1))
            result.append(line)
            i += 1
            continue

        # Block equation: purely symbolic short line
        if _is_math_heavy(stripped) and len(stripped.split()) <= 6:
            # Check if next line is also math-heavy (multi-line block)
            block_lines = [stripped]
            j = i + 1
            while j < len(lines) and _is_math_heavy(lines[j].strip()) and j < i + 5:
                block_lines.append(lines[j].strip())
                j += 1
            if len(block_lines) > 1 or len(stripped.split()) <= 4:
                result.append("$$")
                result.extend(block_lines)
                result.append("$$")
                sub_count += 1
                i = j
                continue

        # Line with Greek/math that's NOT a clean block → flag with TODO
        if _is_math_heavy(stripped) and len(stripped) > 10:
            result.append(line)
            result.append(
                f"<!-- TODO: verify equation against PDF page {current_page} -->"
            )
            todo_count += 1
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result), todo_count, sub_count


# ── Section detection ─────────────────────────────────────────────────────────

def detect_sections(text: str, page_count: int) -> List[dict]:
    """
    Detect section headings and split text into section dicts.
    Each dict: {section_id, title, level, line_start, line_end, text=""}
    """
    lines = text.splitlines()
    headings = []  # (line_index, title, level)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Priority 1: Numbered heading (e.g. "1 Introduction", "2.3 Results")
        m = NUMBERED_HEADING_RE.match(stripped)
        if m:
            num_part = m.group(1)
            title = m.group(2).strip()
            # Exclude if it looks like a list item or paragraph start
            if len(title.split()) >= 2 or title.lower() in KNOWN_SECTIONS:
                level = num_part.count(".") + 1
                headings.append((i, title, min(level, 3)))
                continue

        # Priority 2: Known section name on its own line
        lower = stripped.lower()
        if lower in KNOWN_SECTIONS and len(stripped.split()) <= 5:
            # Avoid capturing inline mentions: must be short and on its own
            headings.append((i, stripped.title(), 1))
            continue

        # Priority 3: ALL-CAPS short line (≤8 words, no sentence punctuation)
        # Requires a blank line immediately before it to avoid table row headers.
        m = ALLCAPS_HEADING_RE.match(stripped)
        if m:
            words = stripped.split()
            if 2 <= len(words) <= 8 and not re.search(r"[.!?,;]$", stripped):
                prev_line = lines[i - 1].strip() if i > 0 else ""
                # Must be preceded by a blank line (strong heading signal)
                if not prev_line:
                    headings.append((i, stripped.title(), 1))
                    continue

    # ── Fallback: no sections detected ───────────────────────────────────────
    if not headings:
        # Attach text directly here; avoids falling through to the
        # attachment loop which would fail because line_start/line_end
        # have already been discarded on early return.
        return [
            {
                "section_id": "s01",
                "title":      "Full Text",
                "level":      1,
                "text":       "\n".join(lines).strip(),
            }
        ]

    # ── Build section list from heading boundaries ────────────────────────────
    sections = []

    # Preamble (text before first heading)
    first_heading_line = headings[0][0]
    if first_heading_line > 5:
        preamble_text = "\n".join(lines[:first_heading_line]).strip()
        if len(preamble_text.split()) > 20:
            sections.append(
                {
                    "section_id": "s00",
                    "title":      "Preamble",
                    "level":      1,
                    "line_start": 0,
                    "line_end":   first_heading_line,
                }
            )

    for idx, (line_no, title, level) in enumerate(headings):
        next_line = (
            headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        )
        sections.append(
            {
                "section_id": f"s{len(sections)+1:02d}",
                "title":      title,
                "level":      level,
                "line_start": line_no + 1,  # body starts after heading
                "line_end":   next_line,
            }
        )

    # ── Attach text ───────────────────────────────────────────────────────────
    for s in sections:
        body = "\n".join(lines[s["line_start"] : s["line_end"]]).strip()
        s["text"] = body
        del s["line_start"]
        del s["line_end"]

    return sections


# ── Schema normalization ──────────────────────────────────────────────────────

def _ensure_section_schema(sections: List[dict]) -> tuple:
    """
    Guarantee every section dict has the required keys.

    Required keys: section_id, title, level, text.
    Tolerates sections that are still in the intermediate builder form
    (line_start / line_end present, text absent) and repairs them.

    Returns (repaired_sections, schema_warnings) where schema_warnings is a
    list of dicts {section_id, title, warning} for any repairs made.
    The repaired sections have 'text' set and line_start/line_end removed.
    """
    schema_warnings = []

    for s in sections:
        # ── Ensure section_id ─────────────────────────────────────────────
        if "section_id" not in s:
            s["section_id"] = "s??"
            schema_warnings.append(
                {"section_id": "s??", "title": s.get("title", "?"), "warning": "missing section_id"}
            )

        # ── Ensure title ──────────────────────────────────────────────────
        if "title" not in s:
            s["title"] = "(untitled)"
            schema_warnings.append(
                {"section_id": s["section_id"], "title": "(untitled)", "warning": "missing title"}
            )

        # ── Ensure level ──────────────────────────────────────────────────
        if "level" not in s:
            s["level"] = 1
            schema_warnings.append(
                {"section_id": s["section_id"], "title": s["title"], "warning": "missing level; defaulted to 1"}
            )

        # ── Ensure text ───────────────────────────────────────────────────
        if "text" not in s:
            # Case 1: still in intermediate form with line_start / line_end
            if "line_start" in s and "line_end" in s:
                schema_warnings.append(
                    {
                        "section_id": s["section_id"],
                        "title":      s["title"],
                        "warning":    "text missing; section was in intermediate builder form (line_start/line_end present). Repaired.",
                    }
                )
                # Cannot reconstruct text without the original lines here,
                # so set to empty and let downstream flag it.
                s["text"] = ""
            # Case 2: alternate field names
            elif "content" in s:
                s["text"] = s.pop("content")
                schema_warnings.append(
                    {"section_id": s["section_id"], "title": s["title"], "warning": "text missing; copied from 'content' field"}
                )
            elif "body" in s:
                s["text"] = s.pop("body")
                schema_warnings.append(
                    {"section_id": s["section_id"], "title": s["title"], "warning": "text missing; copied from 'body' field"}
                )
            else:
                s["text"] = ""
                schema_warnings.append(
                    {"section_id": s["section_id"], "title": s["title"], "warning": "text missing and no recoverable field found; set to empty string"}
                )

        # ── Remove builder-only keys ──────────────────────────────────────
        s.pop("line_start", None)
        s.pop("line_end", None)

    return sections, schema_warnings


# ── Page-range computation ────────────────────────────────────────────────────

def _page_range(section_text: str, full_text_with_markers: str) -> tuple:
    """
    Locate section text within the original (with-markers) text to determine
    page range. Returns (page_start, page_end).
    """
    if not section_text:
        return 1, 1

    # Use first 80 chars of section text as search anchor
    anchor = section_text[:80].strip()
    if not anchor:
        return 1, 1

    pos = full_text_with_markers.find(anchor)
    if pos == -1:
        # Try shorter anchor
        anchor = section_text[:40].strip()
        pos = full_text_with_markers.find(anchor)
    if pos == -1:
        return 1, 1

    before = full_text_with_markers[:pos]
    page_markers_before = re.findall(r"--- PAGE (\d+) ---", before)
    page_start = int(page_markers_before[-1]) if page_markers_before else 1

    within = full_text_with_markers[pos : pos + len(section_text)]
    page_markers_within = re.findall(r"--- PAGE (\d+) ---", within)
    page_end = int(page_markers_within[-1]) if page_markers_within else page_start

    return page_start, page_end


# ── Section annotation ────────────────────────────────────────────────────────

def annotate_section(s: dict) -> dict:
    """Add has_equations, has_table_refs, has_figure_refs, todo_count to section."""
    text = s["text"]
    s["has_equations"]      = bool(re.search(r"\$\$.+?\$\$|\$.+?\$", text, re.DOTALL))
    s["has_table_refs"]     = bool(re.search(r"\bTable\s+\d+", text, re.IGNORECASE))
    s["has_figure_refs"]    = bool(re.search(r"\bFig(?:ure|\.)?\.?\s*\d+", text, re.IGNORECASE))
    s["todo_count"]         = len(re.findall(r"<!-- TODO:", text))
    return s


# ── Non-extractable PDF handler ───────────────────────────────────────────────

def _write_non_extractable(
    paper_id: str, norm_dir: Path, page_count: int, empty_pages: int, body_text_chars: int
) -> dict:
    """Write marker files for scanned/image PDFs that have no extractable text."""
    norm_dir.mkdir(parents=True, exist_ok=True)

    (norm_dir / "paper.md").write_text(
        f"# {paper_id}\n\n"
        "<!-- NON-EXTRACTABLE PDF: This PDF contains no extractable text. "
        "OCR is required before this paper can be processed. -->\n",
        encoding="utf-8",
    )

    sections = [
        {
            "section_id":      "s01",
            "title":           "Non-extractable PDF",
            "level":           1,
            "page_start":      1,
            "page_end":        max(page_count, 1),
            "text":            "",
            "has_equations":   False,
            "has_table_refs":  False,
            "has_figure_refs": False,
            "todo_count":      0,
            "quality":         "needs_ocr",
        }
    ]
    (norm_dir / "sections.json").write_text(
        json.dumps(sections, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report = "\n".join([
        f"# Conversion Report: {paper_id}",
        "",
        "**Extraction status:** NON-EXTRACTABLE (needs OCR)",
        "",
        f"**Page count:** {page_count}  ",
        f"**Empty pages:** {empty_pages}  ",
        f"**Body text chars:** {body_text_chars}  ",
        "",
        "> ERROR: This PDF has no extractable text. PyMuPDF returned empty or",
        "> near-empty text for all pages. The document is likely a scanned image.",
        "> Apply OCR (e.g. ocrmypdf) before re-running the pipeline.",
        "",
        "## Sections detected (0)",
        "",
        "*(No sections -- PDF is non-extractable.)*",
        "",
        "## Math handling",
        "- MathJax blocks written: 0",
        "- TODO markers (uncertain math): 0",
        "",
        "*(Review PDF manually and apply OCR before reprocessing.)*",
    ]) + "\n"
    (norm_dir / "conversion_report.md").write_text(report, encoding="utf-8")

    return {
        "skipped":          False,
        "needs_ocr":        True,
        "page_count":       page_count,
        "empty_pages":      empty_pages,
        "body_text_chars":  body_text_chars,
    }


# ── Main normalization function ───────────────────────────────────────────────

def normalize_paper(paper_id: str, force: bool = False) -> dict:
    ext_dir  = EXTRACTED_DIR  / paper_id
    norm_dir = NORMALIZED_DIR / paper_id

    if (norm_dir / "paper.md").exists() and not force:
        return {"skipped": True}

    full_txt = ext_dir / "full_text.txt"
    if not full_txt.exists():
        return {"error": f"Not yet extracted: {paper_id}"}

    # ── Check extraction quality ───────────────────────────────────────────────
    meta_file = ext_dir / "metadata.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if meta.get("needs_ocr") or meta.get("extraction_status") == "no_text":
                return _write_non_extractable(
                    paper_id, norm_dir,
                    page_count=meta.get("page_count", 0),
                    empty_pages=meta.get("empty_pages", 0),
                    body_text_chars=meta.get("body_text_chars", 0),
                )
        except Exception:
            pass  # if metadata is unreadable, proceed with normal normalization

    raw_text = full_txt.read_text(encoding="utf-8")
    raw_char_count = len(raw_text)

    # ── Pass 1: per-page header/footer removal ────────────────────────────────
    pages = split_pages(raw_text)
    repeated_lines = detect_repeated_lines(pages)
    cleaned_pages = [clean_page(p, repeated_lines) for p in pages]
    cleaned = "\n\n".join(cleaned_pages)

    # ── Pass 2: global cleaning ───────────────────────────────────────────────
    cleaned = remove_page_numbers(cleaned)
    cleaned = rejoin_hyphenated(cleaned)
    cleaned = repair_two_column(cleaned)
    cleaned = normalize_unicode_text(cleaned)
    cleaned = collapse_whitespace(cleaned)

    norm_char_count = len(cleaned)
    ratio = norm_char_count / raw_char_count if raw_char_count else 0.0

    # ── Pass 3: math marking ──────────────────────────────────────────────────
    cleaned, todo_count, math_sub_count = mark_math(cleaned)

    # ── Pass 4: section detection ─────────────────────────────────────────────
    raw_sections = detect_sections(cleaned, len(pages))

    # ── Pass 4b: schema normalization (defensive guard) ───────────────────────
    # Guarantees every section has section_id, title, level, and text before
    # any downstream code accesses those keys.
    raw_sections, schema_warnings = _ensure_section_schema(raw_sections)

    # ── Pass 5: page ranges + annotations ────────────────────────────────────
    final_sections = []
    for s in raw_sections:
        page_start, page_end = _page_range(s.get("text", ""), raw_text)
        s["page_start"] = page_start
        s["page_end"]   = page_end
        annotate_section(s)
        final_sections.append(s)

    # ── Generate paper.md ─────────────────────────────────────────────────────
    md_parts = [f"# {paper_id}\n"]
    for s in final_sections:
        prefix = "#" * (s["level"] + 1)  # ## for level 1, ### for level 2
        header = f"{prefix} {s['title']}"
        md_parts.append(f"{header}\n\n{s['text']}")
    paper_md = "\n\n---\n\n".join(md_parts)

    # ── Write outputs ─────────────────────────────────────────────────────────
    norm_dir.mkdir(parents=True, exist_ok=True)
    (norm_dir / "paper.md").write_text(paper_md, encoding="utf-8")

    # sections.json — only serializable fields
    sections_out = []
    for s in final_sections:
        sections_out.append(
            {
                "section_id":         s["section_id"],
                "title":              s["title"],
                "level":              s["level"],
                "page_start":         s["page_start"],
                "page_end":           s["page_end"],
                "text":               s["text"],
                "has_equations":      s["has_equations"],
                "has_table_refs":     s["has_table_refs"],
                "has_figure_refs":    s["has_figure_refs"],
                "todo_count":         s["todo_count"],
            }
        )
    (norm_dir / "sections.json").write_text(
        json.dumps(sections_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── conversion_report.md ──────────────────────────────────────────────────
    report_lines = [
        f"# Conversion Report: {paper_id}",
        "",
        f"**Raw chars:** {raw_char_count:,}  ",
        f"**Normalized chars:** {norm_char_count:,}  ",
        f"**Ratio (normalized/raw):** {ratio:.3f}",
        "",
    ]

    # Ratio warnings
    if ratio < 0.5:
        report_lines.append(
            "> WARNING: normalized text is < 50% of raw -- possible over-stripping."
        )
        report_lines.append("")
    elif ratio > 1.1:
        report_lines.append(
            "> WARNING: normalized text > 110% of raw -- check cleaning logic."
        )
        report_lines.append("")

    report_lines += [
        f"## Repeated lines removed ({len(repeated_lines)} patterns)",
        "",
    ]
    for line in sorted(repeated_lines)[:20]:
        report_lines.append(f"- `{line[:100]}`")
    if len(repeated_lines) > 20:
        report_lines.append(f"- *(and {len(repeated_lines) - 20} more)*")

    report_lines += [
        "",
        f"## Sections detected ({len(final_sections)})",
        "",
    ]
    for s in final_sections:
        token_est = count_tokens(s["text"])
        eqs = " [EQ]" if s["has_equations"] else ""
        report_lines.append(
            f"- **[{s['section_id']}]** L{s['level']} \"{s['title']}\" "
            f"p.{s['page_start']}-{s['page_end']}, ~{token_est} tokens{eqs}"
        )

    # Schema warnings section (only emitted when repairs occurred)
    if schema_warnings:
        report_lines += [
            "",
            f"## Section Schema Warnings ({len(schema_warnings)} repairs)",
            "",
            "> The section builder produced dicts with missing required fields.",
            "> These were automatically repaired. Review the sections below.",
            "",
        ]
        for w in schema_warnings:
            report_lines.append(
                f"- **[{w['section_id']}]** \"{w['title']}\": {w['warning']}"
            )

    report_lines += [
        "",
        f"## Math handling",
        f"- MathJax blocks written: {math_sub_count}",
        f"- TODO markers (uncertain math): {todo_count}",
        "",
        "*(Review `<!-- TODO: ... -->` markers in paper.md for manual verification.)*",
    ]

    (norm_dir / "conversion_report.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    return {
        "skipped":                  False,
        "section_count":            len(final_sections),
        "repeated_lines_removed":   len(repeated_lines),
        "ratio":                    ratio,
        "todo_count":               todo_count,
        "math_blocks":              math_sub_count,
        "schema_warnings":          len(schema_warnings),
    }


# ── Batch runner ──────────────────────────────────────────────────────────────

def run(force: bool = False, paper_ids: Optional[set] = None) -> dict:
    papers = iter_papers()
    stats = {"processed": 0, "skipped": 0, "errors": 0, "needs_ocr": 0}

    for p in papers:
        if paper_ids is not None and p["paper_id"] not in paper_ids:
            continue

        print(f"  [{p['paper_id']}]", end=" ", flush=True)
        result = normalize_paper(p["paper_id"], force=force)

        if result.get("skipped"):
            print("SKIP")
            stats["skipped"] += 1
        elif result.get("error"):
            print(f"ERROR: {result['error']}")
            stats["errors"] += 1
        elif result.get("needs_ocr"):
            print(
                f"NEEDS_OCR  {result['page_count']}p, "
                f"{result['body_text_chars']} body chars, "
                f"{result['empty_pages']} empty pages"
            )
            stats["needs_ocr"] += 1
        else:
            sw = result.get("schema_warnings", 0)
            schema_note = f", {sw} schema repairs" if sw else ""
            print(
                f"OK  {result['section_count']} sections, "
                f"ratio={result['ratio']:.2f}, "
                f"{result['todo_count']} TODOs, "
                f"{result['math_blocks']} math blocks"
                f"{schema_note}"
            )
            stats["processed"] += 1

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage 2: Normalize extracted text")
    parser.add_argument("--force", action="store_true", help="Reprocess even if output exists")
    parser.add_argument("--pilot", action="store_true", help="Run on pilot papers only")
    args = parser.parse_args()

    ids = None
    if args.pilot:
        ids = {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}

    print("=== Stage 2: Normalize ===")
    s = run(force=args.force, paper_ids=ids)
    print(
        f"\nDone: {s['processed']} normalized, "
        f"{s['skipped']} skipped, "
        f"{s['errors']} errors, "
        f"{s['needs_ocr']} needs_ocr"
    )

"""
inventory.py — Stage 0: scan papers/ and write reports/inventory.md.

Read-only pass: never writes to extracted/, normalized/, corpus/, or derived/.
"""

import json
import sys
from pathlib import Path

from common import (
    CORPUS_DIR,
    DERIVED_DIR,
    EXTRACTED_DIR,
    NORMALIZED_DIR,
    REPORTS_DIR,
    iter_papers,
)


def _chunked_ids() -> set:
    """Collect paper_ids that already have chunks in corpus/chunks.jsonl."""
    ids = set()
    f = CORPUS_DIR / "chunks.jsonl"
    if f.exists():
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["paper_id"])
                    except Exception:
                        pass
    return ids


def paper_status(paper_id: str, chunked_ids: set) -> dict:
    return {
        "extracted":  (EXTRACTED_DIR  / paper_id / "full_text.txt").exists(),
        "normalized": (NORMALIZED_DIR / paper_id / "paper.md").exists(),
        "chunked":    paper_id in chunked_ids,
        "derived":    (DERIVED_DIR    / paper_id / "paper_card.md").exists(),
    }


def run() -> list:
    papers = iter_papers()
    chunked_ids = _chunked_ids()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in papers:
        st = paper_status(p["paper_id"], chunked_ids)
        size_kb = round(p["path"].stat().st_size / 1024, 1)
        rows.append({**p, **st, "size_kb": size_kb})

    # ── Markdown table ────────────────────────────────────────────────────────
    def tick(v):
        return "✓" if v else "—"

    md_lines = [
        "# Paper Corpus Inventory",
        "",
        f"**Total papers:** {len(papers)}",
        f"**Papers directory:** `papers/`",
        "",
        "| paper_id | topic | filename | size_kb | extracted | normalized | chunked | derived |",
        "|---|---|---|---:|:---:|:---:|:---:|:---:|",
    ]
    for r in rows:
        md_lines.append(
            f"| `{r['paper_id']}` | {r['topic']} | {r['path'].name} | {r['size_kb']} "
            f"| {tick(r['extracted'])} | {tick(r['normalized'])} "
            f"| {tick(r['chunked'])} | {tick(r['derived'])} |"
        )

    out = REPORTS_DIR / "inventory.md"
    out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # ── Stdout summary ────────────────────────────────────────────────────────
    w = 72
    print(f"\n  {'PAPER ID':<{w}} {'EXTR':>5} {'NORM':>5} {'CHUNK':>6} {'DERIV':>6}")
    print("  " + "-" * (w + 22))
    for r in rows:
        def yn(v):
            return "yes" if v else "no"
        print(
            f"  {r['paper_id']:<{w}} "
            f"{yn(r['extracted']):>5} {yn(r['normalized']):>5} "
            f"{yn(r['chunked']):>6} {yn(r['derived']):>6}"
        )
    print(f"\n  Wrote: {out}")
    return rows


if __name__ == "__main__":
    print("=== Stage 0: Inventory ===")
    run()

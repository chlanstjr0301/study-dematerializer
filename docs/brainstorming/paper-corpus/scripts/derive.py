"""
derive.py — Stage 4: write stub templates with embedded LLM prompts.

No LLM API calls. Reads already-processed data and writes:
  derived/{paper_id}/
    paper_card.md     — structured template; abstract auto-filled; TODOs for LLM
    key_claims.json   — stub with embedded prompt and evidence_chunk_ids placeholder
    concepts.json     — stub with embedded prompt
    limitations.json  — stub with embedded prompt

Each derived file embeds the LLM prompt needed to fill it in.
All claims must eventually reference chunk_ids from corpus/chunks.jsonl.
"""

import json
from pathlib import Path
from typing import Optional

from common import (
    CORPUS_DIR,
    DERIVED_DIR,
    NORMALIZED_DIR,
    PILOT_TOPICS,
    iter_papers,
)


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_paper_meta(paper_id: str) -> Optional[dict]:
    """Retrieve paper record from corpus/papers.jsonl."""
    f = CORPUS_DIR / "papers.jsonl"
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                if rec.get("paper_id") == paper_id:
                    return rec
    return None


def _load_abstract(paper_id: str) -> str:
    """Pull abstract text from normalized sections.json."""
    f = NORMALIZED_DIR / paper_id / "sections.json"
    if not f.exists():
        return ""
    sections = json.loads(f.read_text(encoding="utf-8"))
    for s in sections:
        if "abstract" in s["title"].lower():
            return s["text"].strip()
    return ""


def _load_chunk_ids(paper_id: str) -> list:
    """Collect all chunk_ids for a paper from corpus/chunks.jsonl."""
    f = CORPUS_DIR / "chunks.jsonl"
    ids = []
    if f.exists():
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if rec.get("paper_id") == paper_id:
                        ids.append(rec["chunk_id"])
    return ids


# ── Stub writers ──────────────────────────────────────────────────────────────

def _write_paper_card(out_dir: Path, paper_id: str, meta: dict, abstract: str):
    title   = meta.get("title")  or f"[{paper_id}]"
    authors = ", ".join(meta.get("authors", [])) or "Unknown"
    year    = meta.get("year", "")
    topic   = meta.get("topic_folder", "")
    source  = meta.get("source_pdf", "")

    abstract_block = (
        abstract if abstract
        else "<!-- TODO: abstract not detected in normalized text -->"
    )

    content = f"""# {title}

**Authors:** {authors}
**Year:** {year}
**Topic:** {topic}
**Source:** `{source}`
**paper_id:** `{paper_id}`

---

## Abstract

{abstract_block}

---

## Research Question

<!-- TODO LLM prompt:
     Using the chunks in corpus/chunks.jsonl with paper_id={paper_id},
     state the central research question in 1-2 sentences.
     Cite the supporting chunk_id. -->

---

## Key Findings

<!-- TODO LLM prompt:
     List 3-5 key empirical or theoretical findings from this paper.
     For each finding, cite the chunk_id from corpus/chunks.jsonl. -->

---

## Methodology

<!-- TODO LLM prompt:
     Describe the research design and methods in 2-3 sentences.
     Cite supporting chunk_ids. -->

---

*This file is a stub. Fill in the TODO sections by running an LLM over the*
*chunk text referenced by the embedded prompts above.*
*Every claim must reference a chunk_id from `corpus/chunks.jsonl`.*
"""
    (out_dir / "paper_card.md").write_text(content, encoding="utf-8")


def _write_key_claims(out_dir: Path, paper_id: str, chunk_ids: list):
    stub = {
        "paper_id": paper_id,
        "claims": [],
        "_status": "stub",
        "_prompt": (
            f"Using the chunks in corpus/chunks.jsonl with paper_id={paper_id}, "
            "identify the major claims this paper makes. "
            "For each claim provide a JSON object with: "
            "{ "
            "  \"statement\": \"...\", "
            "  \"evidence_chunk_ids\": [\"<chunk_id>\", ...], "
            "  \"confidence\": \"low\" | \"medium\" | \"high\", "
            "  \"claim_type\": \"empirical\" | \"theoretical\" | \"methodological\" "
            "}"
        ),
        "_available_chunk_ids": chunk_ids[:10],  # first 10 for reference
    }
    (out_dir / "key_claims.json").write_text(
        json.dumps(stub, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_concepts(out_dir: Path, paper_id: str, chunk_ids: list):
    stub = {
        "paper_id": paper_id,
        "concepts": [],
        "_status": "stub",
        "_prompt": (
            f"Using the chunks in corpus/chunks.jsonl with paper_id={paper_id}, "
            "extract the key concepts and technical terms introduced or defined. "
            "For each concept provide: "
            "{ "
            "  \"term\": \"...\", "
            "  \"definition\": \"...\", "
            "  \"evidence_chunk_ids\": [\"<chunk_id>\", ...], "
            "  \"domain\": \"...\" "
            "}"
        ),
        "_available_chunk_ids": chunk_ids[:10],
    }
    (out_dir / "concepts.json").write_text(
        json.dumps(stub, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_limitations(out_dir: Path, paper_id: str, chunk_ids: list):
    stub = {
        "paper_id": paper_id,
        "limitations": [],
        "_status": "stub",
        "_prompt": (
            f"Using the chunks in corpus/chunks.jsonl with paper_id={paper_id}, "
            "identify limitations stated or implied by the authors. "
            "For each limitation provide: "
            "{ "
            "  \"description\": \"...\", "
            "  \"evidence_chunk_ids\": [\"<chunk_id>\", ...], "
            "  \"limitation_type\": \"scope\" | \"methodology\" | \"generalizability\" | \"replication\" "
            "}"
        ),
        "_available_chunk_ids": chunk_ids[:10],
    }
    (out_dir / "limitations.json").write_text(
        json.dumps(stub, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ── Per-paper derive ──────────────────────────────────────────────────────────

def derive_paper(paper_id: str, force: bool = False) -> dict:
    out_dir = DERIVED_DIR / paper_id

    if (out_dir / "paper_card.md").exists() and not force:
        return {"skipped": True}

    meta = _load_paper_meta(paper_id)
    if meta is None:
        return {
            "error": (
                f"No corpus record found for {paper_id}. "
                "Run build_corpus.py first."
            )
        }

    abstract  = _load_abstract(paper_id)
    chunk_ids = _load_chunk_ids(paper_id)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_paper_card(out_dir, paper_id, meta, abstract)
    _write_key_claims(out_dir, paper_id, chunk_ids)
    _write_concepts(out_dir, paper_id, chunk_ids)
    _write_limitations(out_dir, paper_id, chunk_ids)

    return {"skipped": False, "chunk_ids_available": len(chunk_ids)}


# ── Batch runner ──────────────────────────────────────────────────────────────

def run(force: bool = False, paper_ids: Optional[set] = None) -> dict:
    papers = iter_papers()
    stats = {"processed": 0, "skipped": 0, "errors": 0}

    for p in papers:
        if paper_ids is not None and p["paper_id"] not in paper_ids:
            continue

        print(f"  [{p['paper_id']}]", end=" ", flush=True)
        result = derive_paper(p["paper_id"], force=force)

        if result.get("skipped"):
            print("SKIP")
            stats["skipped"] += 1
        elif result.get("error"):
            print(f"ERROR: {result['error']}")
            stats["errors"] += 1
        else:
            n = result.get("chunk_ids_available", 0)
            print(f"OK  stubs written ({n} chunk_ids available)")
            stats["processed"] += 1

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stage 4: Write derived stub templates")
    parser.add_argument("--force", action="store_true", help="Overwrite existing stubs")
    parser.add_argument("--pilot", action="store_true", help="Run on pilot papers only")
    args = parser.parse_args()

    ids = None
    if args.pilot:
        ids = {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}

    print("=== Stage 4: Derive (stubs) ===")
    s = run(force=args.force, paper_ids=ids)
    print(
        f"\nDone: {s['processed']} written, "
        f"{s['skipped']} skipped, "
        f"{s['errors']} errors"
    )

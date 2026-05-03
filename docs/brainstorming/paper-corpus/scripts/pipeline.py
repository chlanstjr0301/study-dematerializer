"""
pipeline.py — Orchestrator for the paper-corpus preprocessing pipeline.

Stage order:
  inventory -> extract -> normalize -> corpus -> derive -> validate

Usage:
  python scripts/pipeline.py                         # print status table
  python scripts/pipeline.py --pilot                 # run all stages on 2 pilot papers
  python scripts/pipeline.py --pilot --stage extract # run one stage on pilot papers
  python scripts/pipeline.py --all                   # run all stages on all 13 papers
  python scripts/pipeline.py --stage normalize --paper <paper_id>
  python scripts/pipeline.py --all --force           # reprocess everything
"""

import argparse
import sys
import time
from typing import Optional

# Ensure scripts/ directory is on sys.path so sibling modules import correctly
import os
sys.path.insert(0, os.path.dirname(__file__))

from common import PILOT_TOPICS, iter_papers

STAGES = ["inventory", "extract", "normalize", "corpus", "derive", "validate"]


def _pilot_ids() -> set:
    return {p["paper_id"] for p in iter_papers() if p["topic"] in PILOT_TOPICS}


def _single_paper_ids(paper_id: str) -> set:
    known = {p["paper_id"] for p in iter_papers()}
    if paper_id not in known:
        print(f"ERROR: Unknown paper_id '{paper_id}'")
        print(f"Known IDs:\n" + "\n".join(f"  {pid}" for pid in sorted(known)))
        sys.exit(1)
    return {paper_id}


# ── Stage runners ─────────────────────────────────────────────────────────────

def run_inventory():
    import inventory
    inventory.run()


def run_extract(force: bool, paper_ids: Optional[set]):
    import extract
    return extract.run(force=force, paper_ids=paper_ids)


def run_normalize(force: bool, paper_ids: Optional[set]):
    import normalize
    return normalize.run(force=force, paper_ids=paper_ids)


def run_corpus(force: bool, paper_ids: Optional[set]):
    import build_corpus
    return build_corpus.run(force=force, paper_ids=paper_ids)


def run_derive(force: bool, paper_ids: Optional[set]):
    import derive
    return derive.run(force=force, paper_ids=paper_ids)


def run_validate(paper_ids: Optional[set]):
    import validate
    return validate.run(paper_ids=paper_ids)


# ── Dispatch ──────────────────────────────────────────────────────────────────

STAGE_RUNNERS = {
    "inventory": lambda force, ids: run_inventory(),
    "extract":   lambda force, ids: run_extract(force, ids),
    "normalize": lambda force, ids: run_normalize(force, ids),
    "corpus":    lambda force, ids: run_corpus(force, ids),
    "derive":    lambda force, ids: run_derive(force, ids),
    "validate":  lambda force, ids: run_validate(ids),
}

STAGE_LABELS = {
    "inventory": "Stage 0: Inventory",
    "extract":   "Stage 1: Extract",
    "normalize": "Stage 2: Normalize",
    "corpus":    "Stage 3: Build Corpus",
    "derive":    "Stage 4: Derive (stubs)",
    "validate":  "Stage 5: Validate",
}


def _run_stage(stage: str, force: bool, paper_ids: Optional[set]):
    print(f"\n{'='*60}")
    print(f"  {STAGE_LABELS[stage]}")
    print(f"{'='*60}")
    t0 = time.time()
    result = STAGE_RUNNERS[stage](force, paper_ids)
    elapsed = time.time() - t0
    print(f"\n  [{stage}] completed in {elapsed:.1f}s")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Paper-corpus preprocessing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pipeline.py                          Print status table
  python scripts/pipeline.py --pilot                  Full pipeline on 2 pilot papers
  python scripts/pipeline.py --pilot --stage extract  Extract pilot papers only
  python scripts/pipeline.py --all                    Full pipeline on all 13 papers
  python scripts/pipeline.py --stage normalize --paper cognitive-load-theory_s10648-019-09465-5
  python scripts/pipeline.py --all --force            Re-run everything from scratch

Stages (in order): inventory -> extract -> normalize -> corpus -> derive -> validate
        """,
    )

    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--pilot",
        action="store_true",
        help="Run on the two pilot papers only (safe default for first run)",
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="Run on ALL 13 papers (explicit opt-in required)",
    )
    scope.add_argument(
        "--paper",
        metavar="PAPER_ID",
        help="Run on a single paper by paper_id",
    )

    parser.add_argument(
        "--stage",
        choices=STAGES,
        metavar="STAGE",
        help=f"Run a single stage: {', '.join(STAGES)}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess even if outputs already exist",
    )

    args = parser.parse_args()

    # ── Determine scope ───────────────────────────────────────────────────────
    if args.pilot:
        paper_ids = _pilot_ids()
        scope_label = f"pilot ({len(paper_ids)} papers)"
    elif args.all:
        paper_ids = None  # None means "all papers"
        scope_label = "ALL papers"
    elif args.paper:
        paper_ids = _single_paper_ids(args.paper)
        scope_label = f"paper: {args.paper}"
    else:
        # No scope flag: print inventory and exit
        print("=== Paper Corpus Pipeline -- Status ===")
        run_inventory()
        print(
            "\nTo run the pipeline, specify a scope:\n"
            "  --pilot      (2 pilot papers, recommended first run)\n"
            "  --all        (all 13 papers)\n"
            "  --paper ID   (single paper)\n"
            "\nAdd --stage NAME to run one stage only."
        )
        return

    # ── Determine stages to run ───────────────────────────────────────────────
    if args.stage:
        stages_to_run = [args.stage]
    else:
        stages_to_run = STAGES  # full pipeline

    # ── Safety check ─────────────────────────────────────────────────────────
    if args.all and not args.force and not args.stage:
        print(
            "\nWARNING: You are about to run the full pipeline on ALL papers.\n"
            "   This may take several minutes.\n"
            "   Add --force to also reprocess already-completed papers.\n"
            "   Proceeding in 3 seconds... (Ctrl+C to cancel)\n"
        )
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            print("Aborted.")
            return

    # ── Run ───────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Paper Corpus Pipeline")
    print(f"  Scope : {scope_label}")
    print(f"  Stages: {', '.join(stages_to_run)}")
    print(f"  Force : {args.force}")
    print(f"{'='*60}")

    t_total = time.time()
    for stage in stages_to_run:
        _run_stage(stage, force=args.force, paper_ids=paper_ids)

    elapsed_total = time.time() - t_total
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed_total:.1f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

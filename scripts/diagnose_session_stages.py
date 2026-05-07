#!/usr/bin/env python3
"""
Per-stage diagnostic for Gonghaebun session creation pipeline.

Runs the 8-stage pipeline one stage at a time and reports per-stage timing.
Helps isolate which stage is slow or failing during real LLM session creation.

Usage:
    python scripts/diagnose_session_stages.py --dry-run
    python scripts/diagnose_session_stages.py --allow-real-llm
    python scripts/diagnose_session_stages.py --allow-real-llm --stage 3
    python scripts/diagnose_session_stages.py --allow-real-llm --timeout-override 60

Requires:
    - --allow-real-llm flag for live LLM calls (refuses without it)
    - For live mode: GONGHAEBUN_LLM_DISABLED=0, GONGHAEBUN_LLM_PROVIDER=openai,
      OPENAI_API_KEY set
    - Source file in GONGHAEBUN_SOURCES_DIR (or use --source)

SECURITY:
    - Never prints API keys, prompt bodies, or response bodies
    - On failure: prints stage name, exception class, and safe message only
    - NOT for CI/pytest — manual diagnostic script only
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

STAGES = [
    (0, "source_loader", 0),
    (1, "concept_resolver", 0),
    (2, "graph_builder", 0),
    (3, "representation_gen", 5),
    (5, "self_explanation_tmpl", 0),
    (4, "misconception_checker", 1),
    (6, "recall_orchestrator", 1),
    (7, "study_writer", 0),
]


def _resolve_source(source_arg: str | None) -> Path:
    """Find a source file to use."""
    if source_arg:
        p = Path(source_arg)
        if not p.exists():
            print(f"ERROR: Source file not found: {p}")
            sys.exit(1)
        return p

    sources_dir = Path(
        os.getenv("GONGHAEBUN_SOURCES_DIR", "data/gonghaebun/default/sources")
    )
    if sources_dir.is_dir():
        for ext in (".md", ".txt"):
            for f in sorted(sources_dir.iterdir()):
                if f.suffix == ext:
                    return f

    print(f"ERROR: No source file found in {sources_dir}")
    print("  Use --source PATH to specify one explicitly.")
    sys.exit(1)


def _get_llm(use_real: bool, timeout_override: float | None):
    """Return LLM client."""
    if not use_real:
        from gonghaebun.llm.mock import MockLLMClient

        return MockLLMClient()

    if timeout_override is not None:
        os.environ["GONGHAEBUN_LLM_TIMEOUT_SECONDS"] = str(timeout_override)

    from gonghaebun.llm.factory import get_llm_client

    return get_llm_client()


def run_full_session(concept_id: str, source_path: Path, llm, output_dir: Path, study_md: Path):
    """Run full pipeline via session.py and let stage-level logs show timing."""
    from gonghaebun.session import run_new_concept_session

    run_new_concept_session(
        concept_input=concept_id,
        source_path=source_path,
        llm=llm,
        output_dir=output_dir,
        study_md_path=study_md,
    )


def run_single_stage(stage_num: int, concept_id: str, source_path: Path, llm, output_dir: Path, study_md: Path):
    """Run a single pipeline stage in isolation."""
    from gonghaebun.knowledge.real_analysis import CONCEPT_KEYWORDS
    from gonghaebun.pipeline.concept_resolver import resolve_concept
    from gonghaebun.pipeline.source_loader import load_and_extract

    # Stages 0-2 are prerequisites for later stages, always run them
    concept = resolve_concept(concept_id)
    cid = concept.concept_id
    keywords = CONCEPT_KEYWORDS.get(cid, [])
    manifest = load_and_extract(
        source_path=source_path,
        concept_id=cid,
        keywords=keywords,
        output_dir=output_dir,
    )
    source_excerpt = (output_dir / "source_excerpt.md").read_text(encoding="utf-8")

    if stage_num <= 2:
        print(f"  Stages 0-2 are non-LLM setup stages. Already completed above.")
        return

    if stage_num == 3:
        from gonghaebun.pipeline.representation_gen import generate_representations

        rep_set = generate_representations(
            concept_id=cid,
            source_excerpt=source_excerpt,
            source_hash=manifest.source_hash,
            llm=llm,
        )
        print(f"  Generated {len(rep_set.as_list())} representations.")
        return

    # For stages 4 and 6, we need representations first
    from gonghaebun.pipeline.representation_gen import generate_representations

    rep_set = generate_representations(
        concept_id=cid,
        source_excerpt=source_excerpt,
        source_hash=manifest.source_hash,
        llm=llm,
    )

    if stage_num == 4:
        from gonghaebun.pipeline.misconception_checker import check_misconceptions

        diagnosis = check_misconceptions(
            concept_id=cid,
            rep_set=rep_set,
            source_coverage=manifest.source_coverage,
            llm=llm,
        )
        mc_count = len(diagnosis.get("misconceptions", []))
        print(f"  Found {mc_count} misconceptions.")
        return

    if stage_num == 6:
        from gonghaebun.pipeline.recall_orchestrator import generate_recall_tasks

        tasks = generate_recall_tasks(
            concept_id=cid,
            mastery_state="unknown",
            llm=llm,
        )
        task_count = len(tasks.get("tasks", []))
        print(f"  Generated {task_count} recall tasks.")
        return

    print(f"  Stage {stage_num} is not independently runnable.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-stage diagnostic for session creation pipeline."
    )
    parser.add_argument(
        "--allow-real-llm",
        action="store_true",
        help="Enable real LLM API calls (mandatory for live mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Use MockLLMClient only (default if --allow-real-llm not given).",
    )
    parser.add_argument(
        "--stage",
        type=int,
        default=None,
        help="Run only this stage number (0-7). Default: run all.",
    )
    parser.add_argument(
        "--timeout-override",
        type=float,
        default=None,
        help="Override per-call LLM timeout in seconds.",
    )
    parser.add_argument(
        "--concept",
        default="compactness",
        help="Concept ID to use (default: compactness).",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Path to source file. Auto-discovers from SOURCES_DIR if omitted.",
    )
    args = parser.parse_args()

    use_real = args.allow_real_llm and not args.dry_run
    if not args.allow_real_llm and not args.dry_run:
        # Default to dry-run when neither flag is given
        args.dry_run = True

    # Configure logging to see instrumented output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    print("=" * 70)
    print("Gonghaebun Session Creation - Stage Diagnostic")
    print("=" * 70)
    print(f"  Mode:    {'REAL LLM' if use_real else 'DRY-RUN (MockLLMClient)'}")
    print(f"  Concept: {args.concept}")

    if args.stage is not None:
        print(f"  Stage:   {args.stage} only")
    else:
        print(f"  Stage:   all")

    if args.timeout_override:
        print(f"  Timeout: {args.timeout_override}s (override)")

    print()

    # Resolve source
    source_path = _resolve_source(args.source)
    print(f"  Source:  {source_path}")

    # Get LLM client
    llm = _get_llm(use_real, args.timeout_override)
    print(f"  LLM:    {llm.__class__.__name__}")
    print()

    # Create temp output dir
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gonghaebun_diag_") as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        study_md = Path(tmpdir) / "STUDY.md"
        study_md.write_text("", encoding="utf-8")

        total_t0 = time.monotonic()

        if args.stage is not None:
            # Single stage mode
            print(f"Running stage {args.stage}...")
            t0 = time.monotonic()
            try:
                run_single_stage(
                    args.stage, args.concept, source_path, llm, output_dir, study_md,
                )
                elapsed = (time.monotonic() - t0) * 1000
                print(f"  Status: OK ({elapsed:.0f}ms)")
            except Exception as exc:
                elapsed = (time.monotonic() - t0) * 1000
                print(f"  Status: FAIL ({elapsed:.0f}ms) {type(exc).__name__}")
                return 1
        else:
            # Full pipeline mode
            print("Running full pipeline...")
            t0 = time.monotonic()
            try:
                run_full_session(args.concept, source_path, llm, output_dir, study_md)
                elapsed = (time.monotonic() - t0) * 1000
                print(f"\n  Full pipeline: OK ({elapsed:.0f}ms)")
            except Exception as exc:
                elapsed = (time.monotonic() - t0) * 1000
                print(f"\n  Full pipeline: FAIL ({elapsed:.0f}ms) {type(exc).__name__}")
                return 1

        total_elapsed = (time.monotonic() - total_t0) * 1000
        print(f"\n  Total wall time: {total_elapsed:.0f}ms")

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

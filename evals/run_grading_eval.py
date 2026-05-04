#!/usr/bin/env python
"""
Gonghaebun MVP3.5 Engine Quality Gate — CLI runner.

Usage:
    python evals/run_grading_eval.py [--grader mock|llm] [--model MODEL]
                                     [--golden evals/golden_set]
                                     [--report evals/grading_eval_report.md]
                                     [--out-dir evals/runs]

Modes:
    --grader mock  : fully offline; no API key required (default)
    --grader llm   : real OpenAI API; requires OPENAI_API_KEY in env or .env

Exit codes:
    0 — all expected checks pass
    1 — unexpected schema parse failure, wrong_to_solid violation, or
        expected schema failure NOT handled (gc007 passed when it should fail)
    2 — setup error (missing API key for llm mode, etc.)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a script without installing the evals package
sys.path.insert(0, str(Path(__file__).parent))

from eval_utils import (  # noqa: E402
    LLMAPIKeyError,
    build_report,
    compute_metrics,
    make_llm_client,
    parse_eval_args,
    run_all_evals,
)


def main(argv: list[str] | None = None) -> int:
    args = parse_eval_args(argv)

    golden_dir = Path(args.golden)
    report_path = Path(args.report)
    out_dir = Path(args.out_dir)

    # --- guard: LLM mode requires API key ---
    if args.grader == "llm":
        try:
            make_llm_client(args.model)
        except LLMAPIKeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            print(
                "Set OPENAI_API_KEY in your environment or in a .env file.\n"
                "See .env.example for the expected format.",
                file=sys.stderr,
            )
            return 2

    print(f"=== Gonghaebun Engine Quality Gate (MVP3.5) ===")
    print(f"Grader : {args.grader}")
    print(f"Model  : {args.model if args.grader == 'llm' else 'n/a'}")
    print(f"Golden : {golden_dir}")
    print()

    # --- run evals ---
    results, skipped = run_all_evals(
        golden_dir=golden_dir,
        grader=args.grader,
        model=args.model,
    )

    metrics = compute_metrics(results)

    # --- write per-case outputs for LLM mode ---
    if args.grader == "llm" and results:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_out_dir = out_dir / timestamp
        run_out_dir.mkdir(parents=True, exist_ok=True)
        per_case = []
        for r in results:
            entry = {
                "case_id": r.case_id,
                "dimension": r.dimension,
                "passed": r.passed,
                "score": r.score,
                "message": r.message,
            }
            if r.grading is not None:
                entry["grading"] = {
                    "accuracy_score": r.grading.accuracy_score,
                    "mastery_suggestion": r.grading.mastery_suggestion,
                    "confidence": r.grading.confidence,
                    "needs_human_review": r.grading.needs_human_review,
                    "missing_elements": r.grading.missing_elements,
                    "errors": r.grading.errors,
                    "feedback": r.grading.feedback,
                }
            per_case.append(entry)
        (run_out_dir / "results.json").write_text(
            json.dumps(per_case, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"LLM run outputs: {run_out_dir}")

    # --- build and write report ---
    report_text = build_report(results, metrics, args.grader, args.model, skipped)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Report written: {report_path}")
    print()

    # --- print summary ---
    total = len(results)
    passed = sum(r.passed for r in results)
    print(f"Results: {passed}/{total} passed")
    if skipped:
        print(f"Skipped: {skipped}")
    print()

    # --- determine exit code ---
    schema_parse_rate = metrics.get("schema_parse_success_rate")
    expected_handled = metrics.get("expected_schema_failure_handled")
    wrong_to_solid = metrics.get("wrong_to_solid_count", 0)

    critical = False
    if schema_parse_rate is not None and schema_parse_rate < 1.0:
        print("FAIL: unexpected schema parse failure(s)", file=sys.stderr)
        critical = True
    if args.grader == "mock" and expected_handled is False:
        print("FAIL: gc007 expected schema failure was NOT handled correctly", file=sys.stderr)
        critical = True
    if wrong_to_solid > 0:
        print(f"FAIL: {wrong_to_solid} wrong answer(s) graded as solid", file=sys.stderr)
        critical = True

    if critical:
        return 1

    print("All quality checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

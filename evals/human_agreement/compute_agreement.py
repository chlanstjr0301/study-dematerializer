#!/usr/bin/env python
"""
Compute inter-rater agreement and evaluator-human agreement.

Usage:
  python evals/human_agreement/compute_agreement.py
  python evals/human_agreement/compute_agreement.py --include-evaluator

Output: evals/human_agreement/agreement_report.md
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent

MASTERY_LABELS = ["unknown", "partial", "solid"]


def load_answers(path: Path | None = None) -> list[dict]:
    """Load learner answer dataset CSV."""
    path = path or (_HERE / "compactness_answers.csv")
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_rater(path: Path) -> list[dict]:
    """Load a rater CSV file."""
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_misconceptions(raw: str) -> set[str]:
    """Parse comma-separated misconception IDs into a set."""
    if not raw or not raw.strip():
        return set()
    return {m.strip() for m in raw.split(",") if m.strip()}


# ---------------------------------------------------------------------------
# Agreement metrics
# ---------------------------------------------------------------------------


def compute_agreement_rate(rater_a: list[str], rater_b: list[str]) -> float:
    """Simple agreement: fraction of matching mastery labels."""
    if not rater_a:
        return 0.0
    matches = sum(a == b for a, b in zip(rater_a, rater_b))
    return matches / len(rater_a)


def compute_cohens_kappa(rater_a: list[str], rater_b: list[str]) -> float:
    """Cohen's kappa for 3-class mastery labels.

    Handles the standard Cohen's kappa formula:
    kappa = (p_o - p_e) / (1 - p_e)
    where p_o is observed agreement and p_e is expected agreement by chance.
    """
    if not rater_a:
        return 0.0

    n = len(rater_a)
    labels = MASTERY_LABELS

    # Build confusion matrix counts
    a_counts = {label: 0 for label in labels}
    b_counts = {label: 0 for label in labels}
    for a, b in zip(rater_a, rater_b):
        a_counts[a] = a_counts.get(a, 0) + 1
        b_counts[b] = b_counts.get(b, 0) + 1

    # Observed agreement
    p_o = compute_agreement_rate(rater_a, rater_b)

    # Expected agreement by chance
    p_e = sum(
        (a_counts.get(label, 0) / n) * (b_counts.get(label, 0) / n)
        for label in labels
    )

    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0

    return (p_o - p_e) / (1.0 - p_e)


def compute_consensus(
    rater_a_mastery: list[str],
    rater_b_mastery: list[str],
) -> list[str]:
    """Compute consensus: if raters agree, use that; otherwise use the more
    conservative (lower) mastery level.

    Ordering: unknown < partial < solid
    """
    order = {"unknown": 0, "partial": 1, "solid": 2}
    consensus = []
    for a, b in zip(rater_a_mastery, rater_b_mastery):
        if a == b:
            consensus.append(a)
        else:
            # Use more conservative (lower) mastery
            consensus.append(a if order.get(a, 0) < order.get(b, 0) else b)
    return consensus


def compute_evaluator_agreement(
    evaluator_results: list[str],
    human_consensus: list[str],
) -> float:
    """Agreement between evaluator and human consensus."""
    if not evaluator_results:
        return 0.0
    matches = sum(e == h for e, h in zip(evaluator_results, human_consensus))
    return matches / len(evaluator_results)


def compute_fallback_ratio(evaluator_results: list[dict]) -> float:
    """Fraction of answers where evaluator returned needs_human_review=True."""
    if not evaluator_results:
        return 0.0
    reviews = sum(1 for r in evaluator_results if r.get("needs_human_review"))
    return reviews / len(evaluator_results)


def compute_misconception_agreement(
    rater_a_misconceptions: list[set[str]],
    rater_b_misconceptions: list[set[str]],
) -> float:
    """Jaccard similarity of misconception tag sets, averaged over all answers."""
    if not rater_a_misconceptions:
        return 0.0
    similarities = []
    for a_set, b_set in zip(rater_a_misconceptions, rater_b_misconceptions):
        if not a_set and not b_set:
            similarities.append(1.0)
        elif not a_set or not b_set:
            similarities.append(0.0)
        else:
            similarities.append(len(a_set & b_set) / len(a_set | b_set))
    return sum(similarities) / len(similarities)


def build_confusion_matrix(
    rater_a: list[str],
    rater_b: list[str],
) -> dict[str, dict[str, int]]:
    """Build a confusion matrix: matrix[a_label][b_label] = count."""
    labels = MASTERY_LABELS
    matrix: dict[str, dict[str, int]] = {
        a: {b: 0 for b in labels} for a in labels
    }
    for a, b in zip(rater_a, rater_b):
        if a in matrix and b in matrix[a]:
            matrix[a][b] += 1
    return matrix


# ---------------------------------------------------------------------------
# Disagreement analysis
# ---------------------------------------------------------------------------


def find_disagreements(
    answer_ids: list[str],
    rater_a_mastery: list[str],
    rater_b_mastery: list[str],
    rater_a_notes: list[str],
    rater_b_notes: list[str],
) -> list[dict]:
    """Find cases where raters disagree on mastery level."""
    disagreements = []
    for i, aid in enumerate(answer_ids):
        a_m = rater_a_mastery[i]
        b_m = rater_b_mastery[i]
        if a_m != b_m:
            disagreements.append({
                "answer_id": aid,
                "rater_a": a_m,
                "rater_b": b_m,
                "notes_a": rater_a_notes[i] if i < len(rater_a_notes) else "",
                "notes_b": rater_b_notes[i] if i < len(rater_b_notes) else "",
            })
    return disagreements


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

_TARGETS = {
    "agreement_rate": (">=", 0.75),
    "cohens_kappa": (">=", 0.60),
    "misconception_agreement": (">=", 0.60),
    "evaluator_human_agreement": (">=", 0.70),
    "fallback_ratio": ("<=", 0.30),
}


def _pass_fail(metric_name: str, value: float) -> str:
    """Check if a metric meets its target."""
    if metric_name not in _TARGETS:
        return "N/A"
    op, target = _TARGETS[metric_name]
    if op == ">=" and value >= target:
        return "PASS"
    if op == "<=" and value <= target:
        return "PASS"
    return "FAIL"


def generate_report(
    *,
    answer_count: int,
    agreement_rate: float,
    cohens_kappa: float,
    misconception_agreement: float,
    confusion_matrix: dict[str, dict[str, int]],
    disagreements: list[dict],
    evaluator_human_agreement: float | None = None,
    fallback_ratio: float | None = None,
) -> str:
    """Generate markdown agreement report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "# Human Agreement Report",
        "",
        f"Generated: {timestamp}",
        f"Dataset: compactness_answers.csv (N={answer_count})",
        "Rubric: rubric_v1.json",
        "",
        "## Inter-Rater Agreement",
        "",
        "| Metric | Value | Target | Status |",
        "|--------|-------|--------|--------|",
        f"| Agreement rate | {agreement_rate:.3f} | >= 0.75 | {_pass_fail('agreement_rate', agreement_rate)} |",
        f"| Cohen's kappa | {cohens_kappa:.3f} | >= 0.60 | {_pass_fail('cohens_kappa', cohens_kappa)} |",
        f"| Misconception agreement | {misconception_agreement:.3f} | >= 0.60 | {_pass_fail('misconception_agreement', misconception_agreement)} |",
        "",
        "## Confusion Matrix (Rater A vs Rater B)",
        "",
        "|          | B:unknown | B:partial | B:solid |",
        "|----------|-----------|-----------|---------|",
    ]

    for a_label in MASTERY_LABELS:
        row = confusion_matrix.get(a_label, {})
        vals = [str(row.get(b, 0)) for b in MASTERY_LABELS]
        lines.append(f"| A:{a_label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    lines.append("")

    if evaluator_human_agreement is not None:
        lines.extend([
            "## Evaluator-Human Agreement",
            "",
            "| Metric | Value | Target | Status |",
            "|--------|-------|--------|--------|",
            f"| Evaluator-human agreement | {evaluator_human_agreement:.3f} | >= 0.70 | {_pass_fail('evaluator_human_agreement', evaluator_human_agreement)} |",
        ])
        if fallback_ratio is not None:
            lines.append(
                f"| Fallback ratio | {fallback_ratio:.3f} | <= 0.30 | {_pass_fail('fallback_ratio', fallback_ratio)} |"
            )
        lines.append("")

    lines.extend([
        "## Disagreement Analysis",
        "",
        "### Cases where raters disagree:",
        "",
    ])

    if disagreements:
        for d in disagreements:
            notes = ""
            if d.get("notes_a"):
                notes += f" A: {d['notes_a']}"
            if d.get("notes_b"):
                notes += f" B: {d['notes_b']}"
            lines.append(
                f"- {d['answer_id']}: Rater A={d['rater_a']}, Rater B={d['rater_b']}.{notes}"
            )
    else:
        lines.append("_(none)_")

    lines.extend([
        "",
        "## Recommendations",
        "",
    ])

    all_pass = (
        _pass_fail("agreement_rate", agreement_rate) == "PASS"
        and _pass_fail("cohens_kappa", cohens_kappa) == "PASS"
    )
    if all_pass:
        lines.append("- Targets met. Proceed to LLM evaluation gating (MVP7).")
    else:
        lines.append("- Revise rubric / expand aliases / adjust thresholds.")
        if _pass_fail("cohens_kappa", cohens_kappa) == "FAIL":
            lines.append("- Cohen's kappa below target: clarify mastery level boundaries in rubric.")
        if _pass_fail("agreement_rate", agreement_rate) == "FAIL":
            lines.append("- Agreement rate below target: review disagreement cases for ambiguity.")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="compute_agreement",
        description="Compute inter-rater and evaluator-human agreement.",
    )
    parser.add_argument(
        "--answers",
        default=str(_HERE / "compactness_answers.csv"),
        help="Path to learner answers CSV.",
    )
    parser.add_argument(
        "--rater-a",
        default=str(_HERE / "rater_a.csv"),
        dest="rater_a",
        help="Path to rater A CSV.",
    )
    parser.add_argument(
        "--rater-b",
        default=str(_HERE / "rater_b.csv"),
        dest="rater_b",
        help="Path to rater B CSV.",
    )
    parser.add_argument(
        "--report",
        default=str(_HERE / "agreement_report.md"),
        help="Output report path.",
    )
    parser.add_argument(
        "--include-evaluator",
        action="store_true",
        dest="include_evaluator",
        help="Include evaluator-human agreement (requires deterministic evaluator).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    answers = load_answers(Path(args.answers))
    rater_a_rows = load_rater(Path(args.rater_a))
    rater_b_rows = load_rater(Path(args.rater_b))

    answer_ids = [a["answer_id"] for a in answers]
    a_mastery = [r["mastery"] for r in rater_a_rows]
    b_mastery = [r["mastery"] for r in rater_b_rows]
    a_misconceptions = [parse_misconceptions(r.get("misconceptions", "")) for r in rater_a_rows]
    b_misconceptions = [parse_misconceptions(r.get("misconceptions", "")) for r in rater_b_rows]
    a_notes = [r.get("notes", "") for r in rater_a_rows]
    b_notes = [r.get("notes", "") for r in rater_b_rows]

    agreement_rate = compute_agreement_rate(a_mastery, b_mastery)
    kappa = compute_cohens_kappa(a_mastery, b_mastery)
    mc_agreement = compute_misconception_agreement(a_misconceptions, b_misconceptions)
    matrix = build_confusion_matrix(a_mastery, b_mastery)
    disagreements = find_disagreements(answer_ids, a_mastery, b_mastery, a_notes, b_notes)

    print(f"=== Human Agreement Evaluation ===")
    print(f"Answers : {len(answers)}")
    print(f"Rater A : {len(rater_a_rows)} ratings")
    print(f"Rater B : {len(rater_b_rows)} ratings")
    print()
    print(f"Agreement rate      : {agreement_rate:.3f}")
    print(f"Cohen's kappa       : {kappa:.3f}")
    print(f"Misconception agree : {mc_agreement:.3f}")
    print(f"Disagreements       : {len(disagreements)}")
    print()

    report = generate_report(
        answer_count=len(answers),
        agreement_rate=agreement_rate,
        cohens_kappa=kappa,
        misconception_agreement=mc_agreement,
        confusion_matrix=matrix,
        disagreements=disagreements,
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

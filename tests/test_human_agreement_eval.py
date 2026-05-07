"""
Tests for human agreement evaluation harness (Step 18).

Tests cover:
- Agreement rate computation
- Cohen's kappa computation
- Consensus computation
- Misconception agreement (Jaccard)
- Fallback ratio
- Report generation
- CSV loading and end-to-end run
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# Allow importing from evals/ directory
sys.path.insert(0, str(Path(__file__).parent.parent / "evals" / "human_agreement"))

from compute_agreement import (  # noqa: E402
    build_confusion_matrix,
    compute_agreement_rate,
    compute_cohens_kappa,
    compute_consensus,
    compute_evaluator_agreement,
    compute_fallback_ratio,
    compute_misconception_agreement,
    find_disagreements,
    generate_report,
    load_answers,
    load_rater,
    parse_misconceptions,
)


# ---------------------------------------------------------------------------
# Agreement rate
# ---------------------------------------------------------------------------


class TestAgreementRate:
    def test_perfect_agreement(self):
        a = ["solid", "partial", "unknown"]
        b = ["solid", "partial", "unknown"]
        assert compute_agreement_rate(a, b) == 1.0

    def test_no_agreement(self):
        a = ["solid", "solid", "solid"]
        b = ["unknown", "unknown", "unknown"]
        assert compute_agreement_rate(a, b) == 0.0

    def test_partial_agreement(self):
        a = ["solid", "partial", "unknown", "solid"]
        b = ["solid", "partial", "partial", "unknown"]
        assert compute_agreement_rate(a, b) == 0.5

    def test_empty_returns_zero(self):
        assert compute_agreement_rate([], []) == 0.0


# ---------------------------------------------------------------------------
# Cohen's kappa
# ---------------------------------------------------------------------------


class TestCohensKappa:
    def test_perfect_agreement_gives_kappa_one(self):
        a = ["solid", "partial", "unknown", "solid", "partial", "unknown"]
        b = ["solid", "partial", "unknown", "solid", "partial", "unknown"]
        assert compute_cohens_kappa(a, b) == pytest.approx(1.0)

    def test_random_agreement_gives_low_kappa(self):
        # All same label → kappa is 0 (or undefined, we return 1.0 for p_e=1)
        a = ["solid", "solid", "solid"]
        b = ["solid", "solid", "solid"]
        # Both raters always say solid → p_o = 1.0, p_e = 1.0 → kappa = 1.0
        assert compute_cohens_kappa(a, b) == pytest.approx(1.0)

    def test_moderate_agreement(self):
        a = ["solid", "partial", "unknown", "solid", "partial"]
        b = ["solid", "partial", "partial", "solid", "unknown"]
        kappa = compute_cohens_kappa(a, b)
        # 3/5 agreement = 0.6 observed, expected by chance is lower
        assert 0.0 < kappa < 1.0

    def test_empty_returns_zero(self):
        assert compute_cohens_kappa([], []) == 0.0

    def test_no_agreement_negative_or_zero_kappa(self):
        # Systematic disagreement should give kappa <= 0
        a = ["solid", "solid", "solid", "solid"]
        b = ["unknown", "unknown", "unknown", "unknown"]
        kappa = compute_cohens_kappa(a, b)
        assert kappa <= 0.0


# ---------------------------------------------------------------------------
# Consensus
# ---------------------------------------------------------------------------


class TestConsensus:
    def test_agreement_uses_agreed_label(self):
        assert compute_consensus(["solid"], ["solid"]) == ["solid"]
        assert compute_consensus(["unknown"], ["unknown"]) == ["unknown"]

    def test_disagreement_uses_conservative(self):
        # solid vs partial → partial (more conservative)
        assert compute_consensus(["solid"], ["partial"]) == ["partial"]
        # partial vs unknown → unknown
        assert compute_consensus(["partial"], ["unknown"]) == ["unknown"]
        # solid vs unknown → unknown
        assert compute_consensus(["solid"], ["unknown"]) == ["unknown"]

    def test_mixed_sequence(self):
        a = ["solid", "partial", "unknown"]
        b = ["partial", "partial", "solid"]
        result = compute_consensus(a, b)
        assert result == ["partial", "partial", "unknown"]


# ---------------------------------------------------------------------------
# Misconception agreement (Jaccard)
# ---------------------------------------------------------------------------


class TestMisconceptionAgreement:
    def test_both_empty_is_perfect(self):
        a = [set(), set()]
        b = [set(), set()]
        assert compute_misconception_agreement(a, b) == 1.0

    def test_identical_sets(self):
        a = [{"bounded_implies_compact", "misuses_heine_borel"}]
        b = [{"bounded_implies_compact", "misuses_heine_borel"}]
        assert compute_misconception_agreement(a, b) == 1.0

    def test_disjoint_sets(self):
        a = [{"bounded_implies_compact"}]
        b = [{"closed_implies_compact"}]
        assert compute_misconception_agreement(a, b) == 0.0

    def test_partial_overlap(self):
        a = [{"bounded_implies_compact", "misuses_heine_borel"}]
        b = [{"bounded_implies_compact", "closed_implies_compact"}]
        # Intersection = 1, union = 3, Jaccard = 1/3
        assert compute_misconception_agreement(a, b) == pytest.approx(1 / 3)

    def test_one_empty_one_nonempty(self):
        a = [set()]
        b = [{"bounded_implies_compact"}]
        assert compute_misconception_agreement(a, b) == 0.0

    def test_empty_list_returns_zero(self):
        assert compute_misconception_agreement([], []) == 0.0


# ---------------------------------------------------------------------------
# Fallback ratio
# ---------------------------------------------------------------------------


class TestFallbackRatio:
    def test_no_reviews(self):
        results = [
            {"needs_human_review": False},
            {"needs_human_review": False},
        ]
        assert compute_fallback_ratio(results) == 0.0

    def test_all_reviews(self):
        results = [
            {"needs_human_review": True},
            {"needs_human_review": True},
        ]
        assert compute_fallback_ratio(results) == 1.0

    def test_mixed(self):
        results = [
            {"needs_human_review": True},
            {"needs_human_review": False},
            {"needs_human_review": False},
            {"needs_human_review": True},
        ]
        assert compute_fallback_ratio(results) == 0.5

    def test_empty(self):
        assert compute_fallback_ratio([]) == 0.0


# ---------------------------------------------------------------------------
# Evaluator agreement
# ---------------------------------------------------------------------------


class TestEvaluatorAgreement:
    def test_perfect(self):
        assert compute_evaluator_agreement(
            ["solid", "partial"], ["solid", "partial"]
        ) == 1.0

    def test_none(self):
        assert compute_evaluator_agreement(
            ["solid", "solid"], ["unknown", "unknown"]
        ) == 0.0

    def test_empty(self):
        assert compute_evaluator_agreement([], []) == 0.0


# ---------------------------------------------------------------------------
# Parse misconceptions
# ---------------------------------------------------------------------------


class TestParseMisconceptions:
    def test_empty_string(self):
        assert parse_misconceptions("") == set()

    def test_single(self):
        assert parse_misconceptions("bounded_implies_compact") == {"bounded_implies_compact"}

    def test_multiple(self):
        result = parse_misconceptions("bounded_implies_compact,misuses_heine_borel")
        assert result == {"bounded_implies_compact", "misuses_heine_borel"}

    def test_whitespace_handling(self):
        result = parse_misconceptions(" bounded_implies_compact , misuses_heine_borel ")
        assert result == {"bounded_implies_compact", "misuses_heine_borel"}


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------


class TestConfusionMatrix:
    def test_basic_matrix(self):
        a = ["solid", "partial", "unknown"]
        b = ["solid", "partial", "unknown"]
        matrix = build_confusion_matrix(a, b)
        assert matrix["solid"]["solid"] == 1
        assert matrix["partial"]["partial"] == 1
        assert matrix["unknown"]["unknown"] == 1
        assert matrix["solid"]["partial"] == 0

    def test_disagreement_in_matrix(self):
        a = ["solid", "solid"]
        b = ["partial", "solid"]
        matrix = build_confusion_matrix(a, b)
        assert matrix["solid"]["partial"] == 1
        assert matrix["solid"]["solid"] == 1


# ---------------------------------------------------------------------------
# Disagreements
# ---------------------------------------------------------------------------


class TestDisagreements:
    def test_finds_disagreements(self):
        ids = ["ca001", "ca002", "ca003"]
        a = ["solid", "partial", "unknown"]
        b = ["solid", "unknown", "unknown"]
        d = find_disagreements(ids, a, b, ["", "", ""], ["", "", ""])
        assert len(d) == 1
        assert d[0]["answer_id"] == "ca002"
        assert d[0]["rater_a"] == "partial"
        assert d[0]["rater_b"] == "unknown"

    def test_no_disagreements(self):
        ids = ["ca001"]
        a = ["solid"]
        b = ["solid"]
        d = find_disagreements(ids, a, b, [""], [""])
        assert len(d) == 0


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    def test_report_is_markdown(self):
        report = generate_report(
            answer_count=10,
            agreement_rate=0.80,
            cohens_kappa=0.65,
            misconception_agreement=0.70,
            confusion_matrix=build_confusion_matrix(
                ["solid", "partial", "unknown"],
                ["solid", "partial", "unknown"],
            ),
            disagreements=[],
        )
        assert report.startswith("# Human Agreement Report")
        assert "Agreement rate" in report
        assert "Cohen's kappa" in report
        assert "PASS" in report

    def test_report_with_evaluator(self):
        report = generate_report(
            answer_count=10,
            agreement_rate=0.80,
            cohens_kappa=0.65,
            misconception_agreement=0.70,
            confusion_matrix=build_confusion_matrix(
                ["solid", "partial", "unknown"],
                ["solid", "partial", "unknown"],
            ),
            disagreements=[],
            evaluator_human_agreement=0.75,
            fallback_ratio=0.20,
        )
        assert "Evaluator-Human Agreement" in report
        assert "Fallback ratio" in report

    def test_report_failing_metrics(self):
        report = generate_report(
            answer_count=10,
            agreement_rate=0.50,
            cohens_kappa=0.30,
            misconception_agreement=0.40,
            confusion_matrix=build_confusion_matrix(
                ["solid", "partial", "unknown"],
                ["unknown", "solid", "partial"],
            ),
            disagreements=[
                {"answer_id": "ca001", "rater_a": "solid", "rater_b": "unknown",
                 "notes_a": "Clear", "notes_b": "Vague"},
            ],
        )
        assert "FAIL" in report
        assert "ca001" in report
        assert "Revise rubric" in report


# ---------------------------------------------------------------------------
# CSV loading (integration with actual data files)
# ---------------------------------------------------------------------------


class TestCSVLoading:
    def test_load_answers_from_default(self):
        answers_path = Path(__file__).parent.parent / "evals" / "human_agreement" / "compactness_answers.csv"
        if not answers_path.exists():
            pytest.skip("compactness_answers.csv not found")
        answers = load_answers(answers_path)
        assert len(answers) >= 20
        assert all("answer_id" in a for a in answers)
        assert all("task_type" in a for a in answers)
        assert all("expected_mastery" in a for a in answers)

    def test_load_rater_a(self):
        rater_path = Path(__file__).parent.parent / "evals" / "human_agreement" / "rater_a.csv"
        if not rater_path.exists():
            pytest.skip("rater_a.csv not found")
        rows = load_rater(rater_path)
        assert len(rows) >= 20
        assert all(r["mastery"] in ("solid", "partial", "unknown") for r in rows)

    def test_load_rubric(self):
        rubric_path = Path(__file__).parent.parent / "evals" / "human_agreement" / "rubric_v1.json"
        if not rubric_path.exists():
            pytest.skip("rubric_v1.json not found")
        rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
        assert rubric["version"] == "1.0"
        assert "mastery_levels" in rubric
        assert len(rubric["misconception_checklist"]) >= 5


# ---------------------------------------------------------------------------
# End-to-end: compute_agreement.py runs with sample data
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_main_runs_with_sample_data(self, tmp_path):
        """compute_agreement.py main() runs and produces a report."""
        evals_dir = Path(__file__).parent.parent / "evals" / "human_agreement"
        answers_path = evals_dir / "compactness_answers.csv"
        rater_a_path = evals_dir / "rater_a.csv"
        rater_b_path = evals_dir / "rater_b.csv"

        if not all(p.exists() for p in [answers_path, rater_a_path, rater_b_path]):
            pytest.skip("Sample data files not found")

        from compute_agreement import main

        report_path = tmp_path / "agreement_report.md"
        exit_code = main([
            "--answers", str(answers_path),
            "--rater-a", str(rater_a_path),
            "--rater-b", str(rater_b_path),
            "--report", str(report_path),
        ])

        assert exit_code == 0
        assert report_path.exists()
        report_text = report_path.read_text(encoding="utf-8")
        assert "# Human Agreement Report" in report_text
        assert "Agreement rate" in report_text
        assert "Cohen's kappa" in report_text
        assert "Confusion Matrix" in report_text

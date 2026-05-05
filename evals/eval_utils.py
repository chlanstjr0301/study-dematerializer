"""
MVP3.5 Engine Quality Gate — evaluation utilities.

Importable by both run_grading_eval.py (CLI runner) and tests/test_grading_eval.py.

No real LLM calls unless make_llm_client() is used with a valid OPENAI_API_KEY.
All mock-mode evaluation is fully offline.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Re-exports from gonghaebun package
# ---------------------------------------------------------------------------
from gonghaebun.grading.llm_grader import LLMGrader
from gonghaebun.grading.schemas import GradingResult
from gonghaebun.llm.base import LLMClient
from gonghaebun.llm.errors import LLMAPIKeyError, LLMResponseError
from gonghaebun.study_loop.mastery import AttemptResult
from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
from gonghaebun.study_md.writer import validate_study_md

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOLDEN_SET_DIR = Path(__file__).parent / "golden_set"
REPORT_PATH = Path(__file__).parent / "grading_eval_report.md"
RUNS_DIR = Path(__file__).parent / "runs"

# gc007 is an expected-failure case: never counted in schema_parse_success_rate
EXPECTED_FAILURE_ID = "gc007"

# gc007 is skipped in LLM mode (it requires injected malformed JSON)
LLM_MODE_SKIP_IDS = {EXPECTED_FAILURE_ID}

# ---------------------------------------------------------------------------
# _FixtureLLMClient — offline LLM stub
# ---------------------------------------------------------------------------


class _FixtureLLMClient(LLMClient):
    """Returns a fixed string as the LLM response. Enables per-entry offline eval."""

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, system: str, user: str) -> str:
        return self._response

    def complete_json(self, system: str, user: str) -> dict:
        return json.loads(self._response)

    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict:
        """Delegates to complete_json(); json_schema is ignored in fixture mode."""
        return self.complete_json(system, user)


# ---------------------------------------------------------------------------
# .env loader (no python-dotenv dependency)
# ---------------------------------------------------------------------------


def _load_dotenv(env_path: Path = Path(".env")) -> None:
    """Load KEY=VALUE pairs from env_path into os.environ (setdefault — no overwrite)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------------------
# make_llm_client — real OpenAI client
# ---------------------------------------------------------------------------


def make_llm_client(model: str, env_path: Path | None = None) -> LLMClient:
    """
    Instantiate an OpenAIClient with API key from environment or .env.

    Parameters
    ----------
    model    : LLM model ID (e.g. "gpt-5.4-mini")
    env_path : Path to .env file; defaults to Path(".env"). Pass a non-existent
               path in tests to prevent loading from disk.

    Raises
    ------
    LLMAPIKeyError if OPENAI_API_KEY is not set.
    """
    _load_dotenv(env_path if env_path is not None else Path(".env"))
    from gonghaebun.llm.openai_client import OpenAIClient
    return OpenAIClient(model=model)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class GoldenEntry:
    id: str
    description: str
    dimensions: list[str]
    type: str = "standard"
    grader_input: dict[str, str] | None = None
    simulated_grading_response: str | None = None
    expected: dict[str, Any] | None = None


@dataclass
class EvalResult:
    case_id: str
    dimension: str
    passed: bool
    score: float | None
    message: str
    grading: GradingResult | None = None


# ---------------------------------------------------------------------------
# load_golden_set
# ---------------------------------------------------------------------------


def load_golden_set(golden_dir: Path = GOLDEN_SET_DIR) -> list[GoldenEntry]:
    """Load and validate all golden entry JSON files from golden_dir."""
    entries = []
    for path in sorted(golden_dir.glob("gc*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries.append(GoldenEntry(
            id=raw["id"],
            description=raw["description"],
            dimensions=raw["dimensions"],
            type=raw.get("type", "standard"),
            grader_input=raw.get("grader_input"),
            simulated_grading_response=raw.get("simulated_grading_response"),
            expected=raw.get("expected"),
        ))
    return entries


# ---------------------------------------------------------------------------
# token_recall metric
# ---------------------------------------------------------------------------


def token_recall(missing_elements: list[str], expected_answer: str) -> float:
    """
    Fraction of missing_element strings that share at least one word with expected_answer.

    Returns 0.0 if missing_elements is empty.
    """
    if not missing_elements:
        return 0.0
    expected_words = set(expected_answer.lower().split())
    hits = sum(
        1 for elem in missing_elements
        if any(w in expected_words for w in elem.lower().split())
    )
    return hits / len(missing_elements)


# ---------------------------------------------------------------------------
# Per-dimension eval functions
# ---------------------------------------------------------------------------


def _grade(entry: GoldenEntry, grader_client: LLMClient) -> GradingResult:
    """Run LLMGrader.grade() using the provided client and entry's grader_input."""
    gi = entry.grader_input or {}
    grader = LLMGrader(grader_client)
    return grader.grade(
        question=gi.get("question", ""),
        expected_answer=gi.get("expected_answer", ""),
        evidence_text=gi.get("evidence_text", ""),
        learner_response=gi.get("learner_response", ""),
    )


def eval_schema_parse(entry: GoldenEntry, grader_client: LLMClient) -> EvalResult:
    """Verify that grading produces a valid GradingResult (schema_parse dimension)."""
    try:
        result = _grade(entry, grader_client)
    except LLMResponseError as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="schema_parse",
            passed=False,
            score=None,
            message=f"Unexpected LLMResponseError: {exc}",
        )
    except Exception as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="schema_parse",
            passed=False,
            score=None,
            message=f"Unexpected error: {exc}",
        )

    exp = entry.expected or {}
    violations = []
    if exp.get("mastery_suggestion") and result.mastery_suggestion != exp["mastery_suggestion"]:
        violations.append(
            f"mastery_suggestion={result.mastery_suggestion!r}, expected {exp['mastery_suggestion']!r}"
        )
    if exp.get("accuracy_min") is not None and result.accuracy_score < exp["accuracy_min"]:
        violations.append(f"accuracy_score={result.accuracy_score} < min={exp['accuracy_min']}")
    if exp.get("accuracy_max") is not None and result.accuracy_score > exp["accuracy_max"]:
        violations.append(f"accuracy_score={result.accuracy_score} > max={exp['accuracy_max']}")

    passed = not violations
    msg = "Schema valid" if passed else "; ".join(violations)
    return EvalResult(
        case_id=entry.id,
        dimension="schema_parse",
        passed=passed,
        score=result.accuracy_score,
        message=msg,
        grading=result,
    )


def eval_wrong_to_solid(entry: GoldenEntry, grader_client: LLMClient) -> EvalResult:
    """Verify that a wrong learner answer is NOT graded as solid."""
    try:
        result = _grade(entry, grader_client)
    except Exception as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="wrong_to_solid",
            passed=False,
            score=None,
            message=f"Grading failed: {exc}",
        )

    # Key invariant: wrong answer must not reach solid mastery
    is_solid = result.mastery_suggestion == "solid" or result.accuracy_score > 0.84
    passed = not is_solid
    msg = (
        "Correctly graded as non-solid"
        if passed
        else f"CRITICAL: wrong answer graded solid "
             f"(accuracy={result.accuracy_score}, mastery={result.mastery_suggestion})"
    )
    return EvalResult(
        case_id=entry.id,
        dimension="wrong_to_solid",
        passed=passed,
        score=result.accuracy_score,
        message=msg,
        grading=result,
    )


def eval_misconception_detection(entry: GoldenEntry, grader_client: LLMClient) -> EvalResult:
    """Verify that a misconception in the learner response is flagged in errors."""
    try:
        result = _grade(entry, grader_client)
    except Exception as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="misconception_detection",
            passed=False,
            score=None,
            message=f"Grading failed: {exc}",
        )

    passed = bool(result.errors)
    msg = (
        f"Misconception detected ({len(result.errors)} error(s))"
        if passed
        else "No errors detected — misconception missed"
    )
    return EvalResult(
        case_id=entry.id,
        dimension="misconception_detection",
        passed=passed,
        score=float(bool(result.errors)),
        message=msg,
        grading=result,
    )


def eval_missing_elements_overlap(entry: GoldenEntry, grader_client: LLMClient) -> EvalResult:
    """
    Verify missing_elements is non-empty and compute token recall against expected_answer.
    """
    try:
        result = _grade(entry, grader_client)
    except Exception as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="missing_elements_overlap",
            passed=False,
            score=None,
            message=f"Grading failed: {exc}",
        )

    gi = entry.grader_input or {}
    expected_answer = gi.get("expected_answer", "")
    score = token_recall(result.missing_elements, expected_answer)
    passed = bool(result.missing_elements) and score > 0.0
    msg = (
        f"missing_elements={result.missing_elements}, token_recall={score:.2f}"
        if result.missing_elements
        else "missing_elements is empty — gaps not flagged"
    )
    return EvalResult(
        case_id=entry.id,
        dimension="missing_elements_overlap",
        passed=passed,
        score=score,
        message=msg,
        grading=result,
    )


def eval_expected_schema_failure(entry: GoldenEntry, grader_client: LLMClient) -> EvalResult:
    """
    Verify that a malformed response triggers graceful fallback (needs_human_review=True).

    The LLM grader no longer raises LLMResponseError; instead it falls back to a
    human-review result when the response cannot be parsed or validated.
    Not counted in schema_parse_success_rate.
    """
    try:
        result = _grade(entry, grader_client)
    except Exception as exc:
        return EvalResult(
            case_id=entry.id,
            dimension="expected_schema_failure",
            passed=False,
            score=None,
            message=f"Unexpected error {type(exc).__name__}: {exc}",
        )

    if result.needs_human_review:
        return EvalResult(
            case_id=entry.id,
            dimension="expected_schema_failure",
            passed=True,
            score=None,
            message="Malformed response produced fallback with needs_human_review=True",
        )
    return EvalResult(
        case_id=entry.id,
        dimension="expected_schema_failure",
        passed=False,
        score=None,
        message="Expected fallback not triggered — malformed response was accepted as valid",
    )


# ---------------------------------------------------------------------------
# Integration eval functions (gc006)
# ---------------------------------------------------------------------------


def _make_test_attempt(qid: str = "eval_q1") -> AttemptResult:
    """Create a minimal AttemptResult for integration tests (no LLM, no external files)."""
    from gonghaebun.models.question_bank import Evidence, Question

    evidence = Evidence(
        source_text="A set K is compact if every open cover of K has a finite subcover.",
        source_file="synthetic_eval.md",
        start_line=1,
        end_line=1,
        text_hash="eval_hash_001",
    )
    question = Question(
        question_id=qid,
        document_id="eval_doc",
        source_block_id="eval_doc_b000001",
        question_type="definition_recall",
        difficulty="medium",
        question="State the definition of compactness.",
        expected_answer="A set K is compact if every open cover of K has a finite subcover.",
        evidence=evidence,
        rule_id="R01_definition_recall",
    )
    grading = GradingResult(
        accuracy_score=0.75,
        mastery_suggestion="partial",
        raw_response="eval_mock",
    )
    return AttemptResult(
        question=question,
        learner_response="K is compact if every open cover has a finite subcover.",
        grading=grading,
    )


def eval_study_md_roundtrip(tmp_dir: Path) -> tuple[EvalResult, Path | None]:
    """
    Build a fake session, write artifacts, and validate STUDY.md.
    Returns (EvalResult, output_dir) — output_dir is None if failed.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        attempts = [_make_test_attempt()]
        session = build_study_session(
            session_id="eval-roundtrip-001",
            concept_id="compactness",
            source_path="synthetic",
            attempt_results=attempts,
            started_at=now,
            ended_at=now,
        )
        output_dir = write_session_artifacts(
            session=session,
            attempt_results=attempts,
            runs_dir=tmp_dir / "runs",
            study_md_path=tmp_dir / "STUDY.md",
        )
        validate_study_md(tmp_dir / "STUDY.md")
        return EvalResult(
            case_id="gc006",
            dimension="study_md_roundtrip",
            passed=True,
            score=None,
            message="STUDY.md written and validated successfully",
        ), output_dir
    except Exception as exc:
        return EvalResult(
            case_id="gc006",
            dimension="study_md_roundtrip",
            passed=False,
            score=None,
            message=f"Failed: {exc}",
        ), None


def eval_visualization_sanity(output_dir: Path | None) -> EvalResult:
    """Check that all 5 visualization artifacts exist with correct schema."""
    if output_dir is None:
        return EvalResult(
            case_id="gc006",
            dimension="visualization_sanity",
            passed=False,
            score=None,
            message="Skipped: study_md_roundtrip failed",
        )

    viz_dir = output_dir / "visualization"
    required_files = [
        "mastery_map.json",
        "recall_feedback.json",
        "review_queue.json",
        "mastery_map.mmd",
        "session_flow.mmd",
    ]
    missing_files = [f for f in required_files if not (viz_dir / f).exists()]
    if missing_files:
        return EvalResult(
            case_id="gc006",
            dimension="visualization_sanity",
            passed=False,
            score=None,
            message=f"Missing visualization files: {missing_files}",
        )

    # Verify mastery_map.json schema
    mastery_data = json.loads((viz_dir / "mastery_map.json").read_text(encoding="utf-8"))
    required_keys = {"concept_id", "overall_mastery", "representations", "weakest_links"}
    missing_keys = required_keys - mastery_data.keys()
    if missing_keys:
        return EvalResult(
            case_id="gc006",
            dimension="visualization_sanity",
            passed=False,
            score=None,
            message=f"mastery_map.json missing keys: {missing_keys}",
        )

    return EvalResult(
        case_id="gc006",
        dimension="visualization_sanity",
        passed=True,
        score=None,
        message="All 5 visualization artifacts present and schema-valid",
    )


# ---------------------------------------------------------------------------
# run_all_evals
# ---------------------------------------------------------------------------


def run_all_evals(
    golden_dir: Path = GOLDEN_SET_DIR,
    grader: str = "mock",
    model: str = "gpt-5.4-mini",
    tmp_dir: Path | None = None,
    env_path: Path | None = None,
) -> tuple[list[EvalResult], list[str]]:
    """
    Run all golden set evaluations.

    Parameters
    ----------
    golden_dir : directory of golden JSON files
    grader     : "mock" or "llm"
    model      : model ID (only for "llm")
    tmp_dir    : temp dir for integration tests (created if None)
    env_path   : path to .env (for make_llm_client; pass non-existent in tests)

    Returns
    -------
    (results, skipped_ids)
    """
    entries = load_golden_set(golden_dir)
    results: list[EvalResult] = []
    skipped: list[str] = []

    # Build LLM client once (reused across entries in LLM mode)
    llm_client: LLMClient | None = None
    if grader == "llm":
        llm_client = make_llm_client(model, env_path=env_path)

    own_tmp = False
    if tmp_dir is None:
        _td = tempfile.TemporaryDirectory()
        tmp_dir = Path(_td.name)
        own_tmp = True

    try:
        for entry in entries:
            # ---- gc007: expected schema failure ----
            if entry.id == EXPECTED_FAILURE_ID:
                if grader == "llm":
                    skipped.append(entry.id)
                    continue
                client = _FixtureLLMClient(entry.simulated_grading_response or "")
                results.append(eval_expected_schema_failure(entry, client))
                continue

            # ---- gc006: integration ----
            if entry.type == "integration":
                roundtrip_result, output_dir = eval_study_md_roundtrip(tmp_dir)
                viz_result = eval_visualization_sanity(output_dir)
                results.extend([roundtrip_result, viz_result])
                continue

            # ---- standard grading entries ----
            if grader == "mock":
                client: LLMClient = _FixtureLLMClient(entry.simulated_grading_response or "")
            else:
                client = llm_client  # type: ignore[assignment]

            for dimension in entry.dimensions:
                if dimension == "schema_parse":
                    results.append(eval_schema_parse(entry, client))
                elif dimension == "wrong_to_solid":
                    results.append(eval_wrong_to_solid(entry, client))
                elif dimension == "misconception_detection":
                    results.append(eval_misconception_detection(entry, client))
                elif dimension == "missing_elements_overlap":
                    results.append(eval_missing_elements_overlap(entry, client))
    finally:
        if own_tmp:
            _td.cleanup()  # type: ignore[possibly-undefined]

    return results, skipped


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _accuracy_by_label(results: list[EvalResult]) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for r in results:
        if r.grading is not None:
            label = r.grading.mastery_suggestion
            groups.setdefault(label, []).append(r.grading.accuracy_score)
    return {label: sum(scores) / len(scores) for label, scores in groups.items()}


def compute_metrics(results: list[EvalResult]) -> dict[str, Any]:
    """Compute aggregate quality metrics from a list of EvalResults."""
    schema_results = [r for r in results if r.dimension == "schema_parse"]
    failure_result = next(
        (r for r in results if r.dimension == "expected_schema_failure"), None
    )
    wrong_results = [r for r in results if r.dimension == "wrong_to_solid"]
    misconception_results = [r for r in results if r.dimension == "misconception_detection"]
    missing_results = [r for r in results if r.dimension == "missing_elements_overlap"]
    all_grading = [r for r in results if r.grading is not None]

    return {
        "schema_parse_success_rate": _mean([float(r.passed) for r in schema_results]),
        "expected_schema_failure_handled": (
            failure_result.passed if failure_result is not None else None
        ),
        "wrong_to_solid_count": sum(not r.passed for r in wrong_results),
        "misconception_error_detection_rate": _mean(
            [float(r.passed) for r in misconception_results]
        ),
        "missing_elements_overlap": _mean(
            [r.score for r in missing_results if r.score is not None]
        ),
        "needs_human_review_rate": _mean(
            [float(r.grading.needs_human_review) for r in all_grading]
        ),
        "average_confidence": _mean(
            [r.grading.confidence for r in all_grading]
        ),
        "average_accuracy_by_label": _accuracy_by_label(all_grading),
    }


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def build_report(
    results: list[EvalResult],
    metrics: dict[str, Any],
    grader: str,
    model: str,
    skipped: list[str] | None = None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Grading Eval Report — MVP3.5",
        f"_Generated: {timestamp}  Grader: {grader}  Model: {model}_",
        "",
        "## Metrics Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for key, value in metrics.items():
        if key == "average_accuracy_by_label":
            if isinstance(value, dict):
                for label, score in value.items():
                    lines.append(f"| average_accuracy [{label}] | {score:.3f} |")
            else:
                lines.append(f"| {key} | {value} |")
        elif isinstance(value, float):
            lines.append(f"| {key} | {value:.3f} |")
        else:
            lines.append(f"| {key} | {value} |")

    lines += [
        "",
        "## Per-Case Results",
        "",
        "| ID | Dimension | Passed | Score | Message |",
        "|----|-----------|--------|-------|---------|",
    ]
    for r in results:
        score_str = f"{r.score:.3f}" if r.score is not None else "-"
        passed_str = "✓" if r.passed else "✗"
        lines.append(
            f"| {r.case_id} | {r.dimension} | {passed_str} | {score_str} | {r.message} |"
        )

    lines += ["", "## Skipped Cases", ""]
    if skipped:
        for sid in skipped:
            lines.append(
                f"- `{sid}` — skipped in LLM mode (requires simulated malformed JSON)"
            )
    else:
        lines.append("_(none)_")

    critical = [r for r in results if not r.passed and r.dimension in ("wrong_to_solid",)]
    lines += ["", "## Critical Failures", ""]
    if critical:
        for r in critical:
            lines.append(f"- **{r.case_id}** [{r.dimension}]: {r.message}")
    else:
        lines.append("_(none)_")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI argument parser (also importable for tests)
# ---------------------------------------------------------------------------


def parse_eval_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_grading_eval",
        description="Gonghaebun MVP3.5 Engine Quality Gate",
    )
    parser.add_argument(
        "--grader",
        choices=["mock", "llm"],
        default="mock",
        help="Grading mode: mock (offline, default) or llm (requires OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.4-mini",
        metavar="MODEL",
        help="LLM model ID (only with --grader llm). Default: gpt-5.4-mini",
    )
    parser.add_argument(
        "--golden",
        default=str(GOLDEN_SET_DIR),
        metavar="DIR",
        help=f"Path to golden_set directory. Default: {GOLDEN_SET_DIR}",
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        metavar="PATH",
        help=f"Output report path. Default: {REPORT_PATH}",
    )
    parser.add_argument(
        "--out-dir",
        default=str(RUNS_DIR),
        dest="out_dir",
        metavar="DIR",
        help=f"Directory for LLM mode per-case outputs. Default: {RUNS_DIR}",
    )
    return parser.parse_args(argv)

#!/usr/bin/env python3
"""
Real-LLM end-to-end smoke test against a running Gonghaebun API server.

Usage:
    python scripts/smoke_real_llm.py --allow-real-llm
    python scripts/smoke_real_llm.py --allow-real-llm --base-url http://0.0.0.0:8000

Requires:
    - --allow-real-llm flag (mandatory, refuses to run without it)
    - Running uvicorn server (does NOT start one automatically)
    - Environment: GONGHAEBUN_LLM_DISABLED=0, GONGHAEBUN_LLM_PROVIDER=openai,
      GONGHAEBUN_LLM_MODEL=gpt-5.5, OPENAI_API_KEY set

Exits 0 if all steps pass, 1 if any fail.
Requires no third-party libraries — stdlib only.

SECURITY:
    - Never prints API key values, prompt bodies, or response bodies
    - On failure: prints step name and exception class only
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
EXPECTED_MODEL = "gpt-5.5"
CONCEPT_ID = "compactness"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def http_get(url: str, timeout: int = 30) -> tuple[int, dict]:
    """GET request, return (status, parsed JSON body)."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def http_post(url: str, body: dict, timeout: int = 60) -> tuple[int, dict]:
    """POST request with JSON body, return (status, parsed JSON body)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp_body = resp.read().decode("utf-8")
        return resp.status, json.loads(resp_body)


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def preflight_checks() -> bool:
    """Verify environment variables. Returns True if all pass."""
    ok = True

    # OPENAI_API_KEY — existence only, never print value
    key = os.getenv("OPENAI_API_KEY", "")
    if key.strip():
        print("  OPENAI_API_KEY: set")
    else:
        print("  OPENAI_API_KEY: not set")
        print("  ERROR: OPENAI_API_KEY is required for real LLM mode.")
        ok = False

    # GONGHAEBUN_LLM_DISABLED must be "0"
    disabled = os.getenv("GONGHAEBUN_LLM_DISABLED", "1")
    print(f"  GONGHAEBUN_LLM_DISABLED: {disabled}")
    if disabled != "0":
        print("  ERROR: GONGHAEBUN_LLM_DISABLED must be '0' for real LLM mode.")
        ok = False

    # GONGHAEBUN_LLM_PROVIDER must be "openai"
    provider = os.getenv("GONGHAEBUN_LLM_PROVIDER", "mock")
    print(f"  GONGHAEBUN_LLM_PROVIDER: {provider}")
    if provider != "openai":
        print("  ERROR: GONGHAEBUN_LLM_PROVIDER must be 'openai' for real LLM mode.")
        ok = False

    # GONGHAEBUN_LLM_MODEL must be gpt-5.5 (strict)
    model = os.getenv("GONGHAEBUN_LLM_MODEL", EXPECTED_MODEL)
    print(f"  GONGHAEBUN_LLM_MODEL: {model}")
    if model != EXPECTED_MODEL:
        print(f"  ERROR: GONGHAEBUN_LLM_MODEL must be '{EXPECTED_MODEL}' for this smoke test.")
        ok = False

    return ok


def print_expected_stages() -> None:
    """Print expected LLM call stages before starting."""
    print("\nExpected LLM API calls:")
    print("  Session creation:")
    print("    - Stage 3 (representation gen): 5x complete() — prompt-guided")
    print("    - Stage 4 (misconception check): 1x complete_json() — prompt-guided")
    print("    - Stage 6 (recall task gen):     1x complete_json() — prompt-guided")
    print("  Self-explain (formal):      1x complete_structured(EVALUATION_OUTPUT_SCHEMA)")
    print("  Self-explain (proof_schema): 1x complete_structured(EVALUATION_OUTPUT_SCHEMA)")
    print("  Recall evaluation:          1x complete_structured(EVALUATION_OUTPUT_SCHEMA)")
    print("  Total: ~10 LLM API calls")
    print()


# ---------------------------------------------------------------------------
# Smoke test steps
# ---------------------------------------------------------------------------

def step_a_health(base: str) -> bool:
    """GET /api/health → status=ok."""
    status, data = http_get(f"{base}/api/health")
    if status != 200 or data.get("status") != "ok":
        print(f"  [FAIL] Health check: status={data.get('status')}")
        return False
    print("  [PASS] A. GET /api/health → status=ok")
    return True


def step_b_ready(base: str) -> bool:
    """GET /api/ready → ready=true."""
    status, data = http_get(f"{base}/api/ready")
    if status != 200 or data.get("ready") is not True:
        print(f"  [FAIL] Ready check: ready={data.get('ready')}")
        return False
    checks = data.get("checks", {})
    llm_status = checks.get("llm", "unknown")
    print(f"  [PASS] B. GET /api/ready → ready=true (llm: {llm_status})")
    return True


def step_c_create_session(base: str) -> str | None:
    """POST /api/study-session → 201, return session_id."""
    status, data = http_post(
        f"{base}/api/study-session",
        {"concept_id": CONCEPT_ID},
        timeout=120,  # session creation triggers 7 LLM calls
    )
    if status != 201:
        print(f"  [FAIL] Create session: HTTP {status}")
        return None
    session_id = data.get("session_id")
    if not session_id:
        print("  [FAIL] Create session: no session_id in response")
        return None
    rep_count = len(data.get("representations", {}))
    prereq_count = len(data.get("prerequisites", []))
    misconception_count = len(data.get("misconceptions", []))
    print(f"  [PASS] C. POST /api/study-session → session_id={session_id}")
    print(f"         representations={rep_count}, prerequisites={prereq_count}, misconceptions={misconception_count}")
    return session_id


def step_d_diagnose(base: str, session_id: str) -> bool:
    """POST diagnose."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/diagnose",
        {
            "prior_knowledge": "컴팩트 집합의 기본 정의를 알고 있습니다",
            "gap_description": "증명 구조가 약합니다",
        },
    )
    if status != 200:
        print(f"  [FAIL] Diagnose: HTTP {status}")
        return False
    mastery = data.get("initial_mastery_estimate", "?")
    print(f"  [PASS] D. POST diagnose → initial_mastery_estimate={mastery}")
    return True


def step_e_self_explain_formal(base: str, session_id: str) -> bool:
    """POST self-explain (formal) → structured eval."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/self-explain",
        {
            "representation_type": "formal",
            "learner_explanation": (
                "A set K in a metric space (X, d) is compact if every "
                "open cover of K has a finite subcover."
            ),
        },
        timeout=60,
    )
    if status != 200:
        print(f"  [FAIL] Self-explain (formal): HTTP {status}")
        return False
    score = data.get("accuracy_score")
    if not isinstance(score, (int, float)):
        print(f"  [FAIL] Self-explain (formal): accuracy_score is not a number")
        return False
    has_feedback = bool(data.get("feedback"))
    print(f"  [PASS] E. POST self-explain (formal) → accuracy_score={score:.2f}, feedback={'yes' if has_feedback else 'no'}")
    return True


def step_f_self_explain_proof(base: str, session_id: str) -> bool:
    """POST self-explain (proof_schema) → structured eval."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/self-explain",
        {
            "representation_type": "proof_schema",
            "learner_explanation": (
                "To prove compactness, take arbitrary open cover and extract "
                "finite subcover via Heine-Borel or sequential compactness."
            ),
        },
        timeout=60,
    )
    if status != 200:
        print(f"  [FAIL] Self-explain (proof_schema): HTTP {status}")
        return False
    score = data.get("accuracy_score")
    if not isinstance(score, (int, float)):
        print(f"  [FAIL] Self-explain (proof_schema): accuracy_score is not a number")
        return False
    print(f"  [PASS] F. POST self-explain (proof_schema) → accuracy_score={score:.2f}")
    return True


def step_g_advance_steps(base: str, session_id: str) -> bool:
    """POST advance for prerequisites, representations, misconceptions."""
    for step_name in ("prerequisites", "representations", "misconceptions"):
        status, data = http_post(
            f"{base}/api/study-session/{session_id}/advance",
            {"completed_step": step_name},
        )
        if status != 200:
            print(f"  [FAIL] Advance ({step_name}): HTTP {status}")
            return False
    current = data.get("current_step_name", "?")
    print(f"  [PASS] G. POST advance x3 → current_step_name={current}")
    return True


def step_h_recall(base: str, session_id: str) -> bool:
    """POST recall → structured eval."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/recall",
        {
            "learner_response": (
                "A compact set in a metric space has the property that every "
                "open cover admits a finite subcover. This is equivalent to "
                "sequential compactness in metric spaces."
            ),
        },
        timeout=60,
    )
    if status != 200:
        print(f"  [FAIL] Recall: HTTP {status}")
        return False
    score = data.get("accuracy_score")
    if not isinstance(score, (int, float)):
        print(f"  [FAIL] Recall: accuracy_score is not a number")
        return False
    has_feedback = bool(data.get("feedback"))
    print(f"  [PASS] H. POST recall → accuracy_score={score:.2f}, feedback={'yes' if has_feedback else 'no'}")
    return True


def step_i_advance_recall(base: str, session_id: str) -> bool:
    """POST advance for recall."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/advance",
        {"completed_step": "recall"},
    )
    if status != 200:
        print(f"  [FAIL] Advance (recall): HTTP {status}")
        return False
    current = data.get("current_step_name", "?")
    print(f"  [PASS] I. POST advance (recall) → current_step_name={current}")
    return True


def step_j_complete(base: str, session_id: str) -> dict | None:
    """POST complete → completed=true, study_md_updated."""
    status, data = http_post(
        f"{base}/api/study-session/{session_id}/complete",
        {},
    )
    if status != 200:
        print(f"  [FAIL] Complete: HTTP {status}")
        return None
    completed = data.get("completed")
    updated = data.get("study_md_updated")
    if completed is not True:
        print(f"  [FAIL] Complete: completed={completed}")
        return None
    next_review = data.get("next_review_date", "?")
    mastery_count = len(data.get("mastery_updates", []))
    patch_path = data.get("study_patch_path", "")
    print(f"  [PASS] J. POST complete → completed=true, study_md_updated={updated}")
    print(f"         next_review_date={next_review}, mastery_updates={mastery_count}")
    if patch_path:
        print(f"         study_patch_path={patch_path}")
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = ArgumentParser(
        description="Real-LLM end-to-end smoke test for Gonghaebun API.",
        epilog="Requires a running uvicorn server and real OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--allow-real-llm",
        action="store_true",
        help="Required flag to confirm real OpenAI API calls (mandatory).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the running server (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    # Windows UTF-8 output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Mandatory flag check
    if not args.allow_real_llm:
        print("ERROR: --allow-real-llm flag is required.")
        print("This script makes real OpenAI API calls that incur costs.")
        print("Usage: python scripts/smoke_real_llm.py --allow-real-llm")
        return 1

    base = args.base_url.rstrip("/")

    print(f"Real LLM Smoke Test: {base}")
    print(f"Concept: {CONCEPT_ID}")
    print()

    # Pre-flight
    print("Pre-flight checks:")
    if not preflight_checks():
        print("\nPre-flight FAILED. Fix environment variables and retry.")
        return 1
    print("  Pre-flight OK.")

    print_expected_stages()

    # Run steps
    t0 = time.time()
    step_name = ""
    session_id = None

    try:
        step_name = "A. Health"
        if not step_a_health(base):
            return 1

        step_name = "B. Ready"
        if not step_b_ready(base):
            return 1

        step_name = "C. Create session"
        session_id = step_c_create_session(base)
        if session_id is None:
            return 1

        step_name = "D. Diagnose"
        if not step_d_diagnose(base, session_id):
            return 1

        step_name = "E. Self-explain (formal)"
        if not step_e_self_explain_formal(base, session_id):
            return 1

        step_name = "F. Self-explain (proof_schema)"
        if not step_f_self_explain_proof(base, session_id):
            return 1

        step_name = "G. Advance (prerequisites/representations/misconceptions)"
        if not step_g_advance_steps(base, session_id):
            return 1

        step_name = "H. Recall"
        if not step_h_recall(base, session_id):
            return 1

        step_name = "I. Advance (recall)"
        if not step_i_advance_recall(base, session_id):
            return 1

        step_name = "J. Complete"
        result = step_j_complete(base, session_id)
        if result is None:
            return 1

    except urllib.error.HTTPError as e:
        print(f"\n=== Real LLM Smoke Test FAILED ===")
        print(f"Failed at: {step_name}")
        print(f"Exception: {type(e).__name__} (HTTP {e.code})")
        return 1
    except Exception as e:
        print(f"\n=== Real LLM Smoke Test FAILED ===")
        print(f"Failed at: {step_name}")
        print(f"Exception: {type(e).__name__}")
        return 1

    elapsed = time.time() - t0

    # Success summary
    print(f"\n=== Real LLM Smoke Test PASSED ===")
    print(f"Session ID: {session_id}")
    print(f"Completed: True")
    print(f"STUDY.md updated: {result.get('study_md_updated')}")
    print(f"Next review date: {result.get('next_review_date')}")
    print(f"Mastery updates: {len(result.get('mastery_updates', []))} representations")
    print(f"Artifacts:")
    print(f"  runs/{session_id}/study_session_state.json")
    print(f"  runs/{session_id}/STUDY.patch.md")
    print(f"  data/gonghaebun/default/STUDY.md")
    print(f"Runtime: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

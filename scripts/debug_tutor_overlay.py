#!/usr/bin/env python3
"""
Diagnostic script for the LLM Tutor Overlay.

Prints environment status, tests each layer of the tutor pipeline,
and reports exactly what happens at each step. Run from project root:

    python scripts/debug_tutor_overlay.py

Does NOT print OPENAI_API_KEY.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

# Fix Windows console encoding for Korean/Unicode output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 0. Load .env from project root (if python-dotenv is available)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent

dotenv_path = PROJECT_ROOT / ".env"
if dotenv_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path, override=False)
        print(f"[ok] Loaded .env from {dotenv_path}")
    except ImportError:
        print("[warn] python-dotenv not installed; .env NOT loaded")
else:
    print(f"[info] No .env file at {dotenv_path}")

# ---------------------------------------------------------------------------
# 1. Logging setup (so we see gonghaebun.* logs in this script)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stderr,
)

# ---------------------------------------------------------------------------
# 2. Print environment status (no secrets)
# ---------------------------------------------------------------------------
print("\n=== Environment Status ===")
env_vars = {
    "GONGHAEBUN_LLM_DISABLED": os.getenv("GONGHAEBUN_LLM_DISABLED", "(unset → default 1)"),
    "GONGHAEBUN_LLM_PROVIDER": os.getenv("GONGHAEBUN_LLM_PROVIDER", "(unset → default mock)"),
    "GONGHAEBUN_LLM_MODEL": os.getenv("GONGHAEBUN_LLM_MODEL", "(unset → default gpt-5.5)"),
    "GONGHAEBUN_GRADER": os.getenv("GONGHAEBUN_GRADER", "(unset)"),
    "OPENAI_API_KEY": "present" if os.getenv("OPENAI_API_KEY") else "MISSING",
}
for k, v in env_vars.items():
    print(f"  {k} = {v}")

# ---------------------------------------------------------------------------
# 3. Test _is_question_like
# ---------------------------------------------------------------------------
print("\n=== _is_question_like tests ===")
try:
    from apps.api.services.compiler_analyzer_service import _is_question_like

    test_messages = [
        "그럼 (0,1)은 bounded인데 왜 compact하지 않다고 하는 거야? open cover 관점에서 설명해줘",
        "옹골성",
        "안녕",
        "finite subcover가 뭐야?",
        "compact는 closed + bounded 아냐?",
    ]
    for msg in test_messages:
        result = _is_question_like(msg)
        print(f"  question_like={result:<5}  msg={msg[:60]}")
except Exception:
    traceback.print_exc()

# ---------------------------------------------------------------------------
# 4. Test retrieve_context
# ---------------------------------------------------------------------------
print("\n=== retrieve_context (compactness) ===")
try:
    from apps.api.services.rag_context_service import retrieve_context

    snippets = retrieve_context(
        concept_id="compactness",
        message="(0,1)은 왜 compact하지 않아?",
        top_k=5,
    )
    print(f"  Retrieved {len(snippets)} snippets:")
    for s in snippets:
        print(f"    [{s.score:.2f}] {s.source_id}  {s.title[:40]}")
except Exception:
    traceback.print_exc()

# ---------------------------------------------------------------------------
# 5. Test tutor_respond
# ---------------------------------------------------------------------------
print("\n=== tutor_respond ===")
DEMO_MESSAGE = (
    "그럼 (0,1)은 bounded인데 왜 compact하지 않다고 하는 거야? "
    "open cover 관점에서 설명해줘"
)
try:
    from apps.api.services.tutor_orchestrator_service import tutor_respond

    print(f"  Calling tutor_respond with: {DEMO_MESSAGE[:80]}...")
    result = tutor_respond(DEMO_MESSAGE)

    if result is None:
        print("  result: None")
    else:
        print(f"  result is None?       {result is None}")
        print(f"  llm_used:             {result.llm_used}")
        print(f"  rag_used:             {result.rag_used}")
        print(f"  learning_task:        {result.learning_task}")
        print(f"  primary_concept:      {result.primary_concept}")
        print(f"  confidence:           {result.confidence}")
        print(f"  misconception_tags:   {result.misconception_tags}")
        print(f"  direct_answer[:500]:  {result.direct_answer[:500]}")
except Exception:
    print("  EXCEPTION during tutor_respond:")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# 6. Test get_llm_client directly (to see what provider resolves to)
# ---------------------------------------------------------------------------
print("\n=== get_llm_client ===")
try:
    from gonghaebun.llm.factory import get_llm_client

    client = get_llm_client()
    print(f"  Client class: {type(client).__name__}")
    if hasattr(client, "_model"):
        print(f"  Model:        {client._model}")
except Exception:
    print("  EXCEPTION during get_llm_client:")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# 7. Test full analyze_message path
# ---------------------------------------------------------------------------
print("\n=== analyze_message (full path) ===")
try:
    from apps.api.services.compiler_analyzer_service import analyze_message

    result = analyze_message(DEMO_MESSAGE)
    print(f"  concept_id:    {result.get('concept_id')}")
    print(f"  intent:        {result.get('intent')}")
    print(f"  render_mode:   {result.get('render_mode')}")
    print(f"  llm_used:      {result.get('llm_used')}")
    print(f"  rag_used:      {result.get('rag_used')}")
    print(f"  direct_answer: {str(result.get('direct_answer', ''))[:200]}")
except Exception:
    print("  EXCEPTION during analyze_message:")
    traceback.print_exc()

print("\n=== Done ===")

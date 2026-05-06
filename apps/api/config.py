"""
API configuration — all paths are env-overridable.

Layout assumption:
    data/gonghaebun/default/
      STUDY.md
      banks/      ← concept question banks
      runs/       ← session artifacts
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT = Path(os.getenv("GONGHAEBUN_DATA_ROOT", "data/gonghaebun/default"))
BANK_ROOT  = Path(os.getenv("GONGHAEBUN_BANK_ROOT", str(DATA_ROOT / "banks")))
RUNS_DIR   = Path(os.getenv("GONGHAEBUN_RUNS_DIR",  str(DATA_ROOT / "runs")))
STUDY_MD    = Path(os.getenv("GONGHAEBUN_STUDY_MD",    str(DATA_ROOT / "STUDY.md")))
SOURCES_DIR = Path(os.getenv("GONGHAEBUN_SOURCES_DIR", str(DATA_ROOT / "sources")))

# LLM grader guardrails
LLM_MAX_CALLS_PER_SESSION = int(os.getenv("GONGHAEBUN_LLM_MAX_CALLS_PER_SESSION", "20"))
LLM_TIMEOUT_SECONDS       = float(os.getenv("GONGHAEBUN_LLM_TIMEOUT_SECONDS", "30"))
LLM_DISABLED              = os.getenv("GONGHAEBUN_LLM_DISABLED", "1") == "1"
LLM_PROVIDER              = os.getenv("GONGHAEBUN_LLM_PROVIDER", "mock")
LLM_MODEL                 = os.getenv("GONGHAEBUN_LLM_MODEL", "gpt-5.5")

# Server
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "GONGHAEBUN_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174",
    ).split(",")
    if o.strip()
]
API_HOST       = os.getenv("GONGHAEBUN_API_HOST", "127.0.0.1")
API_PORT       = int(os.getenv("GONGHAEBUN_API_PORT", "8000"))
DEFAULT_GRADER = os.getenv("GONGHAEBUN_GRADER", "mock")
SERVE_FRONTEND = os.getenv("GONGHAEBUN_SERVE_FRONTEND", "1") == "1"

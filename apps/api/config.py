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

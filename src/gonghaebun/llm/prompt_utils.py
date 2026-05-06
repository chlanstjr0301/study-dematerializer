"""Prompt text utilities for LLM clients."""
from __future__ import annotations

import re

_FIXTURE_MARKER_RE = re.compile(r"\s*__fixture__:\S+\s*$")


def strip_fixture_marker(text: str) -> str:
    """Remove __fixture__:... marker from end of prompt text."""
    return _FIXTURE_MARKER_RE.sub("", text)

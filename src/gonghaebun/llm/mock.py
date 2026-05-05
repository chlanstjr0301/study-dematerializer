"""
MockLLMClient — deterministic, no network calls.

Loads fixture JSON from tests/fixtures/{concept_id}/{stage_key}.json.
The fixture directory is resolved relative to the repo root via the
GONGHAEBUN_FIXTURE_DIR env var (default: tests/fixtures).
"""
from __future__ import annotations
import json
import os
from pathlib import Path

from .base import LLMClient


def _fixture_dir() -> Path:
    env = os.environ.get("GONGHAEBUN_FIXTURE_DIR")
    if env:
        return Path(env)
    # Walk up from this file to repo root, then into tests/fixtures
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "tests" / "fixtures"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot locate tests/fixtures directory. "
        "Set GONGHAEBUN_FIXTURE_DIR env var to the fixture directory path."
    )


class MockLLMClient(LLMClient):
    """
    Returns deterministic outputs from fixture files.
    Never makes network calls.

    Fixture selection: the caller passes context via the user prompt.
    MockLLMClient uses a simple key extracted from the user prompt to
    select the right fixture file.

    Stage keys embedded in user prompts:
      __fixture__:{concept_id}/{stage_key}
    e.g. "__fixture__:compactness/representations"
    """

    def complete(self, system: str, user: str) -> str:
        data = self._load(user)
        if isinstance(data, dict) and "text" in data:
            return data["text"]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def complete_json(self, system: str, user: str) -> dict:
        data = self._load(user)
        if not isinstance(data, dict):
            raise ValueError(f"Fixture is not a JSON object: {data!r}")
        return data

    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict:
        """Delegates to complete_json(); json_schema is ignored in mock mode."""
        return self.complete_json(system, user)

    def _load(self, user: str) -> dict | str:
        key = self._extract_key(user)
        if key is None:
            return {"text": "[mock: no fixture key found in prompt]"}
        parts = key.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Fixture key must be concept/stage, got: {key!r}")
        concept_id, stage_key = parts
        fixture_path = _fixture_dir() / concept_id / f"{stage_key}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        return json.loads(fixture_path.read_text(encoding="utf-8"))

    @staticmethod
    def _extract_key(text: str) -> str | None:
        marker = "__fixture__:"
        idx = text.find(marker)
        if idx == -1:
            return None
        rest = text[idx + len(marker):]
        return rest.split()[0].strip()

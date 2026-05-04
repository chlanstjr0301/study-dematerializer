"""
Service: recall sessions — list, get, run (MVP4-B adds run_session).

GET operations are implemented here for MVP4-A.
POST (run_session) is a stub that raises NotImplementedError in MVP4-A
and will be filled in during MVP4-B.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import apps.api.config as config

# Artifact file names produced by write_session_artifacts()
_ARTIFACT_MAP: dict[str, str] = {
    "mastery_map":      "visualization/mastery_map.json",
    "recall_feedback":  "visualization/recall_feedback.json",
    "review_queue":     "visualization/review_queue.json",
    "mastery_map_mmd":  "visualization/mastery_map.mmd",
    "session_flow_mmd": "visualization/session_flow.mmd",
}


def list_sessions(runs_dir: Path | None = None) -> list[dict]:
    """
    Scan runs_dir for session directories that contain session.json.

    Returns [{session_id, concept_id, started_at, ended_at}] sorted by started_at descending.
    """
    base = runs_dir or config.RUNS_DIR
    if not base.exists():
        return []

    items: list[dict] = []
    for session_json in base.glob("*/session.json"):
        try:
            data = json.loads(session_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        items.append({
            "session_id": data.get("session_id", session_json.parent.name),
            "concept_id": data.get("concept_id", ""),
            "started_at": data.get("started_at", ""),
            "ended_at":   data.get("ended_at"),
        })

    items.sort(key=lambda x: x["started_at"], reverse=True)
    return items


def get_session(session_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    """
    Return {session, attempts} for the given session_id.

    Raises FileNotFoundError if the session directory or session.json does not exist.
    """
    base = runs_dir or config.RUNS_DIR
    session_dir = base / session_id

    session_json = session_dir / "session.json"
    if not session_json.exists():
        raise FileNotFoundError(f"Session not found: {session_id!r}")

    session_data = json.loads(session_json.read_text(encoding="utf-8"))

    attempts_json = session_dir / "recall_attempts.json"
    attempts_data: list[dict] = []
    if attempts_json.exists():
        try:
            attempts_data = json.loads(attempts_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {"session": session_data, "attempts": attempts_data}


def get_viz(
    session_id: str,
    artifact: str,
    runs_dir: Path | None = None,
) -> Any:
    """
    Return the content of a visualization artifact.

    For JSON artifacts, returns a parsed dict/list.
    For .mmd text artifacts, returns a string.

    Raises FileNotFoundError if session or artifact does not exist.
    Raises ValueError if artifact name is not recognised.
    """
    if artifact not in _ARTIFACT_MAP:
        raise ValueError(
            f"Unknown artifact {artifact!r}. "
            f"Valid values: {list(_ARTIFACT_MAP)}"
        )

    base = runs_dir or config.RUNS_DIR
    path = base / session_id / _ARTIFACT_MAP[artifact]

    if not path.exists():
        raise FileNotFoundError(
            f"Artifact {artifact!r} not found for session {session_id!r}"
        )

    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return text


def get_summary(session_id: str, runs_dir: Path | None = None) -> str:
    """
    Return session_summary.md content.

    Raises FileNotFoundError if not present.
    """
    base = runs_dir or config.RUNS_DIR
    path = base / session_id / "session_summary.md"
    if not path.exists():
        raise FileNotFoundError(
            f"session_summary.md not found for session {session_id!r}"
        )
    return path.read_text(encoding="utf-8")


def run_session(req: Any, runs_dir: Path | None = None, study_md_path: Path | None = None) -> dict:
    """
    Run a recall session (MVP4-B implementation).

    This stub is replaced in MVP4-B when POST /api/sessions is fully implemented.
    """
    raise NotImplementedError("POST /api/sessions is implemented in MVP4-B.")

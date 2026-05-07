"""
Service: recall sessions — list, get, run.

GET operations (list_sessions, get_session, get_viz, get_summary) serve existing artifacts.
POST (run_session) runs a new recall session via the MVP3 engine (grader=mock supported;
grader=llm deferred to MVP4-E).
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
    Run a recall session and write all artifacts.

    Parameters
    ----------
    req            : RunSessionRequest (concept_id, questions_path, grader, model,
                     limit, answers, default_answer)
    runs_dir       : override for config.RUNS_DIR (used in tests)
    study_md_path  : override for config.STUDY_MD (used in tests)

    Returns
    -------
    dict with keys: session_id, summary_md, attempt_count

    Raises
    ------
    NotImplementedError : grader='llm' or grader='self' (MVP4-E/later)
    ValueError          : validation failures (path traversal, missing self_score, etc.)
    """
    import uuid
    from datetime import datetime, timezone

    from gonghaebun.grading.factory import make_grader
    from gonghaebun.grading.schemas import GradingResult
    from gonghaebun.study_loop.question_loader import load_recall_questions
    from gonghaebun.study_loop.session_writer import build_study_session, write_session_artifacts
    from gonghaebun.study_loop.white_recall import run_white_recall_batch, run_white_recall_session
    from apps.api.services.bank_service import safe_resolve_under

    # Grader gating
    if req.grader == "llm":
        if config.LLM_DISABLED:
            raise ValueError(
                "LLM grader is disabled (GONGHAEBUN_LLM_DISABLED=1). Use grader='mock'."
            )
    if req.grader == "self":
        if req.answers:
            for a in req.answers:
                if a.self_score is None:
                    raise ValueError(
                        f"self_score is required for question {a.question_id!r} "
                        "when grader='self'."
                    )
        else:
            raise ValueError(
                "grader='self' requires explicit answers with self_score for each question."
            )
        raise NotImplementedError("grader='self' is not fully supported in MVP4-B.")

    # Path safety: resolve questions_path relative to BANK_ROOT
    questions_path = safe_resolve_under(config.BANK_ROOT, req.questions_path)

    # Load questions
    questions = load_recall_questions(questions_path, limit=req.limit)
    if not questions:
        raise ValueError(f"No accepted questions found at {req.questions_path!r}.")

    # Build grader
    from gonghaebun.llm.errors import LLMAPIKeyError
    try:
        grader = make_grader(req.grader, req.model)
    except LLMAPIKeyError as e:
        raise ValueError(f"LLM grader requires OPENAI_API_KEY: {e}") from e

    started_at = datetime.now(timezone.utc).isoformat()
    session_id = str(uuid.uuid4())

    # Answer resolution
    if req.answers is not None:
        # Mode A: explicit per-question answers
        from gonghaebun.grading.llm_grader import LLMGrader
        from gonghaebun.study_loop.mastery import QUESTION_TYPE_TO_REP
        answer_map = {a.question_id: a.learner_response for a in req.answers}
        responses: list[tuple[str, GradingResult]] = []
        for q in questions:
            if isinstance(grader, LLMGrader):
                grader._set_context(
                    req.concept_id,
                    QUESTION_TYPE_TO_REP.get(q.question_type, "formal"),
                    q.question_id,
                )
            response = answer_map.get(q.question_id, "")
            if not response.strip():
                grading = GradingResult(
                    accuracy_score=0.0,
                    needs_human_review=False,
                    feedback="No answer provided.",
                    mastery_suggestion="unknown",
                    raw_response="",
                )
            else:
                grading = grader.grade(
                    question=q.question,
                    expected_answer=q.expected_answer,
                    evidence_text=q.evidence.source_text,
                    learner_response=response,
                )
            responses.append((response, grading))
        attempt_results = run_white_recall_batch(questions, responses)
    else:
        # Mode B: single default_answer (non-interactive / smoke mode)
        attempt_results = run_white_recall_session(
            questions,
            grader,
            no_interactive=True,
            default_answer=req.default_answer or "",
        )

    ended_at = datetime.now(timezone.utc).isoformat()

    session = build_study_session(
        session_id=session_id,
        concept_id=req.concept_id,
        source_path=str(questions_path),
        attempt_results=attempt_results,
        started_at=started_at,
        ended_at=ended_at,
        grader_type=req.grader,
    )

    runs = runs_dir or config.RUNS_DIR
    study_md = study_md_path or config.STUDY_MD

    output_dir = write_session_artifacts(
        session=session,
        attempt_results=attempt_results,
        runs_dir=runs,
        study_md_path=study_md,
        grader_type=req.grader,
        grader=grader,
    )

    summary_md = ""
    summary_path = output_dir / "session_summary.md"
    if summary_path.exists():
        summary_md = summary_path.read_text(encoding="utf-8")

    return {
        "session_id": session_id,
        "summary_md": summary_md,
        "attempt_count": len(attempt_results),
    }

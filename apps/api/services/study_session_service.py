"""
Service: Study Session — full pipeline lifecycle for integrated study sessions.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import apps.api.config as config
from apps.api.services.bank_service import safe_resolve_under
from apps.api.services.compiler_analyzer_service import GAP_CUES, KOREAN_NAMES
from apps.api.services.path_utils import validate_slug

STEPS = ["diagnose", "prerequisites", "representations", "misconceptions", "recall", "summary"]
ADVANCEABLE_STEPS = ["prerequisites", "representations", "misconceptions", "recall"]

_ALLOWED_SOURCE_EXTS = {".md", ".txt"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_study_session(
    concept_id: str,
    source_relative_path: str | None = None,
    *,
    runs_dir: Path | None = None,
    sources_dir: Path | None = None,
    bank_root: Path | None = None,
    study_md_path: Path | None = None,
    data_root: Path | None = None,
) -> dict:
    """
    Create a study session by running the full 8-stage pipeline.

    Returns a dict matching CreateStudySessionResponse.
    """
    from gonghaebun.llm.mock import MockLLMClient
    from gonghaebun.pipeline.concept_resolver import ConceptNotFoundError, resolve_concept
    from gonghaebun.pipeline.io import save_questions
    from gonghaebun.pipeline.recall_orchestrator import convert_tasks_to_questions
    from gonghaebun.session import run_new_concept_session

    _runs_dir = runs_dir or config.RUNS_DIR
    _sources_dir = sources_dir or config.SOURCES_DIR
    _bank_root = bank_root or config.BANK_ROOT
    _study_md = study_md_path or config.STUDY_MD
    _data_root = data_root or config.DATA_ROOT

    # 1. Validate concept_id
    validate_slug(concept_id, field_name="concept_id")

    # 2. Resolve concept
    try:
        resolve_concept(concept_id)
    except ConceptNotFoundError:
        raise ConceptNotFoundError(concept_id)

    # 3. Resolve source file
    source_path = _resolve_source(source_relative_path, _data_root, _sources_dir)

    # 4. Generate session
    session_id = str(uuid4())
    output_dir = _runs_dir / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 5. Run full 8-stage pipeline
    llm = MockLLMClient()
    run_new_concept_session(
        concept_input=concept_id,
        source_path=source_path,
        llm=llm,
        output_dir=output_dir,
        study_md_path=_study_md,
        session_id=session_id,
    )

    # 6. Bank auto-preparation
    tasks_data: dict = json.loads((output_dir / "recall_tasks.json").read_text(encoding="utf-8"))
    rep_set_data: dict = json.loads((output_dir / "representation_set.json").read_text(encoding="utf-8"))

    questions = convert_tasks_to_questions(tasks_data, rep_set_data, concept_id)
    bank_dir = _bank_root / concept_id
    bank_dir.mkdir(parents=True, exist_ok=True)
    save_questions(bank_dir / "questions.generated.json", questions)
    shutil.copy2(bank_dir / "questions.generated.json", bank_dir / "questions.accepted.json")

    # 7. Read pipeline artifacts for response
    graph_data: dict = json.loads((output_dir / "prerequisite_graph.json").read_text(encoding="utf-8"))
    diagnosis_data: dict = json.loads((output_dir / "diagnosis.json").read_text(encoding="utf-8"))

    representations = _extract_representations(rep_set_data)
    prerequisites = _extract_prerequisites(graph_data, concept_id)
    misconceptions = _extract_misconceptions(diagnosis_data)

    # 8. Write study_session_state.json
    now = datetime.now(timezone.utc).isoformat()
    canonical_name_ko = KOREAN_NAMES.get(concept_id, concept_id)

    state = {
        "session_id": session_id,
        "session_type": "study",
        "concept_id": concept_id,
        "canonical_name_ko": canonical_name_ko,
        "current_step": 1,
        "steps": list(STEPS),
        "steps_completed": [],
        "diagnosis": None,
        "recall_completed": False,
        "self_explanations": None,
        "recall_session_id": None,
        "completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    _write_state(output_dir, state)

    return {
        "session_id": session_id,
        "concept_id": concept_id,
        "canonical_name_ko": canonical_name_ko,
        "current_step": 1,
        "steps": list(STEPS),
        "representations": representations,
        "prerequisites": prerequisites,
        "misconceptions": misconceptions,
    }


def get_study_session(session_id: str, runs_dir: Path | None = None) -> dict:
    """Load and return session state from study_session_state.json."""
    _runs_dir = runs_dir or config.RUNS_DIR
    state_path = _runs_dir / session_id / "study_session_state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"세션을 찾을 수 없습니다: {session_id}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def submit_diagnosis(
    session_id: str,
    prior_knowledge: str,
    gap_description: str,
    runs_dir: Path | None = None,
) -> dict:
    """Save diagnosis, compute deterministic mastery estimate, auto-advance to step 2."""
    _runs_dir = runs_dir or config.RUNS_DIR
    state = get_study_session(session_id, _runs_dir)

    # Already diagnosed?
    if state["diagnosis"] is not None:
        raise ValueError("이미 진단이 완료되었습니다")

    # Compute mastery estimate
    combined = f"{prior_knowledge} {gap_description}"
    if not prior_knowledge.strip() and not gap_description.strip():
        initial_mastery_estimate = "unknown"
    else:
        initial_mastery_estimate = "partial"

    # Identify gaps from GAP_CUES
    identified_gaps = []
    for cue, desc in GAP_CUES:
        if cue in combined:
            identified_gaps.append(desc)

    # Recommendation
    if initial_mastery_estimate == "unknown":
        recommendation = "정의(formal) 표현부터 시작하는 것을 권장합니다"
    else:
        recommendation = "취약 부분에 집중하여 학습하세요"

    # Update state
    diagnosis = {
        "prior_knowledge": prior_knowledge,
        "gap_description": gap_description,
        "initial_mastery_estimate": initial_mastery_estimate,
        "identified_gaps": identified_gaps,
        "recommendation": recommendation,
    }
    state["diagnosis"] = diagnosis
    if "diagnose" not in state["steps_completed"]:
        state["steps_completed"].append("diagnose")
    state["current_step"] = 2
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    _write_state(_runs_dir / session_id, state)

    return {
        "initial_mastery_estimate": initial_mastery_estimate,
        "identified_gaps": identified_gaps,
        "recommendation": recommendation,
    }


def advance_step(session_id: str, completed_step: str, runs_dir: Path | None = None) -> dict:
    """Mark a step complete and advance to next."""
    _runs_dir = runs_dir or config.RUNS_DIR
    state = get_study_session(session_id, _runs_dir)

    # Special handling for "diagnose"
    if completed_step == "diagnose":
        if "diagnose" in state["steps_completed"]:
            raise ValueError("이미 완료된 단계입니다: diagnose")
        else:
            raise ValueError("POST /api/study-session/{id}/diagnose를 먼저 호출하세요")

    # Validate step name
    if completed_step not in ADVANCEABLE_STEPS:
        raise ValueError(f"유효하지 않은 단계입니다: {completed_step}")

    # Check if at final step
    if state["current_step"] >= len(STEPS):
        raise ValueError("더 이상 진행할 단계가 없습니다")

    # Check step order
    expected = STEPS[state["current_step"] - 1]
    if completed_step != expected:
        raise ValueError(f"이전 단계를 먼저 완료해야 합니다: {expected}")

    # Advance
    if completed_step not in state["steps_completed"]:
        state["steps_completed"].append(completed_step)
    state["current_step"] = state["current_step"] + 1
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    _write_state(_runs_dir / session_id, state)

    current_step_name = STEPS[state["current_step"] - 1] if state["current_step"] <= len(STEPS) else "done"

    return {
        "current_step": state["current_step"],
        "current_step_name": current_step_name,
        "steps_completed": state["steps_completed"],
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_source(
    source_relative_path: str | None,
    data_root: Path,
    sources_dir: Path,
) -> Path:
    """Resolve source file path — explicit or auto-discover."""
    if source_relative_path:
        if not source_relative_path.startswith("sources/"):
            raise ValueError(
                f"source_relative_path must start with 'sources/'. Got: {source_relative_path!r}"
            )
        path = safe_resolve_under(data_root, source_relative_path)
        if not path.exists():
            raise ValueError(f"소스 파일을 찾을 수 없습니다: {source_relative_path!r}")
        return path

    # Auto-discover first source file
    if sources_dir.exists():
        for p in sorted(sources_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in _ALLOWED_SOURCE_EXTS:
                return p

    raise ValueError("소스 파일을 찾을 수 없습니다. 먼저 소스를 업로드하세요.")


def _extract_representations(rep_set_data: dict) -> dict[str, str]:
    """Extract {type: content} from representation_set.json."""
    result: dict[str, str] = {}
    if isinstance(rep_set_data, dict):
        for key, value in rep_set_data.items():
            if isinstance(value, dict) and "content" in value:
                result[key] = value["content"]
            elif isinstance(value, str):
                result[key] = value
    return result


def _extract_prerequisites(graph_data: dict, concept_id: str) -> list[dict]:
    """Extract prerequisite nodes (excluding root concept) from prerequisite_graph.json."""
    nodes = graph_data.get("nodes", [])
    prereqs = []
    for node in nodes:
        nid = node.get("concept_id", "")
        if nid and nid != concept_id:
            prereqs.append({
                "concept_id": nid,
                "name_ko": KOREAN_NAMES.get(nid, node.get("canonical_name", nid)),
                "mastery": node.get("mastery_state", "unknown"),
            })
    return prereqs


def _extract_misconceptions(diagnosis_data: dict) -> list[dict]:
    """Extract misconceptions from diagnosis.json."""
    raw = diagnosis_data.get("misconceptions", [])
    result = []
    for m in raw:
        result.append({
            "id": m.get("id", ""),
            "claim": m.get("claim", ""),
            "is_correct": m.get("is_correct", False),
        })
    return result


def _write_state(session_dir: Path, state: dict) -> None:
    """Write study_session_state.json."""
    path = session_dir / "study_session_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

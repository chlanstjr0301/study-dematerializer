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
VALID_REPRESENTATION_TYPES = {"formal", "intuitive", "visual", "counterexample", "proof_schema"}
REQUIRED_SELF_EXPLANATIONS = {"formal", "proof_schema"}

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
    from gonghaebun.llm.factory import get_llm_client
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
    llm = get_llm_client()
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


def submit_self_explanation(
    session_id: str,
    representation_type: str,
    learner_explanation: str,
    runs_dir: Path | None = None,
) -> dict:
    """Evaluate a self-explanation for one representation type."""
    from gonghaebun.llm.factory import get_llm_client
    from gonghaebun.pipeline.self_explanation import evaluate_self_explanation

    _runs_dir = runs_dir or config.RUNS_DIR
    state = get_study_session(session_id, _runs_dir)

    if state.get("completed"):
        raise ConflictError("이미 완료된 세션입니다")

    if representation_type not in VALID_REPRESENTATION_TYPES:
        raise ValueError(f"유효하지 않은 표현 유형입니다: {representation_type}")

    if not learner_explanation.strip():
        raise ValueError("자기 설명을 입력해 주세요")

    # Load target content from representation_set.json
    session_dir = _runs_dir / session_id
    rep_set_path = session_dir / "representation_set.json"
    rep_set_data: dict = json.loads(rep_set_path.read_text(encoding="utf-8"))
    representations = _extract_representations(rep_set_data)
    target_content = representations.get(representation_type, "")

    # Evaluate
    llm = get_llm_client()
    evaluation = evaluate_self_explanation(
        concept_id=state["concept_id"],
        representation_type=representation_type,
        target_content=target_content,
        learner_response=learner_explanation,
        llm=llm,
    )

    # Store in state
    if state["self_explanations"] is None:
        state["self_explanations"] = {}
    state["self_explanations"][representation_type] = {
        "learner_explanation": learner_explanation,
        "accuracy_score": evaluation.accuracy_score,
        "missing_elements": evaluation.missing_elements,
        "errors": evaluation.errors,
        "feedback": evaluation.feedback,
    }
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_state(session_dir, state)

    return {
        "representation_type": representation_type,
        "accuracy_score": evaluation.accuracy_score,
        "missing_elements": evaluation.missing_elements,
        "errors": evaluation.errors,
        "feedback": evaluation.feedback,
    }


def submit_recall(
    session_id: str,
    learner_response: str,
    runs_dir: Path | None = None,
) -> dict:
    """Evaluate White Recall submission."""
    from gonghaebun.llm.factory import get_llm_client
    from gonghaebun.pipeline.evaluation_schema import EVALUATION_OUTPUT_SCHEMA, validate_evaluation_output
    from gonghaebun.prompts import load_prompt

    _runs_dir = runs_dir or config.RUNS_DIR
    state = get_study_session(session_id, _runs_dir)

    if state.get("completed"):
        raise ConflictError("이미 완료된 세션입니다")

    if not learner_response.strip():
        raise ValueError("인출 응답을 입력해 주세요")

    # Load representation_set for combined target
    session_dir = _runs_dir / session_id
    rep_set_path = session_dir / "representation_set.json"
    rep_set_data: dict = json.loads(rep_set_path.read_text(encoding="utf-8"))
    representations = _extract_representations(rep_set_data)
    combined_target = "\n\n".join(
        f"[{k}] {v}" for k, v in representations.items()
    )

    # Evaluate using recall_eval fixture
    llm = get_llm_client()
    concept_id = state["concept_id"]
    system = load_prompt("global_system")
    stage5_prompt = load_prompt("stage5_self_explanation_evaluator")
    user = (
        f"{stage5_prompt}\n\n"
        f"## Concept\n{concept_id}\n\n"
        f"## Representation Type\nrecall_overall\n\n"
        f"## Target Content\n{combined_target}\n\n"
        f"## Learner Explanation\n{learner_response}\n\n"
        f"__fixture__:{concept_id}/recall_eval"
    )
    data = llm.complete_structured(system, user, EVALUATION_OUTPUT_SCHEMA)
    evaluation = validate_evaluation_output(data)

    # Store in state
    state["recall_evaluation"] = {
        "learner_response": learner_response,
        "accuracy_score": evaluation.accuracy_score,
        "missing_elements": evaluation.missing_elements,
        "errors": evaluation.errors,
        "feedback": evaluation.feedback,
    }
    state["recall_completed"] = True
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_state(session_dir, state)

    return {
        "accuracy_score": evaluation.accuracy_score,
        "missing_elements": evaluation.missing_elements,
        "errors": evaluation.errors,
        "feedback": evaluation.feedback,
    }


def complete_session(
    session_id: str,
    runs_dir: Path | None = None,
    study_md_path: Path | None = None,
) -> dict:
    """Mark session complete, compute mastery, update STUDY.md."""
    from gonghaebun.models.session_models import (
        MasteryUpdate,
        RecallAttempt,
        RecallEvaluation,
        StudySession,
    )
    from gonghaebun.study_md.writer import (
        apply_patch,
        compute_mastery_state,
        compute_next_review_date,
        generate_patch,
    )

    _runs_dir = runs_dir or config.RUNS_DIR
    _study_md = study_md_path or config.STUDY_MD
    state = get_study_session(session_id, _runs_dir)
    session_dir = _runs_dir / session_id

    # Idempotent: already completed → return existing result
    if state.get("completed"):
        return {
            "session_id": session_id,
            "completed": True,
            "mastery_updates": state.get("mastery_updates", []),
            "next_review_date": state.get("next_review_date", ""),
            "study_md_updated": state.get("study_md_updated", False),
            "study_patch_path": state.get("study_patch_path"),
            "completion_summary": _build_completion_summary(state),
        }

    # Completion conditions
    if not state.get("recall_completed"):
        raise ValueError("인출 연습을 먼저 완료해야 합니다")

    self_exps = state.get("self_explanations") or {}
    submitted_types = set(self_exps.keys())
    missing_required = REQUIRED_SELF_EXPLANATIONS - submitted_types
    if missing_required:
        raise ValueError("최소 formal, proof_schema 자기 설명을 완료해야 합니다")

    # Compute mastery updates
    concept_id = state["concept_id"]
    mastery_updates: list[dict] = []
    recall_attempts: list[RecallAttempt] = []
    mastery_update_objs: list[MasteryUpdate] = []

    for rep_type, exp_data in self_exps.items():
        score = exp_data["accuracy_score"]
        new_mastery = compute_mastery_state(score)
        mastery_updates.append({
            "representation_type": rep_type,
            "before": "unknown",
            "after": new_mastery,
            "accuracy_score": score,
        })
        # Build RecallAttempt for apply_patch
        recall_attempts.append(RecallAttempt(
            session_id=session_id,
            concept_id=concept_id,
            representation_type=rep_type,
            learner_response=exp_data.get("learner_explanation", ""),
            evaluation=RecallEvaluation(
                accuracy_score=score,
                missing_elements=exp_data.get("missing_elements", []),
                errors=exp_data.get("errors", []),
                feedback=exp_data.get("feedback", ""),
            ),
            attempted_at=state.get("updated_at", ""),
        ))

    # Compute overall mastery (weakest link including reps without self-explanation)
    all_masteries = []
    for rep_type in VALID_REPRESENTATION_TYPES:
        if rep_type in self_exps:
            all_masteries.append(compute_mastery_state(self_exps[rep_type]["accuracy_score"]))
        else:
            all_masteries.append("unknown")

    if "unknown" in all_masteries:
        overall = "unknown"
    elif "partial" in all_masteries:
        overall = "partial"
    else:
        overall = "solid"

    next_review = compute_next_review_date(overall)

    # Build MasteryUpdate objects for StudySession
    for mu in mastery_updates:
        mastery_update_objs.append(MasteryUpdate(
            concept_id=concept_id,
            representation_type=mu["representation_type"],
            before=mu["before"],
            after=mu["after"],
            next_review_date=next_review,
        ))

    # Build minimal StudySession for apply_patch
    now = datetime.now(timezone.utc).isoformat()
    study_session_obj = StudySession(
        session_id=session_id,
        session_type="new_concept",
        concept_ids=[concept_id],
        started_at=state.get("created_at", now),
        ended_at=now,
        llm_backend="mock",
        source_path="",
        source_hash="",
        grounding_mode="local_private_source",
        mastery_updates=mastery_update_objs,
        recall_attempts=recall_attempts,
    )

    # Write STUDY.patch.md (audit trail — always written, even if apply fails)
    patch_content = generate_patch(study_session_obj)
    patch_path = session_dir / "STUDY.patch.md"
    patch_path.write_text(patch_content, encoding="utf-8")

    # Save intermediate state (mastery computed but not yet completed)
    state["mastery_updates"] = mastery_updates
    state["next_review_date"] = next_review
    state["study_patch_path"] = f"runs/{session_id}/STUDY.patch.md"
    state["updated_at"] = now
    _write_state(session_dir, state)

    # Apply to STUDY.md — failure prevents completion
    try:
        apply_patch(_study_md, study_session_obj)
    except Exception as e:
        raise StudyMdUpdateError(f"STUDY.md 업데이트에 실패했습니다: {e}") from e

    # Only mark completed after successful STUDY.md update
    state["completed"] = True
    state["completed_at"] = now
    state["study_md_updated"] = True
    state["updated_at"] = now
    _write_state(session_dir, state)

    return {
        "session_id": session_id,
        "completed": True,
        "mastery_updates": mastery_updates,
        "next_review_date": next_review,
        "study_md_updated": True,
        "study_patch_path": state["study_patch_path"],
        "completion_summary": _build_completion_summary(state),
    }


class ConflictError(Exception):
    """Raised when an operation conflicts with current session state."""
    pass


class StudyMdUpdateError(Exception):
    """Raised when STUDY.md update fails during session completion."""
    pass


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_completion_summary(state: dict) -> str:
    """Build Korean completion summary text."""
    concept_name = state.get("canonical_name_ko", state.get("concept_id", ""))
    mastery_updates = state.get("mastery_updates", [])
    next_review = state.get("next_review_date", "미정")

    updated_reps = len(mastery_updates)
    summary = f"{concept_name} 학습 세션이 완료되었습니다. "
    if updated_reps > 0:
        summary += f"{updated_reps}개 표현의 숙련도가 업데이트되었습니다. "
    summary += f"다음 복습일: {next_review}"
    return summary


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

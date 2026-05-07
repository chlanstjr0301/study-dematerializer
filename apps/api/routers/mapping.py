"""
Router: Mapping Tasks + Confusion Map — MVP6.

Exposes endpoints for retrieving mapping tasks, submitting mapping answers,
and reading the confusion map for a study session.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

import apps.api.config as config
from apps.api.schemas.api_schemas import (
    ConfusionMapResponse,
    MappingSubmitRequest,
    MappingSubmitResponse,
    MappingTaskItem,
    MappingTasksResponse,
)
from apps.api.services.card_service import CardNotFoundError, load_ground_truth_card, load_rubric
from apps.api.services.confusion_map_service import (
    initialize_confusion_map,
    load_confusion_map,
    persist_confusion_map,
)
from apps.api.services.mapping_service import (
    evaluate_mapping_submission,
    generate_mapping_tasks,
    update_confusion_map_from_mapping,
)

router = APIRouter(tags=["mapping"])

_MAPPING_TASKS_FILE = "mapping_tasks.json"
_MAPPING_RESULTS_FILE = "mapping_results.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_session_state(session_id: str) -> tuple[dict, Path]:
    """Load session state and return (state_dict, session_dir).

    Raises HTTPException 404 if session not found.
    """
    session_dir = config.RUNS_DIR / session_id
    state_path = session_dir / "study_session_state.json"
    if not state_path.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return state, session_dir


def _write_state(session_dir: Path, state: dict) -> None:
    path = session_dir / "study_session_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _cmap_to_response(cmap) -> ConfusionMapResponse:
    """Convert a ConfusionMap model to the API response schema."""
    return ConfusionMapResponse(
        concept_id=cmap.concept_id,
        session_id=cmap.session_id,
        prerequisite_nodes=[
            {"concept_id": n.concept_id, "mastery": n.mastery, "self_reported": n.self_reported}
            for n in cmap.prerequisite_nodes
        ],
        mapping_edges=[
            {
                "from_rep": e.from_rep,
                "to_rep": e.to_rep,
                "task_type": e.task_type,
                "passed": e.passed,
                "score": e.score,
            }
            for e in cmap.mapping_edges
        ],
        misconception_tags=list(cmap.misconception_tags),
        next_recall_triggers=list(cmap.next_recall_triggers),
        evidence_snippets=[
            {
                "step": s.step,
                "task_type": s.task_type,
                "learner_text": s.learner_text,
                "issue": s.issue,
            }
            for s in cmap.evidence_snippets
        ],
        last_updated_step=cmap.last_updated_step,
    )


# ---------------------------------------------------------------------------
# GET /api/study-session/{session_id}/mapping-tasks
# ---------------------------------------------------------------------------


@router.get("/study-session/{session_id}/mapping-tasks", response_model=MappingTasksResponse)
def get_mapping_tasks(session_id: str):
    state, session_dir = _load_session_state(session_id)
    concept_id = state["concept_id"]

    # Try to load tasks from disk first
    tasks_path = session_dir / _MAPPING_TASKS_FILE
    if tasks_path.exists():
        from gonghaebun.models.mapping_models import MappingTask
        raw = json.loads(tasks_path.read_text(encoding="utf-8"))
        tasks = [MappingTask.model_validate(t) for t in raw]
    else:
        # Generate from card (lazy generation)
        try:
            card = load_ground_truth_card(concept_id, use_cache=True)
        except CardNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Ground truth card not found for concept {concept_id}",
            )
        tasks = generate_mapping_tasks(session_id, concept_id, card)
        # Persist for future loads
        session_dir.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text(
            json.dumps([t.model_dump() for t in tasks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return MappingTasksResponse(
        session_id=session_id,
        concept_id=concept_id,
        tasks=[
            MappingTaskItem(
                task_id=t.task_id,
                task_type=t.task_type.value if hasattr(t.task_type, "value") else str(t.task_type),
                prompt=t.prompt,
                source_representations=t.source_representations,
                target_representation=t.target_representation,
            )
            for t in tasks
        ],
    )


# ---------------------------------------------------------------------------
# POST /api/study-session/{session_id}/mapping-submit
# ---------------------------------------------------------------------------


@router.post("/study-session/{session_id}/mapping-submit", response_model=MappingSubmitResponse)
def submit_mapping(session_id: str, req: MappingSubmitRequest):
    # Validate request
    if not req.learner_response.strip():
        raise HTTPException(status_code=422, detail="learner_response must not be empty")

    state, session_dir = _load_session_state(session_id)
    concept_id = state["concept_id"]

    # Load tasks
    tasks_path = session_dir / _MAPPING_TASKS_FILE
    if not tasks_path.exists():
        raise HTTPException(status_code=400, detail="Mapping tasks not yet generated for this session")

    from gonghaebun.models.mapping_models import MappingTask
    raw_tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    tasks = [MappingTask.model_validate(t) for t in raw_tasks]

    # Find the target task
    task = next((t for t in tasks if t.task_id == req.task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {req.task_id} not found in session")

    # Check if task already submitted
    results_path = session_dir / _MAPPING_RESULTS_FILE
    existing_results: list[dict] = []
    if results_path.exists():
        existing_results = json.loads(results_path.read_text(encoding="utf-8"))
    if any(r["task_id"] == req.task_id for r in existing_results):
        raise HTTPException(status_code=400, detail=f"Task {req.task_id} already submitted")

    # Load card + rubric
    try:
        card = load_ground_truth_card(concept_id, use_cache=True)
    except CardNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Ground truth card not found for concept {concept_id}",
        )
    try:
        rubric = load_rubric(concept_id, use_cache=True)
    except CardNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Rubric not found for concept {concept_id}",
        )

    # Evaluate
    result = evaluate_mapping_submission(task, req.learner_response, card, rubric)

    # Persist result
    existing_results.append(result.model_dump(mode="json"))
    results_path.write_text(
        json.dumps(existing_results, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # Update confusion map
    cmap = load_confusion_map(session_dir)
    if cmap is None:
        cmap = initialize_confusion_map(session_id, concept_id, card)
    cmap = update_confusion_map_from_mapping(cmap, result)
    persist_confusion_map(cmap, session_dir)

    task_type_str = result.task_type.value if hasattr(result.task_type, "value") else str(result.task_type)

    return MappingSubmitResponse(
        task_id=result.task_id,
        task_type=task_type_str,
        score=result.score,
        passed=result.passed,
        missing_elements=result.missing_elements,
        misconception_tags=result.misconception_tags,
        mapping_failures=result.mapping_failures,
        feedback=result.feedback,
        next_recall_trigger=result.next_recall_trigger,
        confusion_map=_cmap_to_response(cmap),
    )


# ---------------------------------------------------------------------------
# GET /api/study-session/{session_id}/confusion-map
# ---------------------------------------------------------------------------


@router.get("/study-session/{session_id}/confusion-map", response_model=ConfusionMapResponse)
def get_confusion_map(session_id: str):
    state, session_dir = _load_session_state(session_id)
    concept_id = state["concept_id"]

    cmap = load_confusion_map(session_dir)
    if cmap is None:
        # Return an empty/initialized confusion map
        try:
            card = load_ground_truth_card(concept_id, use_cache=True)
        except CardNotFoundError:
            # No card available — return minimal empty map
            return ConfusionMapResponse(
                concept_id=concept_id,
                session_id=session_id,
                prerequisite_nodes=[],
                mapping_edges=[],
                misconception_tags=[],
                next_recall_triggers=[],
                evidence_snippets=[],
                last_updated_step="init",
            )
        cmap = initialize_confusion_map(session_id, concept_id, card)

    return _cmap_to_response(cmap)

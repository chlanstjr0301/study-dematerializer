"""
Router: Study Session — create, get, diagnose, advance, self-explain, recall, complete.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from gonghaebun.llm.errors import LLMError, LLMResponseError

from apps.api.schemas.api_schemas import (
    AdvanceStepRequest,
    AdvanceStepResponse,
    CompleteStudySessionResponse,
    CreateStudySessionRequest,
    CreateStudySessionResponse,
    DiagnoseRequest,
    DiagnoseResponse,
    RecallSubmitRequest,
    RecallSubmitResponse,
    SelfExplainRequest,
    SelfExplainResponse,
    StudySessionStateResponse,
)
from apps.api.services import study_session_service as svc
from apps.api.services.study_session_service import ConflictError, StudyMdUpdateError

router = APIRouter()


@router.post("/study-session", response_model=CreateStudySessionResponse, status_code=201)
def create_study_session(req: CreateStudySessionRequest):
    from gonghaebun.pipeline.concept_resolver import ConceptNotFoundError

    try:
        result = svc.create_study_session(
            concept_id=req.concept_id,
            source_relative_path=req.source_relative_path,
        )
    except ConceptNotFoundError:
        raise HTTPException(status_code=422, detail=f"지원하지 않는 개념입니다: {req.concept_id}")
    except ValueError as e:
        msg = str(e)
        if "소스 파일을 찾을 수 없습니다" in msg:
            raise HTTPException(status_code=422, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 중 오류가 발생했습니다: {e}")
    return CreateStudySessionResponse(**result)


@router.get("/study-session/{session_id}", response_model=StudySessionStateResponse)
def get_study_session(session_id: str):
    try:
        state = svc.get_study_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    # Ensure fields are present for older/legacy sessions
    state.setdefault("confusion_map_initialized", False)
    state.setdefault("steps", list(svc.STEPS))
    return StudySessionStateResponse(**state)


@router.post("/study-session/{session_id}/diagnose", response_model=DiagnoseResponse)
def diagnose(session_id: str, req: DiagnoseRequest):
    try:
        result = svc.submit_diagnosis(
            session_id=session_id,
            prior_knowledge=req.prior_knowledge,
            gap_description=req.gap_description,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    except ValueError as e:
        msg = str(e)
        if "이미 진단이 완료되었습니다" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return DiagnoseResponse(**result)


@router.post("/study-session/{session_id}/advance", response_model=AdvanceStepResponse)
def advance_step(session_id: str, req: AdvanceStepRequest):
    try:
        result = svc.advance_step(
            session_id=session_id,
            completed_step=req.completed_step,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    except ValueError as e:
        msg = str(e)
        if "이미 완료된 단계입니다" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return AdvanceStepResponse(**result)


@router.post("/study-session/{session_id}/self-explain", response_model=SelfExplainResponse)
def self_explain(session_id: str, req: SelfExplainRequest):
    try:
        result = svc.submit_self_explanation(
            session_id=session_id,
            representation_type=req.representation_type,
            learner_explanation=req.learner_explanation,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (LLMResponseError, LLMError) as e:
        raise HTTPException(status_code=502, detail=f"LLM 평가 응답이 유효하지 않습니다: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SelfExplainResponse(**result)


@router.post("/study-session/{session_id}/recall", response_model=RecallSubmitResponse)
def recall_submit(session_id: str, req: RecallSubmitRequest):
    try:
        result = svc.submit_recall(
            session_id=session_id,
            learner_response=req.learner_response,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (LLMResponseError, LLMError) as e:
        raise HTTPException(status_code=502, detail=f"LLM 평가 응답이 유효하지 않습니다: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RecallSubmitResponse(**result)


@router.post("/study-session/{session_id}/complete", response_model=CompleteStudySessionResponse)
def complete_session(session_id: str):
    try:
        result = svc.complete_session(session_id=session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except StudyMdUpdateError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CompleteStudySessionResponse(**result)

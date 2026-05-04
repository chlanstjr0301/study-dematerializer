from fastapi import APIRouter, HTTPException
from apps.api.schemas.api_schemas import (
    RunSessionRequest,
    RunSessionResponse,
    SessionResponse,
    SessionSummaryItem,
    SummaryResponse,
)
from apps.api.services import session_service

router = APIRouter()


@router.get("/sessions", response_model=list[SessionSummaryItem])
def list_sessions() -> list[SessionSummaryItem]:
    items = session_service.list_sessions()
    return [SessionSummaryItem(**item) for item in items]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    try:
        data = session_service.get_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SessionResponse(**data)


@router.get("/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    try:
        content = session_service.get_summary(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SummaryResponse(content=content)


@router.post("/sessions", response_model=RunSessionResponse, status_code=201)
def run_session(req: RunSessionRequest) -> RunSessionResponse:
    try:
        result = session_service.run_session(req)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RunSessionResponse(**result)

"""
Router: chat-based concept analyzer — POST /compiler/analyze.
"""
from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
from apps.api.services import compiler_analyzer_service

router = APIRouter()


@router.post("/compiler/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    result = compiler_analyzer_service.analyze_message(
        message=req.message,
        source_id=req.source_id,
        recent_messages=req.recent_messages,
    )
    return AnalyzeResponse(**result)

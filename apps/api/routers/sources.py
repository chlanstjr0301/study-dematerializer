"""
Router: source file endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from apps.api.schemas.api_schemas import SourceItem, UploadSourceResponse
from apps.api.services import source_service

router = APIRouter()


@router.get("/sources", response_model=list[SourceItem])
def list_sources() -> list[SourceItem]:
    return [SourceItem(**s) for s in source_service.list_sources()]


@router.post("/sources/upload", response_model=UploadSourceResponse, status_code=201)
async def upload_source(
    file: UploadFile = File(...),
    concept_id: str = Form(...),
    document_id: str | None = Form(None),
) -> UploadSourceResponse:
    try:
        data = await file.read()
        result = source_service.save_source(
            data, file.filename or "upload.md", concept_id, document_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return UploadSourceResponse(**result)

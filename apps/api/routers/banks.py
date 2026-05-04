"""
Router: bank build, review, and export endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.api_schemas import (
    BuildBankRequest,
    BuildBankResponse,
    ExportAcceptedResponse,
    GeneratedQuestionItem,
    ReviewBankRequest,
    ReviewBankResponse,
)
from apps.api.services import banks_service

router = APIRouter()


# Static route BEFORE parameterized routes to avoid routing conflict
@router.post("/banks/build", response_model=BuildBankResponse, status_code=201)
def build_bank(req: BuildBankRequest) -> BuildBankResponse:
    try:
        result = banks_service.build_bank(
            req.concept_id, req.source_relative_path, req.document_id
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return BuildBankResponse(**result)


@router.get("/banks/{concept_id}/generated", response_model=list[GeneratedQuestionItem])
def get_generated_bank(concept_id: str) -> list[GeneratedQuestionItem]:
    try:
        qs = banks_service.get_generated_questions(concept_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [GeneratedQuestionItem(**q) for q in qs]


@router.get("/banks/{concept_id}/accepted", response_model=list[GeneratedQuestionItem])
def get_accepted_bank(concept_id: str) -> list[GeneratedQuestionItem]:
    try:
        qs = banks_service.get_accepted_questions(concept_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [GeneratedQuestionItem(**q) for q in qs]


@router.post("/banks/{concept_id}/review", response_model=ReviewBankResponse)
def review_bank(concept_id: str, req: ReviewBankRequest) -> ReviewBankResponse:
    try:
        result = banks_service.review_bank(
            concept_id,
            [a.model_dump() for a in req.actions],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ReviewBankResponse(**result)


@router.post("/banks/{concept_id}/export-accepted", response_model=ExportAcceptedResponse)
def export_accepted(concept_id: str) -> ExportAcceptedResponse:
    try:
        result = banks_service.export_accepted_questions(concept_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ExportAcceptedResponse(**result)

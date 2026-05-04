"""
Router: concept compiler — list concepts and run the full 8-stage compiler.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.api_schemas import (
    CompileConceptRequest,
    CompileConceptResponse,
    ConceptItem,
)
from apps.api.services import concept_service
from gonghaebun.pipeline.concept_resolver import ConceptNotFoundError

router = APIRouter()


@router.get("/concepts", response_model=list[ConceptItem])
def list_concepts() -> list[ConceptItem]:
    return [ConceptItem(**c) for c in concept_service.list_concepts()]


@router.post("/concepts/{concept_id}/compile", response_model=CompileConceptResponse, status_code=201)
def compile_concept(concept_id: str, req: CompileConceptRequest) -> CompileConceptResponse:
    try:
        result = concept_service.compile_concept(
            concept_id=concept_id,
            source_relative_path=req.source_relative_path,
            document_id=req.document_id,
            grader=req.grader,
        )
    except ConceptNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CompileConceptResponse(**result)

from fastapi import APIRouter
from apps.api.schemas.api_schemas import DueConceptItem, StudyMdResponse, WeakRepItem
from apps.api.services import study_md_service

router = APIRouter()


@router.get("/due", response_model=list[DueConceptItem])
def get_due() -> list[DueConceptItem]:
    items = study_md_service.get_due()
    return [DueConceptItem(**item) for item in items]


@router.get("/study-md", response_model=StudyMdResponse)
def get_study_md() -> StudyMdResponse:
    content = study_md_service.read_study_md()
    return StudyMdResponse(content=content)


@router.get("/weak", response_model=list[WeakRepItem])
def get_weak() -> list[WeakRepItem]:
    items = study_md_service.get_weak_representations()
    return [WeakRepItem(**item) for item in items]

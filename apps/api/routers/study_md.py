from fastapi import APIRouter
from apps.api.schemas.api_schemas import DueConceptItem, StudyMdResponse
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

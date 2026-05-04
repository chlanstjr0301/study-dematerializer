from fastapi import APIRouter, HTTPException
from apps.api.schemas.api_schemas import BankSummaryItem, QuestionItem
from apps.api.services import bank_service

router = APIRouter()


@router.get("/bank", response_model=list[BankSummaryItem])
def list_banks() -> list[BankSummaryItem]:
    items = bank_service.list_banks()
    return [BankSummaryItem(**item) for item in items]


@router.get("/bank/{concept_id}", response_model=list[QuestionItem])
def get_bank(concept_id: str) -> list[QuestionItem]:
    try:
        questions = bank_service.load_bank(concept_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [
        QuestionItem(
            id=q["question_id"],
            question=q["question"],
            question_type=q["question_type"],
            expected_answer=q["expected_answer"],
            status=q.get("status", ""),
        )
        for q in questions
    ]

"""
Evaluation output schema for self-explanation and recall evaluation.

Used with LLMClient.complete_structured() for provider-level JSON schema enforcement.
validate_evaluation_output() provides a second local validation layer.
"""
from __future__ import annotations

from gonghaebun.llm.errors import LLMResponseError
from gonghaebun.models.session_models import RecallEvaluation

# JSON Schema for OpenAI structured output enforcement.
EVALUATION_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "accuracy_score": {"type": "number"},
        "missing_elements": {"type": "array", "items": {"type": "string"}},
        "errors": {"type": "array", "items": {"type": "string"}},
        "feedback": {"type": "string"},
    },
    "required": ["accuracy_score", "missing_elements", "errors", "feedback"],
    "additionalProperties": False,
}


def validate_evaluation_output(data: dict) -> RecallEvaluation:
    """
    Validate a raw dict against the evaluation schema.

    Raises LLMResponseError on any violation.
    Returns a validated RecallEvaluation on success.
    """
    required = ["accuracy_score", "missing_elements", "errors", "feedback"]
    for key in required:
        if key not in data:
            raise LLMResponseError(f"평가 응답에 필수 필드가 없습니다: {key!r}")

    # Reject extra fields (strict policy matching additionalProperties: false)
    allowed = set(required)
    extra = set(data.keys()) - allowed
    if extra:
        raise LLMResponseError(
            f"평가 응답에 허용되지 않는 필드가 있습니다: {sorted(extra)}"
        )

    # accuracy_score: number in [0.0, 1.0]
    accuracy = data["accuracy_score"]
    if not isinstance(accuracy, (int, float)):
        raise LLMResponseError(
            f"accuracy_score는 숫자여야 합니다. 받은 타입: {type(accuracy).__name__}"
        )
    if not 0.0 <= float(accuracy) <= 1.0:
        raise LLMResponseError(
            f"accuracy_score는 0.0~1.0 범위여야 합니다. 받은 값: {accuracy!r}"
        )

    # missing_elements: list[str]
    _validate_string_list(data["missing_elements"], "missing_elements")

    # errors: list[str]
    _validate_string_list(data["errors"], "errors")

    # feedback: str (empty allowed)
    if not isinstance(data["feedback"], str):
        raise LLMResponseError(
            f"feedback는 문자열이어야 합니다. 받은 타입: {type(data['feedback']).__name__}"
        )

    return RecallEvaluation(
        accuracy_score=float(data["accuracy_score"]),
        missing_elements=list(data["missing_elements"]),
        errors=list(data["errors"]),
        feedback=str(data["feedback"]),
    )


def _validate_string_list(value: object, field_name: str) -> None:
    """Validate that value is a list of strings."""
    if not isinstance(value, list):
        raise LLMResponseError(
            f"{field_name}은(는) 문자열 리스트여야 합니다. 받은 타입: {type(value).__name__}"
        )
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise LLMResponseError(
                f"{field_name}[{i}]은(는) 문자열이어야 합니다. 받은 타입: {type(item).__name__}"
            )

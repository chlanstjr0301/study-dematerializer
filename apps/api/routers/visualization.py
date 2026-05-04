from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from apps.api.services import session_service

router = APIRouter()

_VALID_ARTIFACTS = {
    "mastery_map", "recall_feedback", "review_queue",
    "mastery_map_mmd", "session_flow_mmd",
}


@router.get("/sessions/{session_id}/visualization/{artifact}")
def get_visualization(session_id: str, artifact: str):
    if artifact not in _VALID_ARTIFACTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown artifact {artifact!r}. Valid: {sorted(_VALID_ARTIFACTS)}",
        )
    try:
        content = session_service.get_viz(session_id, artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if artifact.endswith("_mmd"):
        return PlainTextResponse(content=content)
    return JSONResponse(content=content)

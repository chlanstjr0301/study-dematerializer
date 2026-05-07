import os

from fastapi import APIRouter

import apps.api.config as config
from apps.api.schemas.api_schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    checks: dict[str, str] = {}

    # 1. data_dir
    try:
        config.DATA_ROOT.mkdir(parents=True, exist_ok=True)
        checks["data_dir"] = "ok"
    except Exception as exc:
        checks["data_dir"] = f"error: {exc}"

    # 2. study_md
    if config.STUDY_MD.exists():
        try:
            from gonghaebun.study_md.writer import validate_study_md
            validate_study_md(config.STUDY_MD)
            checks["study_md"] = "ok"
        except Exception as exc:
            checks["study_md"] = f"invalid: {exc}"
    else:
        checks["study_md"] = "missing"

    # 3. llm (informational; does not block readiness)
    if config.LLM_DISABLED:
        checks["llm"] = "disabled"
    elif os.environ.get("OPENAI_API_KEY"):
        checks["llm"] = "enabled"
    else:
        checks["llm"] = "no_api_key"

    is_ready = (
        checks["data_dir"] == "ok"
        and checks["study_md"] in ("ok", "missing")
    )

    # Determine default grader: "llm" when LLM is enabled + API key present
    if not config.LLM_DISABLED and os.environ.get("OPENAI_API_KEY"):
        default_grader = "llm"
    else:
        default_grader = "mock"

    return ReadyResponse(ready=is_ready, checks=checks, default_grader=default_grader)

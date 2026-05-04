"""
Router: project bootstrap endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.schemas.api_schemas import BootstrapResponse, ProjectStatus
from apps.api.services import project_service

router = APIRouter()


@router.get("/project/status", response_model=ProjectStatus)
def get_project_status() -> ProjectStatus:
    return ProjectStatus(**project_service.get_status())


@router.post("/project/bootstrap", response_model=BootstrapResponse)
def bootstrap_project(overwrite: bool = Query(False)) -> BootstrapResponse:
    return BootstrapResponse(**project_service.bootstrap(overwrite=overwrite))

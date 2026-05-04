"""
Gonghaebun API — FastAPI application factory.

Run with:
    uvicorn apps.api.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import bank, banks, concepts, health, project, sessions, sources, study_md, visualization


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gonghaebun API",
        description="Local study compiler API — single-user, localhost only.",
        version="0.4.0",
    )

    # Allow the Vite dev server (localhost:5173) to reach the API.
    # No public CORS — only localhost origins are permitted.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(project.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")
    app.include_router(banks.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(study_md.router, prefix="/api")
    app.include_router(bank.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(visualization.router, prefix="/api")
    app.include_router(concepts.router, prefix="/api")

    return app


app = create_app()

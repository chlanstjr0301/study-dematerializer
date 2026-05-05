"""
Gonghaebun API — FastAPI application factory.

Run with:
    uvicorn apps.api.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import apps.api.config as config
from apps.api.routers import bank, banks, concepts, health, project, sessions, sources, study_md, visualization

# Module-level so tests can monkeypatch before calling create_app()
_DIST = Path(__file__).parent.parent / "web" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gonghaebun API",
        description="Local study compiler API — single-user, localhost only.",
        version="0.4.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
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

    if config.SERVE_FRONTEND:
        dist = _DIST  # capture module-level var for closure (testable via monkeypatch)
        if dist.exists():
            _assets = dist / "assets"
            if _assets.is_dir():
                from fastapi.staticfiles import StaticFiles
                app.mount("/assets", StaticFiles(directory=_assets), name="assets")

            # SPA catch-all: registered LAST so all /api/* routes take priority
            from fastapi import HTTPException as _HTTPException
            from fastapi.responses import FileResponse

            @app.get("/{full_path:path}", include_in_schema=False)
            async def spa_fallback(full_path: str):
                # Explicitly reject unknown /api/* paths — never serve SPA HTML for API routes
                if full_path == "api" or full_path.startswith("api/"):
                    raise _HTTPException(status_code=404, detail="API route not found")
                # Serve actual static files (favicon.ico, vite.svg, etc.)
                file_path = dist / full_path
                if file_path.is_file():
                    return FileResponse(str(file_path))
                # SPA fallback: all other paths → index.html
                index = dist / "index.html"
                if not index.exists():
                    raise _HTTPException(
                        status_code=404,
                        detail="Frontend not built. Run: cd apps/web && npm run build",
                    )
                return FileResponse(str(index))

    return app


app = create_app()

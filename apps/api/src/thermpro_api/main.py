"""ThermPro FastAPI application entry point."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from thermpro_api.routers import (
    artifacts,
    calculation_runs,
    dataset_manifests,
    geometry,
    health,
    library_entries,
    library_releases,
    projects,
)
from thermpro_api.settings import get_settings

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "ThermPro LV Switchboard Thermal Digital Twin — API server.\n\n"
            "Milestone 1: Platform foundation. Thermal solver not yet implemented.\n"
            "All calculation submissions return ENGINE_NOT_IMPLEMENTED."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — dev permissive; tighten for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    api_v1_prefix = "/api/v1"
    app.include_router(health.router, prefix=api_v1_prefix)
    app.include_router(projects.router, prefix=api_v1_prefix)
    app.include_router(library_releases.router, prefix=api_v1_prefix)
    app.include_router(dataset_manifests.router, prefix=api_v1_prefix)
    app.include_router(calculation_runs.router, prefix=api_v1_prefix)
    app.include_router(artifacts.router, prefix=api_v1_prefix)
    app.include_router(geometry.router, prefix=api_v1_prefix)
    app.include_router(library_entries.router, prefix=api_v1_prefix)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "thermpro_api.startup",
            version=settings.app_version,
            debug=settings.debug,
            dev_auth=settings.dev_auth_enabled,
        )

    return app


app = create_app()

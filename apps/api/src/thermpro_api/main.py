"""ThermPro FastAPI application entry point."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from thermal_core.contract import ENGINE_VERSION

from thermpro_api.routers import (
    artifacts,
    calculation_runs,
    dataset_manifests,
    geometry,
    health,
    iec60890,
    library_entries,
    library_releases,
    projects,
)
from thermpro_api.settings import get_settings

logger = structlog.get_logger()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application startup and shutdown.

    A lifespan context, not the deprecated @app.on_event hooks, so that the
    shutdown half has somewhere to live when there is work to do there.
    """
    settings = get_settings()
    logger.info(
        "thermpro_api.startup",
        version=settings.app_version,
        debug=settings.debug,
        dev_auth=settings.dev_auth_enabled,
        engine_version=ENGINE_VERSION,
    )
    yield
    logger.info("thermpro_api.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "ThermPro LV Switchboard Thermal Digital Twin — API server.\n\n"
            "Submit an M0-03 InputSnapshot, execute it, and retrieve the M0-04 "
            "ResultSnapshot verbatim.\n\n"
            "MODE 1 (IEC TR 60890) requires the licensed coefficient dataset, "
            "which is never shipped in this repository (CR-ENG-002); an "
            "administrator imports it through /iec60890-datasets."
        ),
        lifespan=_lifespan,
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
    app.include_router(iec60890.router, prefix=api_v1_prefix)

    return app


app = create_app()

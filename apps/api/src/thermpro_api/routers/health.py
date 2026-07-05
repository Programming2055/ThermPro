"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from thermpro_api.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic liveness probe — returns 200 if the process is running."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        service=settings.app_name,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """
    Readiness probe.

    In M1 we do not check database connectivity here to avoid coupling
    the Docker healthcheck to the DB startup race. Full dependency checks
    are added in M2 once the integration suite is established.
    """
    return ReadyResponse(
        status="ready",
        checks={"engine": "not_implemented_m1", "db": "unchecked_m1"},
    )

"""Calculation run endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.calculation_run import CalculationRun as CalculationRunModel
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.calculation import CalculationService, CalculationSubmissionError

router = APIRouter(prefix="/calculation-runs", tags=["calculation-runs"])

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class CalculationRunSubmit(BaseModel):
    project_id: uuid.UUID
    input_snapshot: dict[str, Any]


class CalculationRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    mode: str
    schema_version: str
    status: str
    input_checksum_sha256: str
    rejection_reason: str | None
    submitted_at: str | None
    completed_at: str | None

    model_config = {"from_attributes": True}


@router.post("", response_model=CalculationRunResponse, status_code=status.HTTP_201_CREATED)
async def submit_calculation(
    body: CalculationRunSubmit,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalculationRunResponse:
    """
    Submit a calculation run.

    The input_snapshot is validated against M0-03 JSON Schema and the
    library manifest is verified. The run is stored immutably with status
    ENGINE_NOT_IMPLEMENTED (M1).
    """
    svc = CalculationService(db)
    try:
        run = await svc.submit(
            input_snapshot=body.input_snapshot,
            project_id=body.project_id,
            actor=current_user,
        )
    except CalculationSubmissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "errors": exc.details},
        ) from exc
    await db.commit()
    await db.refresh(run)
    return CalculationRunResponse.model_validate(run)


@router.get("", response_model=PaginatedResponse[CalculationRunResponse])
async def list_calculation_runs(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = None,
    run_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[CalculationRunResponse]:
    """List calculation runs with optional filters (paginated)."""
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(CalculationRunModel))
    total = total_result.scalar_one()
    svc = CalculationService(db)
    runs = await svc.list_runs(
        project_id=project_id,
        status=run_status,
        limit=page_size,
        offset=offset,
    )
    return PaginatedResponse(
        items=[CalculationRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=CalculationRunResponse)
async def get_calculation_run(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalculationRunResponse:
    """Retrieve a calculation run by ID."""
    svc = CalculationService(db)
    run = await svc.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="CalculationRun not found.")
    return CalculationRunResponse.model_validate(run)

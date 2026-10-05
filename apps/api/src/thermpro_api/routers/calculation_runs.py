"""Calculation run endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.calculation_run import CalculationRun
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.calculation import (
    CalculationExecutionError,
    CalculationService,
    CalculationSubmissionError,
)

router = APIRouter(prefix="/calculation-runs", tags=["calculation-runs"])



class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class CalculationRunSubmit(BaseModel):
    project_id: uuid.UUID
    input_snapshot: dict[str, Any]
    #: Solve immediately instead of leaving the run PENDING. Convenient for
    #: the small models the UI submits; a long study should queue instead.
    execute: bool = False


class CalculationRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    mode: str
    schema_version: str
    status: str
    input_checksum_sha256: str
    rejection_reason: str | None
    submitted_at: str | None
    started_at: str | None
    completed_at: str | None
    engine_version: str | None
    result_checksum_sha256: str | None
    #: True once a ResultSnapshot has been stored, so a client can tell a
    #: queued run from one whose result it can fetch.
    has_result: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def of(cls, run: CalculationRun) -> CalculationRunResponse:
        response = cls.model_validate(run)
        return response.model_copy(
            update={"has_result": run.result_snapshot is not None}
        )


@router.post("", response_model=CalculationRunResponse, status_code=status.HTTP_201_CREATED)
async def submit_calculation(
    body: CalculationRunSubmit,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalculationRunResponse:
    """
    Submit a calculation run.

    The input_snapshot is validated against M0-03 JSON Schema and the
    library manifest is verified, then stored immutably with status PENDING.

    Submitting does not solve. POST to `/{run_id}/execute` to run the engine,
    or pass `execute=true` to do both in one request.
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

    if body.execute:
        try:
            await svc.execute(run, current_user)
        except CalculationExecutionError as exc:
            # The run itself is kept: a rejected input is part of the record.
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": str(exc), "errors": exc.details},
            ) from exc

    await db.commit()
    await db.refresh(run)
    return CalculationRunResponse.of(run)


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
    svc = CalculationService(db)
    # The total counts what the filters select, not every run in the
    # database: a page count that ignores the filter is simply wrong.
    total = await svc.count_runs(project_id=project_id, status=run_status)
    runs = await svc.list_runs(
        project_id=project_id,
        status=run_status,
        limit=page_size,
        offset=offset,
    )
    return PaginatedResponse(
        items=[CalculationRunResponse.of(r) for r in runs],
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
    return CalculationRunResponse.of(run)


@router.post("/{run_id}/execute", response_model=CalculationRunResponse)
async def execute_calculation_run(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CalculationRunResponse:
    """
    Run the thermal engine against a submitted snapshot.

    A solver failure is not an HTTP error: the run completes with a stored
    FAILED or NON_CONVERGED result carrying the reason, which is what an
    engineer needs to see. Only a run that cannot be started at all — already
    completed, or an input the engine cannot map onto a model — returns 4xx.
    """
    svc = CalculationService(db)
    run = await svc.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="CalculationRun not found.")
    try:
        await svc.execute(run, current_user)
    except CalculationExecutionError as exc:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "errors": exc.details},
        ) from exc
    await db.commit()
    await db.refresh(run)
    return CalculationRunResponse.of(run)


@router.get("/{run_id}/result")
async def get_calculation_result(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """
    The stored M0-04 ResultSnapshot for a run.

    Returned verbatim, exactly as the engine produced it: this document is
    the calculation record, and reshaping it here would break the content
    hash that proves it has not been edited.

    404 while the run has not produced a result yet.
    """
    svc = CalculationService(db)
    run = await svc.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="CalculationRun not found.")
    result = svc.result_document(run)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Run {run_id} has status {run.status!r} and has produced no "
                f"result yet. POST to /calculation-runs/{run_id}/execute to run it."
            ),
        )
    return JSONResponse(
        content=result,
        headers={"X-Result-Checksum-SHA256": run.result_checksum_sha256 or ""},
    )


@router.get("/{run_id}/input")
async def get_calculation_input(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """The immutable M0-03 InputSnapshot a run was submitted with."""
    svc = CalculationService(db)
    run = await svc.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="CalculationRun not found.")
    return JSONResponse(
        content=run.input_snapshot,
        headers={"X-Input-Checksum-SHA256": run.input_checksum_sha256},
    )


@router.get("/{run_id}/cfd-export")
async def get_cfd_export_package(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """
    The MODE 4 CFD export package for a run.

    A neutral description of the geometry, the loads and the boundary
    conditions, in SI units, for an external CFD engineer. It carries no mesh
    or solver settings: meshing and discretisation are their judgement, not
    this platform's.
    """
    svc = CalculationService(db)
    run = await svc.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="CalculationRun not found.")
    try:
        filename, package = await svc.cfd_export_package(run)
    except CalculationExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "errors": exc.details},
        ) from exc
    return JSONResponse(
        content=package,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

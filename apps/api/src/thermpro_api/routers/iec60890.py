"""
Administration of the licensed IEC TR 60890 coefficient dataset.

CR-ENG-002: the coefficient tables are licensed and are never shipped in this
repository. These endpoints are how a deployment that holds a licence supplies
them. Until an administrator imports a dataset, MODE 1 runs fail with a clear
reason — which is the correct behaviour, not a gap.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.iec60890_dataset import Iec60890Dataset
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.iec60890 import (
    COEFFICIENT_TEMPLATE,
    Iec60890ImportError,
    Iec60890Service,
)

router = APIRouter(prefix="/iec60890-datasets", tags=["iec60890-datasets"])


class Iec60890ImportRequest(BaseModel):
    version: str = Field(description="Semantic version of this import, e.g. '2022.1.0'.")
    source_reference: str = Field(
        description=(
            "The licensed document, edition and tables this was transcribed "
            "from, so a MODE 1 result can be traced to its source."
        )
    )
    coefficients: dict[str, Any] = Field(
        description=(
            "c0, n, d, installation_factors and the optional height "
            "distribution. See GET /iec60890-datasets/template."
        )
    )
    activate: bool = True


class Iec60890DatasetResponse(BaseModel):
    """
    A dataset's metadata.

    The coefficients themselves are deliberately absent: they are licensed
    content, and an API that hands them back to any authenticated caller
    would be a redistribution channel.
    """

    id: uuid.UUID
    version: str
    source_reference: str
    content_hash_sha256: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


def _require_admin(user: CurrentUser) -> None:
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Importing the licensed IEC TR 60890 dataset is an "
                "administrator action (CR-ENG-002)."
            ),
        )


@router.get("/template")
async def get_import_template(current_user: CurrentUser) -> dict[str, Any]:
    """
    The empty import template.

    This is the only IEC TR 60890 artefact this repository ships: it states
    the shape of the data and contains none of it (CR-ENG-002). Every
    coefficient is zero, and a zero c_0 is rejected on import, so a template
    that was never filled in cannot be mistaken for a dataset.
    """
    return COEFFICIENT_TEMPLATE


@router.get("", response_model=list[Iec60890DatasetResponse])
async def list_datasets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Iec60890Dataset]:
    """Every imported dataset, newest first. Metadata only."""
    return await Iec60890Service(db).list_datasets()


@router.post(
    "", response_model=Iec60890DatasetResponse, status_code=status.HTTP_201_CREATED
)
async def import_dataset(
    body: Iec60890ImportRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Iec60890Dataset:
    """Import a licensed coefficient dataset and make it active."""
    _require_admin(current_user)
    try:
        dataset = await Iec60890Service(db).import_dataset(
            version=body.version,
            source_reference=body.source_reference,
            coefficients=body.coefficients,
            actor=current_user,
            activate=body.activate,
        )
    except Iec60890ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "errors": exc.details},
        ) from exc
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.post("/{dataset_id}/activate", response_model=Iec60890DatasetResponse)
async def activate_dataset(
    dataset_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Iec60890Dataset:
    """
    Make an already-imported dataset the one MODE 1 runs use.

    Past results are unaffected: each stored result names the engine version
    and the manifest it was computed with, so switching the active dataset
    changes what happens next and never what already happened.
    """
    _require_admin(current_user)
    service = Iec60890Service(db)
    datasets = {d.id: d for d in await service.list_datasets()}
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="IEC TR 60890 dataset not found.")
    await service.activate(dataset_id, current_user)
    await db.commit()
    await db.refresh(datasets[dataset_id])
    return datasets[dataset_id]

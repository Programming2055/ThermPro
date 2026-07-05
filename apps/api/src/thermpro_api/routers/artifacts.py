"""Calculation artifact endpoints."""
from __future__ import annotations

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.artifact import CalculationArtifact
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.storage import ObjectStorage, get_storage

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    calculation_run_id: uuid.UUID
    artifact_type: str
    filename: str
    content_type: str
    size_bytes: int
    file_hash_sha256: str

    model_config = {"from_attributes": True}


class ArtifactDownloadResponse(BaseModel):
    presigned_url: str
    expires_in_seconds: int = 3600


@router.post(
    "/calculation-runs/{run_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_artifact(
    run_id: uuid.UUID,
    artifact_type: str,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> ArtifactResponse:
    """Upload an artifact for a calculation run."""
    data = await file.read()
    file_hash = hashlib.sha256(data).hexdigest()
    s3_key = f"calculation-runs/{run_id}/artifacts/{file_hash}/{file.filename}"

    storage.put_object(
        key=s3_key,
        data=data,
        content_type=file.content_type or "application/octet-stream",
        metadata={
            "run_id": str(run_id),
            "artifact_type": artifact_type,
        },
    )

    artifact = CalculationArtifact(
        calculation_run_id=run_id,
        artifact_type=artifact_type,
        filename=file.filename or "artifact",
        s3_key=s3_key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        file_hash_sha256=file_hash,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ArtifactResponse:
    """Retrieve artifact metadata by ID."""
    result = await db.execute(
        select(CalculationArtifact).where(CalculationArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}/download", response_model=ArtifactDownloadResponse)
async def download_artifact(
    artifact_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> ArtifactDownloadResponse:
    """Get a pre-signed download URL for an artifact."""
    result = await db.execute(
        select(CalculationArtifact).where(CalculationArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    url = storage.get_presigned_url(artifact.s3_key, expires_in_seconds=3600)
    return ArtifactDownloadResponse(presigned_url=url, expires_in_seconds=3600)

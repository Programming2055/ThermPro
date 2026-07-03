"""Dataset manifest endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.manifest import ManifestService

router = APIRouter(prefix="/dataset-manifests", tags=["dataset-manifests"])


class LibraryPinRequest(BaseModel):
    library_key: str
    library_name: str
    version: str
    content_hash_sha256: str


class DatasetManifestCreate(BaseModel):
    name: str
    pins: list[LibraryPinRequest]
    description: str | None = None


class LibraryPinResultResponse(BaseModel):
    library_key: str
    library_name: str
    version: str
    content_hash_sha256: str
    resolved: bool
    is_approved: bool
    hash_matches: bool
    detail: str


class ManifestValidationResponse(BaseModel):
    manifest_id: uuid.UUID
    is_valid: bool
    validated_at: str
    pin_results: list[LibraryPinResultResponse]


class DatasetManifestResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_valid: bool | None

    model_config = {"from_attributes": True}


@router.post("", response_model=DatasetManifestResponse, status_code=status.HTTP_201_CREATED)
async def create_manifest(
    body: DatasetManifestCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetManifestResponse:
    """Create a new dataset manifest from a list of library pins."""
    svc = ManifestService(db)
    manifest = await svc.create_manifest(
        name=body.name,
        pins=[p.model_dump() for p in body.pins],
        created_by_id=current_user.user_id,
        description=body.description,
    )
    await db.commit()
    await db.refresh(manifest)
    return DatasetManifestResponse.model_validate(manifest)


@router.get("/{manifest_id}", response_model=DatasetManifestResponse)
async def get_manifest(
    manifest_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetManifestResponse:
    """Retrieve a dataset manifest by ID."""
    svc = ManifestService(db)
    manifest = await svc.get_by_id(manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="DatasetManifest not found.")
    return DatasetManifestResponse.model_validate(manifest)


@router.post("/{manifest_id}/validate", response_model=ManifestValidationResponse)
async def validate_manifest(
    manifest_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ManifestValidationResponse:
    """
    Validate a dataset manifest.

    Resolves each library pin to an APPROVED release and verifies content hashes.
    """
    svc = ManifestService(db)
    try:
        result = await svc.validate_manifest(manifest_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return ManifestValidationResponse(
        manifest_id=result.manifest_id,
        is_valid=result.is_valid,
        validated_at=result.validated_at,
        pin_results=[
            LibraryPinResultResponse(
                library_key=p.library_key,
                library_name=p.library_name,
                version=p.version,
                content_hash_sha256=p.content_hash_sha256,
                resolved=p.resolved,
                is_approved=p.is_approved,
                hash_matches=p.hash_matches,
                detail=p.detail,
            )
            for p in result.pin_results
        ],
    )

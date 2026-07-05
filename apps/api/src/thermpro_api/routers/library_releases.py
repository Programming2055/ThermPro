"""Library release management endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.library_release import LibraryRelease as LibraryReleaseModel
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.library import LibraryImmutabilityError, LibraryService

router = APIRouter(prefix="/library-releases", tags=["library-releases"])

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class LibraryReleaseCreate(BaseModel):
    library_name: str
    version: str
    entries: list[dict[str, Any]]
    description: str | None = None


class LibraryReleaseResponse(BaseModel):
    id: uuid.UUID
    library_name: str
    version: str
    status: str
    content_hash_sha256: str
    description: str | None
    created_at: str | None = None

    model_config = {"from_attributes": True}


@router.post("", response_model=LibraryReleaseResponse, status_code=status.HTTP_201_CREATED)
async def create_release(
    body: LibraryReleaseCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LibraryReleaseResponse:
    """Create a new DRAFT library release."""
    svc = LibraryService(db)
    release = await svc.create_release(
        library_name=body.library_name,
        version=body.version,
        entries=body.entries,
        description=body.description,
    )
    await db.commit()
    await db.refresh(release)
    return LibraryReleaseResponse.model_validate(release)


@router.get("", response_model=PaginatedResponse[LibraryReleaseResponse])
async def list_releases(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    library_name: str | None = None,
    release_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[LibraryReleaseResponse]:
    """List library releases with optional filters (paginated)."""
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(LibraryReleaseModel))
    total = total_result.scalar_one()
    svc = LibraryService(db)
    releases = await svc.list_releases(
        library_name=library_name,
        status=release_status,
        limit=page_size,
        offset=offset,
    )
    return PaginatedResponse(
        items=[LibraryReleaseResponse.model_validate(r) for r in releases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{release_id}", response_model=LibraryReleaseResponse)
async def get_release(
    release_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LibraryReleaseResponse:
    """Retrieve a library release by ID."""
    svc = LibraryService(db)
    release = await svc.get_by_id(release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="LibraryRelease not found.")
    return LibraryReleaseResponse.model_validate(release)


@router.post("/{release_id}/approve", response_model=LibraryReleaseResponse)
async def approve_release(
    release_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LibraryReleaseResponse:
    """
    Approve a library release.

    Once approved, the release is immutable (DR-002 / M0-09).
    Only users with ADMIN or REVIEWER role may approve.
    """
    if current_user.role not in ("ADMIN", "REVIEWER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or REVIEWER users may approve library releases.",
        )
    svc = LibraryService(db)
    try:
        release = await svc.approve_release(
            release_id=release_id,
            approver_id=current_user.user_id,
        )
    except LibraryImmutabilityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(release)
    return LibraryReleaseResponse.model_validate(release)

"""Project CRUD endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.project import Project
from thermpro_api.services.auth import CurrentUser

router = APIRouter(prefix="/projects", tags=["projects"])

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    is_archived: bool
    created_at: str | None = None

    model_config = {"from_attributes": True}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Create a new project owned by the current user."""
    project = Project(
        name=body.name,
        description=body.description,
        owner_id=current_user.user_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[ProjectResponse]:
    """List all projects visible to the current user (paginated)."""
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(Project))
    total = total_result.scalar_one()
    result = await db.execute(
        select(Project)
        .order_by(Project.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    projects = result.scalars().all()
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Retrieve a project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse.model_validate(project)

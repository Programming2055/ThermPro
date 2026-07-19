"""Geometry CRUD endpoints — M2 enclosure spatial model.

No thermal calculations, no airflow calculations, no IEC TR 60890 logic.
Audit events are recorded on every write.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.geometry import (
    Assembly,
    BusbarPlacement,
    Compartment,
    DevicePlacement,
    Enclosure,
    ExternalOpening,
    GeometryValidationIssue,
    InternalOpening,
    Partition,
    Surface,
)
from thermpro_api.models.project import Project
from thermpro_api.services.audit import AuditService
from thermpro_api.services.auth import CurrentUser
from thermpro_api.services.geometry_validation import validate_enclosure_geometry

router = APIRouter(tags=["geometry"])

# ─── Request / response schemas ──────────────────────────────────────────────


class AssemblyCreate(BaseModel):
    name: str
    description: str | None = None


class AssemblyResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    coordinate_system_version: str
    revision: int
    created_at: str | None = None

    model_config = {"from_attributes": True}


class EnclosureCreate(BaseModel):
    name: str
    assembly_id: uuid.UUID | None = None
    external_width_m: float
    external_height_m: float
    external_depth_m: float
    internal_width_m: float
    internal_height_m: float
    internal_depth_m: float
    wall_thickness_m: float = 0.002
    material_ref: str | None = None
    installation_type: str = "FLOOR_STANDING"
    ip_rating: str | None = None

    @field_validator(
        "external_width_m", "external_height_m", "external_depth_m",
        "internal_width_m", "internal_height_m", "internal_depth_m",
        "wall_thickness_m",
    )
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class EnclosureResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    assembly_id: uuid.UUID | None
    name: str
    external_width_m: float
    external_height_m: float
    external_depth_m: float
    internal_width_m: float
    internal_height_m: float
    internal_depth_m: float
    wall_thickness_m: float
    material_ref: str | None
    installation_type: str
    ip_rating: str | None
    coordinate_system_version: str
    revision: int
    created_at: str | None = None

    model_config = {"from_attributes": True}


class SurfaceCreate(BaseModel):
    face: str
    is_exposed: bool = True
    material_override: str | None = None
    emissivity_override: float | None = None


class SurfaceResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    face: str
    is_exposed: bool
    material_override: str | None
    emissivity_override: float | None

    model_config = {"from_attributes": True}


class CompartmentCreate(BaseModel):
    name: str
    compartment_type: str = "DEVICE_CHAMBER"
    parent_compartment_id: uuid.UUID | None = None
    position_x_m: float = 0.0
    position_y_m: float = 0.0
    position_z_m: float = 0.0
    width_m: float
    height_m: float
    depth_m: float

    @field_validator("width_m", "height_m", "depth_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class CompartmentResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    parent_compartment_id: uuid.UUID | None
    name: str
    compartment_type: str
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    height_m: float
    depth_m: float
    revision: int

    model_config = {"from_attributes": True}


class PartitionCreate(BaseModel):
    name: str | None = None
    orientation: str = "VERTICAL_YZ"
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    height_m: float
    thickness_m: float = 0.001
    material_ref: str | None = None
    is_removable: bool = False

    @field_validator("width_m", "height_m", "thickness_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class PartitionResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    name: str | None
    orientation: str
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    height_m: float
    thickness_m: float
    material_ref: str | None
    is_removable: bool
    revision: int

    model_config = {"from_attributes": True}


class ExternalOpeningCreate(BaseModel):
    surface_id: uuid.UUID | None = None
    name: str | None = None
    position_x_m: float
    position_y_m: float
    width_m: float
    height_m: float
    open_area_fraction: float = 1.0
    discharge_coefficient: float = 0.61
    direction: str = "BIDIRECTIONAL"
    elevation_m: float = 0.0
    has_grille: bool = False
    has_filter: bool = False

    @field_validator("open_area_fraction", "discharge_coefficient")
    @classmethod
    def unit_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("must be in [0, 1]")
        return v

    @field_validator("width_m", "height_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class ExternalOpeningResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    surface_id: uuid.UUID | None
    name: str | None
    position_x_m: float
    position_y_m: float
    width_m: float
    height_m: float
    open_area_fraction: float
    discharge_coefficient: float
    direction: str
    elevation_m: float
    has_grille: bool
    has_filter: bool

    model_config = {"from_attributes": True}


class InternalOpeningCreate(BaseModel):
    compartment_a_id: uuid.UUID | None = None
    compartment_b_id: uuid.UUID | None = None
    name: str | None = None
    position_x_m: float
    position_y_m: float
    width_m: float
    height_m: float
    open_area_fraction: float = 1.0
    discharge_coefficient: float = 0.61
    direction: str = "BIDIRECTIONAL"

    @field_validator("open_area_fraction", "discharge_coefficient")
    @classmethod
    def unit_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("must be in [0, 1]")
        return v

    @field_validator("width_m", "height_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class InternalOpeningResponse(BaseModel):
    id: uuid.UUID
    partition_id: uuid.UUID
    compartment_a_id: uuid.UUID | None
    compartment_b_id: uuid.UUID | None
    name: str | None
    position_x_m: float
    position_y_m: float
    width_m: float
    height_m: float
    open_area_fraction: float
    discharge_coefficient: float
    direction: str

    model_config = {"from_attributes": True}


class DevicePlacementCreate(BaseModel):
    compartment_id: uuid.UUID | None = None
    name: str
    device_library_ref: str | None = None
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    height_m: float
    depth_m: float
    rotation_deg: float = 0.0
    mounting_surface: str | None = None
    clearance_x_m: float = 0.0
    clearance_y_m: float = 0.0
    clearance_z_m: float = 0.0

    @field_validator("width_m", "height_m", "depth_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class DevicePlacementResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    compartment_id: uuid.UUID | None
    name: str
    device_library_ref: str | None
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    height_m: float
    depth_m: float
    rotation_deg: float
    mounting_surface: str | None
    clearance_x_m: float
    clearance_y_m: float
    clearance_z_m: float

    model_config = {"from_attributes": True}


class BusbarPlacementCreate(BaseModel):
    compartment_id: uuid.UUID | None = None
    name: str
    busbar_library_ref: str | None = None
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    thickness_m: float
    length_m: float
    phase_designation: str | None = None
    clearance_m: float = 0.005

    @field_validator("width_m", "thickness_m", "length_m")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("dimension must be > 0 metres")
        return v


class BusbarPlacementResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    compartment_id: uuid.UUID | None
    name: str
    busbar_library_ref: str | None
    position_x_m: float
    position_y_m: float
    position_z_m: float
    width_m: float
    thickness_m: float
    length_m: float
    phase_designation: str | None
    clearance_m: float

    model_config = {"from_attributes": True}


class ValidationIssueResponse(BaseModel):
    id: uuid.UUID
    enclosure_id: uuid.UUID
    issue_id: str
    severity: str
    entity_type: str
    entity_id: str
    message: str
    coordinate_ref: dict[str, Any] | None
    suggested_fix: str | None
    rule_id: str
    is_resolved: bool

    model_config = {"from_attributes": True}


class ValidationResponse(BaseModel):
    enclosure_id: uuid.UUID
    issue_count: int
    error_count: int
    warning_count: int
    blocker_count: int
    issues: list[ValidationIssueResponse]


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _get_enclosure_or_404(
    enclosure_id: uuid.UUID, db: AsyncSession
) -> Enclosure:
    result = await db.execute(select(Enclosure).where(Enclosure.id == enclosure_id))
    enc = result.scalar_one_or_none()
    if enc is None:
        raise HTTPException(status_code=404, detail="Enclosure not found")
    return enc


async def _get_project_or_404(project_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


# ─── Assembly endpoints ───────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/assemblies",
    response_model=AssemblyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assembly(
    project_id: uuid.UUID,
    body: AssemblyCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssemblyResponse:
    await _get_project_or_404(project_id, db)
    assembly = Assembly(
        project_id=project_id,
        name=body.name,
        description=body.description,
    )
    db.add(assembly)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "assembly.created", "Assembly", assembly.id, actor=current_user
    )
    await db.commit()
    await db.refresh(assembly)
    return AssemblyResponse.model_validate(assembly)


@router.get("/projects/{project_id}/assemblies", response_model=list[AssemblyResponse])
async def list_assemblies(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[AssemblyResponse]:
    await _get_project_or_404(project_id, db)
    result = await db.execute(
        select(Assembly)
        .where(Assembly.project_id == project_id)
        .order_by(Assembly.created_at.asc())
    )
    return [AssemblyResponse.model_validate(a) for a in result.scalars().all()]


# ─── Enclosure endpoints ──────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/enclosures",
    response_model=EnclosureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_enclosure(
    project_id: uuid.UUID,
    body: EnclosureCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnclosureResponse:
    await _get_project_or_404(project_id, db)
    enclosure = Enclosure(
        project_id=project_id,
        assembly_id=body.assembly_id,
        name=body.name,
        external_width_m=body.external_width_m,
        external_height_m=body.external_height_m,
        external_depth_m=body.external_depth_m,
        internal_width_m=body.internal_width_m,
        internal_height_m=body.internal_height_m,
        internal_depth_m=body.internal_depth_m,
        wall_thickness_m=body.wall_thickness_m,
        material_ref=body.material_ref,
        installation_type=body.installation_type,
        ip_rating=body.ip_rating,
    )
    db.add(enclosure)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "enclosure.created", "Enclosure", enclosure.id, actor=current_user
    )
    await db.commit()
    await db.refresh(enclosure)
    return EnclosureResponse.model_validate(enclosure)


@router.get(
    "/projects/{project_id}/enclosures", response_model=list[EnclosureResponse]
)
async def list_enclosures(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[EnclosureResponse]:
    await _get_project_or_404(project_id, db)
    result = await db.execute(
        select(Enclosure)
        .where(Enclosure.project_id == project_id)
        .order_by(Enclosure.created_at.asc())
    )
    return [EnclosureResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/enclosures/{enclosure_id}", response_model=EnclosureResponse)
async def get_enclosure(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> EnclosureResponse:
    enc = await _get_enclosure_or_404(enclosure_id, db)
    return EnclosureResponse.model_validate(enc)


@router.delete("/enclosures/{enclosure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enclosure(
    enclosure_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    enc = await _get_enclosure_or_404(enclosure_id, db)
    audit = AuditService(db)
    await audit.record_event(
        "enclosure.deleted", "Enclosure", enc.id, actor=current_user
    )
    await db.delete(enc)
    await db.commit()


# ─── Surface endpoints ────────────────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/surfaces",
    response_model=SurfaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_surface(
    enclosure_id: uuid.UUID,
    body: SurfaceCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurfaceResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    surface = Surface(
        enclosure_id=enclosure_id,
        face=body.face,
        is_exposed=body.is_exposed,
        material_override=body.material_override,
        emissivity_override=body.emissivity_override,
    )
    db.add(surface)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "surface.created", "Surface", surface.id, actor=current_user
    )
    await db.commit()
    await db.refresh(surface)
    return SurfaceResponse.model_validate(surface)


@router.get(
    "/enclosures/{enclosure_id}/surfaces", response_model=list[SurfaceResponse]
)
async def list_surfaces(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[SurfaceResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(Surface).where(Surface.enclosure_id == enclosure_id)
    )
    return [SurfaceResponse.model_validate(s) for s in result.scalars().all()]


# ─── Compartment endpoints ────────────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/compartments",
    response_model=CompartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_compartment(
    enclosure_id: uuid.UUID,
    body: CompartmentCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompartmentResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    comp = Compartment(
        enclosure_id=enclosure_id,
        parent_compartment_id=body.parent_compartment_id,
        name=body.name,
        compartment_type=body.compartment_type,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        position_z_m=body.position_z_m,
        width_m=body.width_m,
        height_m=body.height_m,
        depth_m=body.depth_m,
    )
    db.add(comp)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "compartment.created", "Compartment", comp.id, actor=current_user
    )
    await db.commit()
    await db.refresh(comp)
    return CompartmentResponse.model_validate(comp)


@router.get(
    "/enclosures/{enclosure_id}/compartments",
    response_model=list[CompartmentResponse],
)
async def list_compartments(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[CompartmentResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(Compartment)
        .where(Compartment.enclosure_id == enclosure_id)
        .order_by(Compartment.created_at.asc())
    )
    return [CompartmentResponse.model_validate(c) for c in result.scalars().all()]


@router.delete(
    "/compartments/{compartment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_compartment(
    compartment_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(Compartment).where(Compartment.id == compartment_id)
    )
    comp = result.scalar_one_or_none()
    if comp is None:
        raise HTTPException(status_code=404, detail="Compartment not found")
    audit = AuditService(db)
    await audit.record_event(
        "compartment.deleted", "Compartment", comp.id, actor=current_user
    )
    await db.delete(comp)
    await db.commit()


# ─── Partition endpoints ──────────────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/partitions",
    response_model=PartitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partition(
    enclosure_id: uuid.UUID,
    body: PartitionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PartitionResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    part = Partition(
        enclosure_id=enclosure_id,
        name=body.name,
        orientation=body.orientation,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        position_z_m=body.position_z_m,
        width_m=body.width_m,
        height_m=body.height_m,
        thickness_m=body.thickness_m,
        material_ref=body.material_ref,
        is_removable=body.is_removable,
    )
    db.add(part)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "partition.created", "Partition", part.id, actor=current_user
    )
    await db.commit()
    await db.refresh(part)
    return PartitionResponse.model_validate(part)


@router.get(
    "/enclosures/{enclosure_id}/partitions",
    response_model=list[PartitionResponse],
)
async def list_partitions(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[PartitionResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(Partition)
        .where(Partition.enclosure_id == enclosure_id)
        .order_by(Partition.created_at.asc())
    )
    return [PartitionResponse.model_validate(p) for p in result.scalars().all()]


@router.delete(
    "/partitions/{partition_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_partition(
    partition_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(Partition).where(Partition.id == partition_id)
    )
    part = result.scalar_one_or_none()
    if part is None:
        raise HTTPException(status_code=404, detail="Partition not found")
    audit = AuditService(db)
    await audit.record_event(
        "partition.deleted", "Partition", part.id, actor=current_user
    )
    await db.delete(part)
    await db.commit()


# ─── External opening endpoints ───────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/external-openings",
    response_model=ExternalOpeningResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_external_opening(
    enclosure_id: uuid.UUID,
    body: ExternalOpeningCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExternalOpeningResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    opening = ExternalOpening(
        enclosure_id=enclosure_id,
        surface_id=body.surface_id,
        name=body.name,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        width_m=body.width_m,
        height_m=body.height_m,
        open_area_fraction=body.open_area_fraction,
        discharge_coefficient=body.discharge_coefficient,
        direction=body.direction,
        elevation_m=body.elevation_m,
        has_grille=body.has_grille,
        has_filter=body.has_filter,
    )
    db.add(opening)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "external_opening.created", "ExternalOpening", opening.id, actor=current_user
    )
    await db.commit()
    await db.refresh(opening)
    return ExternalOpeningResponse.model_validate(opening)


@router.get(
    "/enclosures/{enclosure_id}/external-openings",
    response_model=list[ExternalOpeningResponse],
)
async def list_external_openings(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[ExternalOpeningResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(ExternalOpening).where(ExternalOpening.enclosure_id == enclosure_id)
    )
    return [ExternalOpeningResponse.model_validate(o) for o in result.scalars().all()]


# ─── Internal opening endpoints ───────────────────────────────────────────────


@router.post(
    "/partitions/{partition_id}/internal-openings",
    response_model=InternalOpeningResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_internal_opening(
    partition_id: uuid.UUID,
    body: InternalOpeningCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InternalOpeningResponse:
    result = await db.execute(select(Partition).where(Partition.id == partition_id))
    part = result.scalar_one_or_none()
    if part is None:
        raise HTTPException(status_code=404, detail="Partition not found")
    opening = InternalOpening(
        partition_id=partition_id,
        compartment_a_id=body.compartment_a_id,
        compartment_b_id=body.compartment_b_id,
        name=body.name,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        width_m=body.width_m,
        height_m=body.height_m,
        open_area_fraction=body.open_area_fraction,
        discharge_coefficient=body.discharge_coefficient,
        direction=body.direction,
    )
    db.add(opening)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "internal_opening.created", "InternalOpening", opening.id, actor=current_user
    )
    await db.commit()
    await db.refresh(opening)
    return InternalOpeningResponse.model_validate(opening)


@router.get(
    "/partitions/{partition_id}/internal-openings",
    response_model=list[InternalOpeningResponse],
)
async def list_internal_openings(
    partition_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[InternalOpeningResponse]:
    result = await db.execute(select(Partition).where(Partition.id == partition_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Partition not found")
    result2 = await db.execute(
        select(InternalOpening).where(InternalOpening.partition_id == partition_id)
    )
    return [InternalOpeningResponse.model_validate(o) for o in result2.scalars().all()]


# ─── Device placement endpoints ───────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/device-placements",
    response_model=DevicePlacementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device_placement(
    enclosure_id: uuid.UUID,
    body: DevicePlacementCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DevicePlacementResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    dev = DevicePlacement(
        enclosure_id=enclosure_id,
        compartment_id=body.compartment_id,
        name=body.name,
        device_library_ref=body.device_library_ref,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        position_z_m=body.position_z_m,
        width_m=body.width_m,
        height_m=body.height_m,
        depth_m=body.depth_m,
        rotation_deg=body.rotation_deg,
        mounting_surface=body.mounting_surface,
        clearance_x_m=body.clearance_x_m,
        clearance_y_m=body.clearance_y_m,
        clearance_z_m=body.clearance_z_m,
    )
    db.add(dev)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "device_placement.created", "DevicePlacement", dev.id, actor=current_user
    )
    await db.commit()
    await db.refresh(dev)
    return DevicePlacementResponse.model_validate(dev)


@router.get(
    "/enclosures/{enclosure_id}/device-placements",
    response_model=list[DevicePlacementResponse],
)
async def list_device_placements(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[DevicePlacementResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(DevicePlacement).where(DevicePlacement.enclosure_id == enclosure_id)
    )
    return [DevicePlacementResponse.model_validate(d) for d in result.scalars().all()]


@router.delete(
    "/device-placements/{device_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_device_placement(
    device_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(DevicePlacement).where(DevicePlacement.id == device_id)
    )
    dev = result.scalar_one_or_none()
    if dev is None:
        raise HTTPException(status_code=404, detail="DevicePlacement not found")
    audit = AuditService(db)
    await audit.record_event(
        "device_placement.deleted", "DevicePlacement", dev.id, actor=current_user
    )
    await db.delete(dev)
    await db.commit()


# ─── Busbar placement endpoints ───────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/busbar-placements",
    response_model=BusbarPlacementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_busbar_placement(
    enclosure_id: uuid.UUID,
    body: BusbarPlacementCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusbarPlacementResponse:
    await _get_enclosure_or_404(enclosure_id, db)
    bus = BusbarPlacement(
        enclosure_id=enclosure_id,
        compartment_id=body.compartment_id,
        name=body.name,
        busbar_library_ref=body.busbar_library_ref,
        position_x_m=body.position_x_m,
        position_y_m=body.position_y_m,
        position_z_m=body.position_z_m,
        width_m=body.width_m,
        thickness_m=body.thickness_m,
        length_m=body.length_m,
        phase_designation=body.phase_designation,
        clearance_m=body.clearance_m,
    )
    db.add(bus)
    await db.flush()
    audit = AuditService(db)
    await audit.record_event(
        "busbar_placement.created", "BusbarPlacement", bus.id, actor=current_user
    )
    await db.commit()
    await db.refresh(bus)
    return BusbarPlacementResponse.model_validate(bus)


@router.get(
    "/enclosures/{enclosure_id}/busbar-placements",
    response_model=list[BusbarPlacementResponse],
)
async def list_busbar_placements(
    enclosure_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
) -> list[BusbarPlacementResponse]:
    await _get_enclosure_or_404(enclosure_id, db)
    result = await db.execute(
        select(BusbarPlacement).where(BusbarPlacement.enclosure_id == enclosure_id)
    )
    return [BusbarPlacementResponse.model_validate(b) for b in result.scalars().all()]


@router.delete(
    "/busbar-placements/{busbar_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_busbar_placement(
    busbar_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(BusbarPlacement).where(BusbarPlacement.id == busbar_id)
    )
    bus = result.scalar_one_or_none()
    if bus is None:
        raise HTTPException(status_code=404, detail="BusbarPlacement not found")
    audit = AuditService(db)
    await audit.record_event(
        "busbar_placement.deleted", "BusbarPlacement", bus.id, actor=current_user
    )
    await db.delete(bus)
    await db.commit()


# ─── Geometry validation endpoint ─────────────────────────────────────────────


@router.post(
    "/enclosures/{enclosure_id}/validate",
    response_model=ValidationResponse,
)
async def validate_geometry(
    enclosure_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationResponse:
    """
    Run geometry validation rules for the enclosure and persist results.

    Clears existing unresolved validation issues before inserting new ones.
    No thermal or airflow calculations are performed (M2 scope boundary).
    """
    enc = await _get_enclosure_or_404(enclosure_id, db)

    compartments_result = await db.execute(
        select(Compartment).where(Compartment.enclosure_id == enclosure_id)
    )
    compartments = list(compartments_result.scalars().all())

    partitions_result = await db.execute(
        select(Partition).where(Partition.enclosure_id == enclosure_id)
    )
    partitions = list(partitions_result.scalars().all())

    devices_result = await db.execute(
        select(DevicePlacement).where(DevicePlacement.enclosure_id == enclosure_id)
    )
    devices = list(devices_result.scalars().all())

    busbars_result = await db.execute(
        select(BusbarPlacement).where(BusbarPlacement.enclosure_id == enclosure_id)
    )
    busbars = list(busbars_result.scalars().all())

    ext_openings_result = await db.execute(
        select(ExternalOpening).where(ExternalOpening.enclosure_id == enclosure_id)
    )
    ext_openings = list(ext_openings_result.scalars().all())

    partition_ids = [p.id for p in partitions]
    int_openings: list[InternalOpening] = []
    if partition_ids:
        int_result = await db.execute(
            select(InternalOpening).where(
                InternalOpening.partition_id.in_(partition_ids)
            )
        )
        int_openings = list(int_result.scalars().all())

    # Delete existing unresolved issues for this enclosure
    existing = await db.execute(
        select(GeometryValidationIssue).where(
            GeometryValidationIssue.enclosure_id == enclosure_id,
            GeometryValidationIssue.is_resolved.is_(False),
        )
    )
    for issue in existing.scalars().all():
        await db.delete(issue)
    await db.flush()

    # Run validation
    issue_dicts = validate_enclosure_geometry(
        enc, compartments, partitions, devices, busbars, ext_openings, int_openings
    )

    orm_issues: list[GeometryValidationIssue] = []
    for d in issue_dicts:
        orm_issue = GeometryValidationIssue(
            enclosure_id=enclosure_id,
            issue_id=d["issue_id"],
            severity=d["severity"],
            entity_type=d["entity_type"],
            entity_id=d["entity_id"],
            message=d["message"],
            coordinate_ref=d.get("coordinate_ref"),
            suggested_fix=d.get("suggested_fix"),
            rule_id=d["rule_id"],
            is_resolved=False,
        )
        db.add(orm_issue)
        orm_issues.append(orm_issue)

    audit = AuditService(db)
    await audit.record_event(
        "enclosure.validated",
        "Enclosure",
        enc.id,
        actor=current_user,
        metadata={"issue_count": len(issue_dicts)},
    )
    await db.commit()
    for issue in orm_issues:
        await db.refresh(issue)

    responses = [ValidationIssueResponse.model_validate(i) for i in orm_issues]
    return ValidationResponse(
        enclosure_id=enclosure_id,
        issue_count=len(responses),
        error_count=sum(1 for r in responses if r.severity == "ERROR"),
        warning_count=sum(1 for r in responses if r.severity == "WARNING"),
        blocker_count=sum(1 for r in responses if r.severity == "BLOCKER"),
        issues=responses,
    )

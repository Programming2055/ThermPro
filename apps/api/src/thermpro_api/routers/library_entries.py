"""M3 engineering library entry endpoints.

Each library type has its own set of CRUD endpoints under:
  /library-entries/{type}/

where {type} is one of:
  materials | surfaces | busbar-profiles | devices
  fans | filters | ventilation-openings | cables | connections

All entries belong to a library release (release_id required on create).
Mutation is blocked once the parent release is APPROVED (CR-ENG-012).
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.database import get_db
from thermpro_api.models.library import (
    BusbarProfileLibraryEntry as BusbarProfileORM,
    CableLibraryEntry as CableORM,
    ConnectionLibraryEntry as ConnectionORM,
    DeviceLibraryEntry as DeviceORM,
    FanLibraryEntry as FanORM,
    FilterLibraryEntry as FilterORM,
    MaterialLibraryEntry as MaterialORM,
    SurfaceLibraryEntry as SurfaceORM,
    VentilationOpeningLibraryEntry as VentilationOpeningORM,
)
from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.auth import CurrentUser

router = APIRouter(prefix="/library-entries", tags=["library-entries"])

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Guard: block mutation on APPROVED releases
# ---------------------------------------------------------------------------


async def _assert_release_mutable(release_id: uuid.UUID, db: AsyncSession) -> LibraryRelease:
    result = await db.execute(select(LibraryRelease).where(LibraryRelease.id == release_id))
    release = result.scalar_one_or_none()
    if release is None:
        raise HTTPException(status_code=404, detail="LibraryRelease not found.")
    if release.status not in ("DRAFT", "UNDER_REVIEW"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"LibraryRelease {release_id} is {release.status}. "
                "Library entries are immutable once a release is APPROVED (CR-ENG-012)."
            ),
        )
    return release


# ---------------------------------------------------------------------------
# Schemas — Material
# ---------------------------------------------------------------------------


class MaterialCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    category: str
    thermal_conductivity_w_per_m_k: float
    density_kg_per_m3: float
    specific_heat_j_per_kg_k: float
    electrical_resistivity_ohm_m: float | None = None
    temp_coeff_resistance_per_k: float | None = None
    emissivity: float | None = None
    max_operating_temp_k: float | None = None
    references: list[str] | None = None
    notes: str | None = None


class MaterialResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    category: str
    thermal_conductivity_w_per_m_k: float
    density_kg_per_m3: float
    specific_heat_j_per_kg_k: float
    electrical_resistivity_ohm_m: float | None
    temp_coeff_resistance_per_k: float | None
    emissivity: float | None
    max_operating_temp_k: float | None
    references: list[str] | None
    notes: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Surface
# ---------------------------------------------------------------------------


class SurfaceCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    emissivity: float
    absorptivity: float | None = None
    roughness_um: float | None = None
    coating: str | None = None
    material_ref: str | None = None
    references: list[str] | None = None


class SurfaceResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    emissivity: float
    absorptivity: float | None
    roughness_um: float | None
    coating: str | None
    material_ref: str | None
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — BusbarProfile
# ---------------------------------------------------------------------------


class BusbarProfileCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    material_ref: str
    profile: str
    coating: str
    thickness_m: float
    width_m: float
    cross_section_area_m2: float
    max_continuous_current_a: float | None = None
    emissivity_override: float | None = None
    references: list[str] | None = None


class BusbarProfileResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    material_ref: str
    profile: str
    coating: str
    thickness_m: float
    width_m: float
    cross_section_area_m2: float
    max_continuous_current_a: float | None
    emissivity_override: float | None
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Device
# ---------------------------------------------------------------------------


class LossCurvePointSchema(BaseModel):
    current_fraction: float
    power_loss_w: float


class DeviceCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    family: str
    model: str
    rated_current_a: float
    poles: int
    width_m: float
    height_m: float
    depth_m: float
    mounting_type: str
    ventilation_requirement: str
    max_ambient_temp_k: float = Field(description="Kelvin — CR-ENG-003")
    power_loss_curve: list[LossCurvePointSchema]
    loss_confidence: str
    references: list[str] | None = None
    notes: str | None = None


class DeviceResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    family: str
    model: str
    rated_current_a: float
    poles: int
    width_m: float
    height_m: float
    depth_m: float
    mounting_type: str
    ventilation_requirement: str
    max_ambient_temp_k: float
    power_loss_curve: list[dict[str, Any]]
    loss_confidence: str
    references: list[str] | None
    notes: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Fan
# ---------------------------------------------------------------------------


class FanCurvePointSchema(BaseModel):
    flow_m3_per_s: float
    static_pressure_pa: float
    power_w: float | None = None
    efficiency: float | None = None


class FanCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    direction: str
    rated_speed_rpm: float
    rated_flow_m3_per_s: float
    rated_pressure_pa: float
    rated_power_w: float
    voltage_v: float | None = None
    frequency_hz: float | None = None
    fan_curve: list[FanCurvePointSchema]
    references: list[str] | None = None


class FanResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    direction: str
    rated_speed_rpm: float
    rated_flow_m3_per_s: float
    rated_pressure_pa: float
    rated_power_w: float
    voltage_v: float | None
    frequency_hz: float | None
    fan_curve: list[dict[str, Any]]
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Filter
# ---------------------------------------------------------------------------


class FilterCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    dust_class: str | None = None
    rated_flow_m3_per_s: float
    pressure_drop_pa: float
    loss_coefficient: float
    porosity: float | None = None
    initial_efficiency: float | None = None
    references: list[str] | None = None


class FilterResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    dust_class: str | None
    rated_flow_m3_per_s: float
    pressure_drop_pa: float
    loss_coefficient: float
    porosity: float | None
    initial_efficiency: float | None
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — VentilationOpening
# ---------------------------------------------------------------------------


class VentilationOpeningCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    accessory: str
    gross_width_m: float
    gross_height_m: float
    open_area_fraction: float
    discharge_coefficient: float
    filter_ref: str | None = None
    references: list[str] | None = None


class VentilationOpeningResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str
    model: str
    accessory: str
    gross_width_m: float
    gross_height_m: float
    open_area_fraction: float
    discharge_coefficient: float
    filter_ref: str | None
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Cable
# ---------------------------------------------------------------------------


class CableCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str | None = None
    designation: str
    conductor: str
    insulation: str
    conductor_cross_section_m2: float
    outer_diameter_m: float
    rated_current_a: float
    resistance_ohm_per_m: float
    temp_coeff_resistance_per_k: float
    max_conductor_temp_k: float = Field(description="Kelvin — CR-ENG-003")
    references: list[str] | None = None


class CableResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    manufacturer: str | None
    designation: str
    conductor: str
    insulation: str
    conductor_cross_section_m2: float
    outer_diameter_m: float
    rated_current_a: float
    resistance_ohm_per_m: float
    temp_coeff_resistance_per_k: float
    max_conductor_temp_k: float
    references: list[str] | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — Connection
# ---------------------------------------------------------------------------


class ConnectionCreate(BaseModel):
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    contact_quality: str
    plating: str | None = None
    bolt_size_m: float | None = None
    bolt_torque_n_m: float | None = None
    contact_pressure_pa: float | None = None
    joint_resistance_ohm: float
    resistance_source: str
    age_factor: float = 1.0
    references: list[str] | None = None
    notes: str | None = None


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    domain_entry_id: str
    library_version: str
    name: str
    contact_quality: str
    plating: str | None
    bolt_size_m: float | None
    bolt_torque_n_m: float | None
    contact_pressure_pa: float | None
    joint_resistance_ohm: float
    resistance_source: str
    age_factor: float
    references: list[str] | None
    notes: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Material endpoints
# ---------------------------------------------------------------------------


@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    body: MaterialCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MaterialResponse:
    await _assert_release_mutable(body.release_id, db)
    row = MaterialORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return MaterialResponse.model_validate(row)


@router.get("/materials", response_model=PaginatedResponse[MaterialResponse])
async def list_materials(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[MaterialResponse]:
    q = select(MaterialORM)
    if release_id is not None:
        q = q.where(MaterialORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    count_result = await db.execute(
        select(MaterialORM).where(
            MaterialORM.release_id == release_id if release_id else True  # type: ignore[arg-type]
        )
    )
    total = len(count_result.scalars().all())
    return PaginatedResponse(
        items=[MaterialResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/materials/{entry_id}", response_model=MaterialResponse)
async def get_material(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MaterialResponse:
    result = await db.execute(select(MaterialORM).where(MaterialORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="MaterialLibraryEntry not found.")
    return MaterialResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Surface endpoints
# ---------------------------------------------------------------------------


@router.post("/surfaces", response_model=SurfaceResponse, status_code=status.HTTP_201_CREATED)
async def create_surface(
    body: SurfaceCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurfaceResponse:
    await _assert_release_mutable(body.release_id, db)
    row = SurfaceORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SurfaceResponse.model_validate(row)


@router.get("/surfaces", response_model=PaginatedResponse[SurfaceResponse])
async def list_surfaces(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SurfaceResponse]:
    q = select(SurfaceORM)
    if release_id is not None:
        q = q.where(SurfaceORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[SurfaceResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/surfaces/{entry_id}", response_model=SurfaceResponse)
async def get_surface(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SurfaceResponse:
    result = await db.execute(select(SurfaceORM).where(SurfaceORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="SurfaceLibraryEntry not found.")
    return SurfaceResponse.model_validate(row)


# ---------------------------------------------------------------------------
# BusbarProfile endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/busbar-profiles",
    response_model=BusbarProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_busbar_profile(
    body: BusbarProfileCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusbarProfileResponse:
    await _assert_release_mutable(body.release_id, db)
    row = BusbarProfileORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return BusbarProfileResponse.model_validate(row)


@router.get("/busbar-profiles", response_model=PaginatedResponse[BusbarProfileResponse])
async def list_busbar_profiles(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[BusbarProfileResponse]:
    q = select(BusbarProfileORM)
    if release_id is not None:
        q = q.where(BusbarProfileORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[BusbarProfileResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/busbar-profiles/{entry_id}", response_model=BusbarProfileResponse)
async def get_busbar_profile(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusbarProfileResponse:
    result = await db.execute(select(BusbarProfileORM).where(BusbarProfileORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="BusbarProfileLibraryEntry not found.")
    return BusbarProfileResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Device endpoints
# ---------------------------------------------------------------------------


@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: DeviceCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceResponse:
    await _assert_release_mutable(body.release_id, db)
    data = body.model_dump()
    data["power_loss_curve"] = [p.model_dump() for p in body.power_loss_curve]
    row = DeviceORM(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return DeviceResponse.model_validate(row)


@router.get("/devices", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    manufacturer: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[DeviceResponse]:
    q = select(DeviceORM)
    if release_id is not None:
        q = q.where(DeviceORM.release_id == release_id)
    if manufacturer is not None:
        q = q.where(DeviceORM.manufacturer == manufacturer)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[DeviceResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/devices/{entry_id}", response_model=DeviceResponse)
async def get_device(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceResponse:
    result = await db.execute(select(DeviceORM).where(DeviceORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="DeviceLibraryEntry not found.")
    return DeviceResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Fan endpoints
# ---------------------------------------------------------------------------


@router.post("/fans", response_model=FanResponse, status_code=status.HTTP_201_CREATED)
async def create_fan(
    body: FanCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FanResponse:
    await _assert_release_mutable(body.release_id, db)
    data = body.model_dump()
    data["fan_curve"] = [p.model_dump() for p in body.fan_curve]
    row = FanORM(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return FanResponse.model_validate(row)


@router.get("/fans", response_model=PaginatedResponse[FanResponse])
async def list_fans(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[FanResponse]:
    q = select(FanORM)
    if release_id is not None:
        q = q.where(FanORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[FanResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/fans/{entry_id}", response_model=FanResponse)
async def get_fan(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FanResponse:
    result = await db.execute(select(FanORM).where(FanORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="FanLibraryEntry not found.")
    return FanResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Filter endpoints
# ---------------------------------------------------------------------------


@router.post("/filters", response_model=FilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    body: FilterCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FilterResponse:
    await _assert_release_mutable(body.release_id, db)
    row = FilterORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return FilterResponse.model_validate(row)


@router.get("/filters", response_model=PaginatedResponse[FilterResponse])
async def list_filters(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[FilterResponse]:
    q = select(FilterORM)
    if release_id is not None:
        q = q.where(FilterORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[FilterResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/filters/{entry_id}", response_model=FilterResponse)
async def get_filter(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FilterResponse:
    result = await db.execute(select(FilterORM).where(FilterORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="FilterLibraryEntry not found.")
    return FilterResponse.model_validate(row)


# ---------------------------------------------------------------------------
# VentilationOpening endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/ventilation-openings",
    response_model=VentilationOpeningResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ventilation_opening(
    body: VentilationOpeningCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VentilationOpeningResponse:
    await _assert_release_mutable(body.release_id, db)
    row = VentilationOpeningORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return VentilationOpeningResponse.model_validate(row)


@router.get("/ventilation-openings", response_model=PaginatedResponse[VentilationOpeningResponse])
async def list_ventilation_openings(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[VentilationOpeningResponse]:
    q = select(VentilationOpeningORM)
    if release_id is not None:
        q = q.where(VentilationOpeningORM.release_id == release_id)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[VentilationOpeningResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/ventilation-openings/{entry_id}", response_model=VentilationOpeningResponse)
async def get_ventilation_opening(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VentilationOpeningResponse:
    result = await db.execute(
        select(VentilationOpeningORM).where(VentilationOpeningORM.id == entry_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="VentilationOpeningLibraryEntry not found.")
    return VentilationOpeningResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Cable endpoints
# ---------------------------------------------------------------------------


@router.post("/cables", response_model=CableResponse, status_code=status.HTTP_201_CREATED)
async def create_cable(
    body: CableCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CableResponse:
    await _assert_release_mutable(body.release_id, db)
    row = CableORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CableResponse.model_validate(row)


@router.get("/cables", response_model=PaginatedResponse[CableResponse])
async def list_cables(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    conductor: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CableResponse]:
    q = select(CableORM)
    if release_id is not None:
        q = q.where(CableORM.release_id == release_id)
    if conductor is not None:
        q = q.where(CableORM.conductor == conductor)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[CableResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/cables/{entry_id}", response_model=CableResponse)
async def get_cable(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CableResponse:
    result = await db.execute(select(CableORM).where(CableORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="CableLibraryEntry not found.")
    return CableResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Connection endpoints
# ---------------------------------------------------------------------------


@router.post("/connections", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: ConnectionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectionResponse:
    await _assert_release_mutable(body.release_id, db)
    row = ConnectionORM(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ConnectionResponse.model_validate(row)


@router.get("/connections", response_model=PaginatedResponse[ConnectionResponse])
async def list_connections(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    release_id: uuid.UUID | None = Query(default=None),
    contact_quality: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ConnectionResponse]:
    q = select(ConnectionORM)
    if release_id is not None:
        q = q.where(ConnectionORM.release_id == release_id)
    if contact_quality is not None:
        q = q.where(ConnectionORM.contact_quality == contact_quality)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[ConnectionResponse.model_validate(r) for r in rows],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/connections/{entry_id}", response_model=ConnectionResponse)
async def get_connection(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectionResponse:
    result = await db.execute(select(ConnectionORM).where(ConnectionORM.id == entry_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="ConnectionLibraryEntry not found.")
    return ConnectionResponse.model_validate(row)

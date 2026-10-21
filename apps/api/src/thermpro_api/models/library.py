"""M3 engineering library entry ORM models.

All physical values stored in SI base units (CR-ENG-013).
Temperatures stored in kelvin (CR-ENG-003).
Immutability enforced at the service layer: once a release is APPROVED,
no entry may be updated or deleted (CR-ENG-012).

Compound fields (loss curves, fan curves, references tuples) are stored as
JSONB arrays for schema-free extensibility while keeping normalised rows per
entry. The `domain_entry_id` column holds the library-assigned string key
(e.g. "dev-3wl-001") distinct from the UUID primary key.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from thermpro_api.models.library_release import LibraryRelease


class MaterialLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical material specification (conductor, enclosure, coating, …)."""

    __tablename__ = "material_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_material_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    thermal_conductivity_w_per_m_k: Mapped[float] = mapped_column(Float, nullable=False)
    density_kg_per_m3: Mapped[float] = mapped_column(Float, nullable=False)
    specific_heat_j_per_kg_k: Mapped[float] = mapped_column(Float, nullable=False)
    electrical_resistivity_ohm_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_coeff_resistance_per_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    emissivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_operating_temp_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class SurfaceLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Radiative and optical surface properties."""

    __tablename__ = "surface_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_surface_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    emissivity: Mapped[float] = mapped_column(Float, nullable=False)
    absorptivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    roughness_um: Mapped[float | None] = mapped_column(Float, nullable=True)
    coating: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class BusbarProfileLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cross-sectional specification of a busbar conductor."""

    __tablename__ = "busbar_profile_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_busbar_profile_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    profile: Mapped[str] = mapped_column(String(32), nullable=False)
    coating: Mapped[str] = mapped_column(String(32), nullable=False)
    thickness_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    cross_section_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    max_continuous_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    emissivity_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class DeviceLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Switchgear device specification with power-loss curve."""

    __tablename__ = "device_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_device_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(128), nullable=False)
    family: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    rated_current_a: Mapped[float] = mapped_column(Float, nullable=False)
    poles: Mapped[int] = mapped_column(Integer, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    mounting_type: Mapped[str] = mapped_column(String(32), nullable=False)
    ventilation_requirement: Mapped[str] = mapped_column(String(64), nullable=False)
    max_ambient_temp_k: Mapped[float] = mapped_column(Float, nullable=False)
    power_loss_curve: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="[{current_fraction: float, power_loss_w: float}, ...]",
    )
    loss_confidence: Mapped[str] = mapped_column(String(64), nullable=False)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class FanLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Manufacturer fan specification with pressure-flow curve."""

    __tablename__ = "fan_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_fan_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    rated_speed_rpm: Mapped[float] = mapped_column(Float, nullable=False)
    rated_flow_m3_per_s: Mapped[float] = mapped_column(Float, nullable=False)
    rated_pressure_pa: Mapped[float] = mapped_column(Float, nullable=False)
    rated_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequency_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    fan_curve: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="[{flow_m3_per_s, static_pressure_pa, power_w, efficiency}, ...]",
    )
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class FilterLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Pressure-drop specification for ventilation filter or mat."""

    __tablename__ = "filter_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_filter_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dust_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rated_flow_m3_per_s: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_drop_pa: Mapped[float] = mapped_column(Float, nullable=False)
    loss_coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    porosity: Mapped[float | None] = mapped_column(Float, nullable=True)
    initial_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class VentilationOpeningLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Catalogue entry for ventilation accessory (louver, grille, etc.)."""

    __tablename__ = "ventilation_opening_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_ventilation_opening_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    accessory: Mapped[str] = mapped_column(String(32), nullable=False)
    gross_width_m: Mapped[float] = mapped_column(Float, nullable=False)
    gross_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    open_area_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    discharge_coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    filter_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class CableLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cable specification for heat-source contribution estimation."""

    __tablename__ = "cable_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_cable_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    conductor: Mapped[str] = mapped_column(String(32), nullable=False)
    insulation: Mapped[str] = mapped_column(String(32), nullable=False)
    conductor_cross_section_m2: Mapped[float] = mapped_column(Float, nullable=False)
    outer_diameter_m: Mapped[float] = mapped_column(Float, nullable=False)
    rated_current_a: Mapped[float] = mapped_column(Float, nullable=False)
    resistance_ohm_per_m: Mapped[float] = mapped_column(Float, nullable=False)
    temp_coeff_resistance_per_k: Mapped[float] = mapped_column(Float, nullable=False)
    max_conductor_temp_k: Mapped[float] = mapped_column(Float, nullable=False)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")


class ConnectionLibraryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Electrical joint resistance specification (DR-004 hierarchy)."""

    __tablename__ = "connection_library_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_connection_release_domain_id"
        ),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    plating: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bolt_size_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    bolt_torque_n_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    contact_pressure_pa: Mapped[float | None] = mapped_column(Float, nullable=True)
    joint_resistance_ohm: Mapped[float] = mapped_column(Float, nullable=False)
    resistance_source: Mapped[str] = mapped_column(String(64), nullable=False)
    age_factor: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    release: Mapped[LibraryRelease] = relationship("LibraryRelease")

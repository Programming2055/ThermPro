"""Geometry models — M2 enclosure and assembly spatial model."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from thermpro_api.models.project import Project


class Assembly(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Top-level grouping of one or more enclosures within a project."""

    __tablename__ = "assemblies"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    coordinate_system_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1.0"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    project: Mapped[Project] = relationship("Project")
    enclosures: Mapped[list[Enclosure]] = relationship(
        "Enclosure",
        back_populates="assembly",
        foreign_keys="[Enclosure.assembly_id]",
    )


class Enclosure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical switchboard cabinet with external and internal dimensions."""

    __tablename__ = "enclosures"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assembly_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assemblies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_width_m: Mapped[float] = mapped_column(Float, nullable=False)
    external_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    external_depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    internal_width_m: Mapped[float] = mapped_column(Float, nullable=False)
    internal_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    internal_depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    wall_thickness_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.002)
    material_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    installation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FLOOR_STANDING"
    )
    ip_rating: Mapped[str | None] = mapped_column(String(16), nullable=True)
    coordinate_system_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1.0"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    project: Mapped[Project] = relationship("Project")
    assembly: Mapped[Assembly | None] = relationship(
        "Assembly",
        back_populates="enclosures",
        foreign_keys="[Enclosure.assembly_id]",
    )
    surfaces: Mapped[list[Surface]] = relationship(
        "Surface",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    compartments: Mapped[list[Compartment]] = relationship(
        "Compartment",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    partitions: Mapped[list[Partition]] = relationship(
        "Partition",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    external_openings: Mapped[list[ExternalOpening]] = relationship(
        "ExternalOpening",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    device_placements: Mapped[list[DevicePlacement]] = relationship(
        "DevicePlacement",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    busbar_placements: Mapped[list[BusbarPlacement]] = relationship(
        "BusbarPlacement",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )
    validation_issues: Mapped[list[GeometryValidationIssue]] = relationship(
        "GeometryValidationIssue",
        back_populates="enclosure",
        cascade="all, delete-orphan",
    )


class Surface(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One of the six faces of an enclosure, with thermal boundary attributes."""

    __tablename__ = "surfaces"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    face: Mapped[str] = mapped_column(String(16), nullable=False)
    is_exposed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    material_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emissivity_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    bc_placeholder: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    enclosure: Mapped[Enclosure] = relationship("Enclosure", back_populates="surfaces")
    external_openings: Mapped[list[ExternalOpening]] = relationship(
        "ExternalOpening",
        back_populates="surface",
    )


class Compartment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spatial subdivision within an enclosure, supporting nested hierarchy."""

    __tablename__ = "compartments"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_compartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compartments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    compartment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_z_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    enclosure: Mapped[Enclosure] = relationship(
        "Enclosure", back_populates="compartments"
    )
    parent_compartment: Mapped[Compartment | None] = relationship(
        "Compartment",
        back_populates="child_compartments",
        foreign_keys="[Compartment.parent_compartment_id]",
        remote_side="[Compartment.id]",
    )
    child_compartments: Mapped[list[Compartment]] = relationship(
        "Compartment",
        back_populates="parent_compartment",
        foreign_keys="[Compartment.parent_compartment_id]",
    )


class Partition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Internal dividing panel within an enclosure."""

    __tablename__ = "partitions"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orientation: Mapped[str] = mapped_column(String(16), nullable=False)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_z_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    thickness_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.001)
    material_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_removable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    enclosure: Mapped[Enclosure] = relationship("Enclosure", back_populates="partitions")
    internal_openings: Mapped[list[InternalOpening]] = relationship(
        "InternalOpening",
        back_populates="partition",
        cascade="all, delete-orphan",
    )


class ExternalOpening(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ventilation aperture or cable entry on an enclosure face."""

    __tablename__ = "external_openings"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surface_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surfaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    gross_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_area_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    discharge_coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=0.61)
    direction: Mapped[str] = mapped_column(
        String(16), nullable=False, default="BIDIRECTIONAL"
    )
    elevation_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    has_grille: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_filter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    airflow_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    enclosure: Mapped[Enclosure] = relationship(
        "Enclosure", back_populates="external_openings"
    )
    surface: Mapped[Surface | None] = relationship(
        "Surface", back_populates="external_openings"
    )


class InternalOpening(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Aperture through a partition connecting two compartments."""

    __tablename__ = "internal_openings"

    partition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compartment_a_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compartments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    compartment_b_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compartments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    gross_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_area_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    discharge_coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=0.61)
    direction: Mapped[str] = mapped_column(
        String(16), nullable=False, default="BIDIRECTIONAL"
    )

    # Relationships
    partition: Mapped[Partition] = relationship(
        "Partition", back_populates="internal_openings"
    )
    compartment_a: Mapped[Compartment | None] = relationship(
        "Compartment",
        foreign_keys="[InternalOpening.compartment_a_id]",
    )
    compartment_b: Mapped[Compartment | None] = relationship(
        "Compartment",
        foreign_keys="[InternalOpening.compartment_b_id]",
    )


class DevicePlacement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spatial placement and bounding box of a switchgear device within an enclosure."""

    __tablename__ = "device_placements"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compartments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_library_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_z_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    rotation_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mounting_surface: Mapped[str | None] = mapped_column(String(16), nullable=True)
    clearance_x_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clearance_y_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clearance_z_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    enclosure: Mapped[Enclosure] = relationship(
        "Enclosure", back_populates="device_placements"
    )
    compartment: Mapped[Compartment | None] = relationship("Compartment")


class BusbarPlacement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spatial placement and routing of a busbar conductor within an enclosure."""

    __tablename__ = "busbar_placements"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compartments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    busbar_library_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_y_m: Mapped[float] = mapped_column(Float, nullable=False)
    position_z_m: Mapped[float] = mapped_column(Float, nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    thickness_m: Mapped[float] = mapped_column(Float, nullable=False)
    length_m: Mapped[float] = mapped_column(Float, nullable=False)
    phase_designation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    clearance_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.005)
    route_points: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    enclosure: Mapped[Enclosure] = relationship(
        "Enclosure", back_populates="busbar_placements"
    )
    compartment: Mapped[Compartment | None] = relationship("Compartment")


class GeometryValidationIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A geometry rule violation or warning recorded against an enclosure."""

    __tablename__ = "geometry_validation_issues"

    enclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enclosures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    coordinate_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    enclosure: Mapped[Enclosure] = relationship(
        "Enclosure", back_populates="validation_issues"
    )

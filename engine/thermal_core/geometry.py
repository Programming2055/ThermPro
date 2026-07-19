"""
Geometry domain types for thermpro_engine.

All dimensions are in SI base units (metres) per CR-ENG-013 and M0-10.
No thermal or airflow calculations are performed here.
No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Version constant
# ---------------------------------------------------------------------------

COORDINATE_SYSTEM_VERSION: str = "1.0"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SurfaceFace(str, Enum):
    """The six faces of a rectangular enclosure or compartment."""

    FRONT = "FRONT"
    REAR = "REAR"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"


class CompartmentType(str, Enum):
    """Functional classification of an enclosure compartment."""

    DEVICE_CHAMBER = "DEVICE_CHAMBER"
    BUSBAR_CHAMBER = "BUSBAR_CHAMBER"
    CABLE_CHAMBER = "CABLE_CHAMBER"
    AUXILIARY_CHAMBER = "AUXILIARY_CHAMBER"
    VENTILATION_CHAMBER = "VENTILATION_CHAMBER"
    CUSTOM = "CUSTOM"


class PartitionOrientation(str, Enum):
    """Orientation of an internal partition plate."""

    VERTICAL_XZ = "VERTICAL_XZ"    # parallel to XZ plane, separates Y axis
    VERTICAL_YZ = "VERTICAL_YZ"    # parallel to YZ plane, separates X axis
    HORIZONTAL_XY = "HORIZONTAL_XY"  # parallel to XY plane, separates Z axis


class OpeningDirection(str, Enum):
    """Airflow direction for an external opening (opening to ambient)."""

    INLET = "INLET"
    OUTLET = "OUTLET"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    UNKNOWN = "UNKNOWN"


class InternalOpeningDirection(str, Enum):
    """Airflow direction for an opening between internal compartments."""

    BIDIRECTIONAL = "BIDIRECTIONAL"
    CONTROLLED = "CONTROLLED"
    UNKNOWN = "UNKNOWN"


class ValidationSeverity(str, Enum):
    """Severity level for geometry validation issues."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKER = "BLOCKER"


class InstallationType(str, Enum):
    """Physical installation configuration of the switchboard assembly."""

    FLOOR_STANDING = "FLOOR_STANDING"
    WALL_MOUNTED = "WALL_MOUNTED"
    RACK_MOUNTED = "RACK_MOUNTED"
    FREESTANDING = "FREESTANDING"


# ---------------------------------------------------------------------------
# Coordinate system descriptor
# ---------------------------------------------------------------------------


@dataclass
class CoordinateSystem:
    """
    Descriptor for the coordinate reference frame used by geometry entities.

    version:
        Schema version of the coordinate convention; must equal
        COORDINATE_SYSTEM_VERSION for all current engine builds.
    origin_description:
        Human-readable description of where the origin (0, 0, 0) is located,
        e.g. "bottom-left-front corner of the enclosure base plate".
    """

    __slots__ = ("version", "origin_description")

    version: str
    origin_description: str


# ---------------------------------------------------------------------------
# Primitive geometry types
# ---------------------------------------------------------------------------


@dataclass
class Point3D:
    """
    A point in 3-D Cartesian space.

    All coordinates are in metres (SI, CR-ENG-013).
    """

    __slots__ = ("x", "y", "z")

    x: float  # metres
    y: float  # metres
    z: float  # metres


@dataclass
class Dimensions3D:
    """
    Positive, non-zero dimensions of a rectangular body.

    All values are in metres (SI, CR-ENG-013).
    Raises ValueError for any dimension that is <= 0.
    """

    __slots__ = ("width", "height", "depth")

    width: float   # metres  (X direction)
    height: float  # metres  (Z direction)
    depth: float   # metres  (Y direction)

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError(
                f"Dimensions3D.width must be > 0 (metres); got {self.width}"
            )
        if self.height <= 0:
            raise ValueError(
                f"Dimensions3D.height must be > 0 (metres); got {self.height}"
            )
        if self.depth <= 0:
            raise ValueError(
                f"Dimensions3D.depth must be > 0 (metres); got {self.depth}"
            )


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


@dataclass
class BoundingBox:
    """
    Axis-aligned bounding box defined by an origin corner and dimensions.

    origin:
        The minimum-coordinate corner of the box (in metres).
    dimensions:
        Width (X), height (Z), and depth (Y) of the box (in metres).
    """

    __slots__ = ("origin", "dimensions")

    origin: Point3D
    dimensions: Dimensions3D

    # ------------------------------------------------------------------
    # Derived corner helpers (not cached; cheap to compute)
    # ------------------------------------------------------------------

    def _max_x(self) -> float:
        return self.origin.x + self.dimensions.width

    def _max_y(self) -> float:
        return self.origin.y + self.dimensions.depth

    def _max_z(self) -> float:
        return self.origin.z + self.dimensions.height

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def contains_point(self, point: Point3D) -> bool:
        """
        Return True if *point* lies strictly inside or on the boundary of
        this bounding box.

        Comparison is inclusive on all six faces.
        """
        return (
            self.origin.x <= point.x <= self._max_x()
            and self.origin.y <= point.y <= self._max_y()
            and self.origin.z <= point.z <= self._max_z()
        )

    def overlaps(self, other: BoundingBox) -> bool:
        """
        Return True if this bounding box overlaps *other* (including touching
        faces/edges/corners).

        Two boxes overlap when their projections onto every axis overlap.
        """
        # Separation on X axis
        if self._max_x() < other.origin.x or other._max_x() < self.origin.x:
            return False
        # Separation on Y axis
        if self._max_y() < other.origin.y or other._max_y() < self.origin.y:
            return False
        # Separation on Z axis
        if self._max_z() < other.origin.z or other._max_z() < self.origin.z:
            return False
        return True


# ---------------------------------------------------------------------------
# Validation issue record
# ---------------------------------------------------------------------------


@dataclass
class GeometryValidationIssue:
    """
    A single geometry validation finding raised during model integrity checks.

    issue_id:
        Unique identifier for this issue instance (e.g. a UUID string).
    severity:
        How critical this issue is for subsequent calculations.
    entity_type:
        The kind of entity that triggered the issue (e.g. "BoundingBox",
        "Compartment", "Partition").
    entity_id:
        The identifier of the specific entity instance.
    message:
        Human-readable description of what is wrong.
    coordinate_ref:
        Optional Point3D pinpointing the location in 3-D space where the
        issue was detected.
    suggested_fix:
        Optional human-readable guidance for resolving the issue.
    rule_id:
        Identifier of the validation rule that raised this issue
        (e.g. "GEO-001").
    """

    issue_id: str
    severity: ValidationSeverity
    entity_type: str
    entity_id: str
    message: str
    coordinate_ref: Optional[Point3D]
    suggested_fix: Optional[str]
    rule_id: str

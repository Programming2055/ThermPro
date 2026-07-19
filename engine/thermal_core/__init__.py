"""
thermpro_engine -- Numerical thermal engine placeholder.

Milestone 1: Domain types and interfaces only.
No thermal physics has been implemented.
All calculation submissions return ENGINE_NOT_IMPLEMENTED.

Milestone 2: Geometry domain types added (geometry.py).
"""
__version__ = "0.1.0"

from thermal_core.geometry import (
    COORDINATE_SYSTEM_VERSION,
    BoundingBox,
    CompartmentType,
    CoordinateSystem,
    Dimensions3D,
    GeometryValidationIssue,
    InstallationType,
    InternalOpeningDirection,
    OpeningDirection,
    PartitionOrientation,
    Point3D,
    SurfaceFace,
    ValidationSeverity,
)

__all__ = [
    # geometry constants
    "COORDINATE_SYSTEM_VERSION",
    # geometry dataclasses
    "CoordinateSystem",
    "Point3D",
    "Dimensions3D",
    "BoundingBox",
    "GeometryValidationIssue",
    # geometry enums
    "SurfaceFace",
    "CompartmentType",
    "PartitionOrientation",
    "OpeningDirection",
    "InternalOpeningDirection",
    "ValidationSeverity",
    "InstallationType",
]

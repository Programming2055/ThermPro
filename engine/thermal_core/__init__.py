"""
thermpro_engine -- Numerical thermal engine.

Milestone 1: Domain types and interfaces.
Milestone 2: Geometry domain types (geometry.py).
Milestone 3: Engineering libraries and heat source model (libraries.py,
             heat_source.py, loss_models.py).
"""
__version__ = "0.3.0"

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
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    HeatSourceMap,
    LossBreakdown,
    LossCalculationSource,
)
from thermal_core.libraries import (
    BusbarCoating,
    BusbarProfile,
    BusbarProfileLibraryEntry,
    CableConductor,
    CableInsulation,
    CableLibraryEntry,
    ConnectionLibraryEntry,
    ContactQuality,
    DeviceLibraryEntry,
    FanCurvePoint,
    FanDirection,
    FanLibraryEntry,
    FilterLibraryEntry,
    LossConfidence,
    LossCurvePoint,
    MaterialCategory,
    MaterialLibraryEntry,
    MountingType,
    OpeningAccessory,
    SurfaceLibraryEntry,
    VentilationOpeningLibraryEntry,
    VentilationRequirement,
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
    # heat source
    "HeatSource",
    "HeatSourceEntityType",
    "HeatSourceMap",
    "LossBreakdown",
    "LossCalculationSource",
    # library types
    "LossConfidence",
    "LossCurvePoint",
    "FanCurvePoint",
    "MaterialCategory",
    "BusbarProfile",
    "BusbarCoating",
    "MountingType",
    "VentilationRequirement",
    "ContactQuality",
    "FanDirection",
    "OpeningAccessory",
    "CableConductor",
    "CableInsulation",
    # library entries
    "MaterialLibraryEntry",
    "SurfaceLibraryEntry",
    "BusbarProfileLibraryEntry",
    "DeviceLibraryEntry",
    "FanLibraryEntry",
    "FilterLibraryEntry",
    "VentilationOpeningLibraryEntry",
    "CableLibraryEntry",
    "ConnectionLibraryEntry",
]

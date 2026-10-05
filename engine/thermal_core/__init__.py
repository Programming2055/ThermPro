"""
thermpro_engine -- Numerical thermal engine.

Milestone 1: Domain types and interfaces.
Milestone 2: Geometry domain types (geometry.py).
Milestone 3: Engineering libraries and heat source model (libraries.py,
             heat_source.py, loss_models.py).
Milestone 4: Thermal physics solver (snapshot.py, result.py, solver/, materials/,
             conduction/, natural_convection/, radiation/, airflow/, benchmarks/).
"""
__version__ = "0.4.0"

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
    HeatSourceGenerationType,
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
from thermal_core.result import (
    CompartmentResult,
    ConvergenceTrace,
    NodeTemperature,
    ResultSnapshot,
    SolverStatus,
    SolverWarning,
)
from thermal_core.snapshot import (
    BoundaryConditions,
    CalculationMode,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    OpeningSnapshot,
    SolverSettings,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.solver.iterative import ZonalSolver, solve

__all__ = [
    # geometry constants
    "COORDINATE_SYSTEM_VERSION",
    "BoundaryConditions",
    "BoundingBox",
    "BusbarCoating",
    "BusbarProfile",
    "BusbarProfileLibraryEntry",
    "CableConductor",
    "CableInsulation",
    "CableLibraryEntry",
    "CalculationMode",
    "CompartmentResult",
    "CompartmentSnapshot",
    "CompartmentType",
    "ConnectionLibraryEntry",
    "ContactQuality",
    "ConvergenceTrace",
    # geometry dataclasses
    "CoordinateSystem",
    "DeviceLibraryEntry",
    "Dimensions3D",
    "FanCurvePoint",
    "FanDirection",
    "FanLibraryEntry",
    "FilterLibraryEntry",
    "GeometrySnapshot",
    "GeometryValidationIssue",
    # heat source (M3)
    "HeatSource",
    "HeatSourceEntityType",
    "HeatSourceGenerationType",
    "HeatSourceMap",
    # solver inputs (M4)
    "InputSnapshot",
    "InstallationType",
    "InternalOpeningDirection",
    "LossBreakdown",
    "LossCalculationSource",
    # library types
    "LossConfidence",
    "LossCurvePoint",
    "MaterialCategory",
    # library entries
    "MaterialLibraryEntry",
    "MountingType",
    "NodeTemperature",
    "OpeningAccessory",
    "OpeningDirection",
    "OpeningSnapshot",
    "PartitionOrientation",
    "Point3D",
    # solver results (M4)
    "ResultSnapshot",
    "SolverSettings",
    "SolverStatus",
    "SolverWarning",
    # geometry enums
    "SurfaceFace",
    "SurfaceLibraryEntry",
    "SurfaceOrientation",
    "SurfaceSnapshot",
    "ValidationSeverity",
    "VentilationOpeningLibraryEntry",
    "VentilationRequirement",
    # solver (M4)
    "ZonalSolver",
    "solve",
]

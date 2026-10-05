"""SQLAlchemy ORM models for thermpro_api."""
from thermpro_api.models.artifact import CalculationArtifact
from thermpro_api.models.audit_event import AuditEvent
from thermpro_api.models.calculation_run import CalculationRun
from thermpro_api.models.dataset_manifest import DatasetManifest, DatasetManifestEntry
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
from thermpro_api.models.library import (
    BusbarProfileLibraryEntry,
    CableLibraryEntry,
    ConnectionLibraryEntry,
    DeviceLibraryEntry,
    FanLibraryEntry,
    FilterLibraryEntry,
    MaterialLibraryEntry,
    SurfaceLibraryEntry,
    VentilationOpeningLibraryEntry,
)
from thermpro_api.models.library_release import LibraryRelease, LibraryReleaseFile
from thermpro_api.models.project import Project
from thermpro_api.models.user import User

__all__ = [
    # M2 geometry
    "Assembly",
    "AuditEvent",
    "BusbarPlacement",
    "BusbarProfileLibraryEntry",
    "CableLibraryEntry",
    "CalculationArtifact",
    "CalculationRun",
    "Compartment",
    "ConnectionLibraryEntry",
    "DatasetManifest",
    "DatasetManifestEntry",
    "DeviceLibraryEntry",
    "DevicePlacement",
    "Enclosure",
    "ExternalOpening",
    "FanLibraryEntry",
    "FilterLibraryEntry",
    "GeometryValidationIssue",
    "InternalOpening",
    "LibraryRelease",
    "LibraryReleaseFile",
    # M3 library entries
    "MaterialLibraryEntry",
    "Partition",
    "Project",
    "Surface",
    "SurfaceLibraryEntry",
    "User",
    "VentilationOpeningLibraryEntry",
]

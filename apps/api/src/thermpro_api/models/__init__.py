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
    "User",
    "Project",
    "LibraryRelease",
    "LibraryReleaseFile",
    "DatasetManifest",
    "DatasetManifestEntry",
    "CalculationRun",
    "CalculationArtifact",
    "AuditEvent",
    # M2 geometry
    "Assembly",
    "Enclosure",
    "Surface",
    "Compartment",
    "Partition",
    "ExternalOpening",
    "InternalOpening",
    "DevicePlacement",
    "BusbarPlacement",
    "GeometryValidationIssue",
    # M3 library entries
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

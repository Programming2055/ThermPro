"""
The M0-03 → engine → M0-04 JSON contract (CR-TECH-001).

`thermpro_engine` takes a versioned JSON document and returns a versioned JSON
document. It never queries a database, a library or an HTTP service; everything
the physics needs — resistivities, loss coefficients, fan curves, contact
resistances — arrives inlined on the InputSnapshot, resolved at the API
boundary before the engine is called.

This module is that boundary:

  * `input_snapshot_from_json` maps an M0-03 document onto the engine's own
    `InputSnapshot`, building the enclosure's six external faces, the internal
    partitions, the ventilation openings and one `HeatSource` per device,
    busbar segment, busbar joint, conductor and fan motor;
  * `result_to_json` maps a solved `ResultSnapshot`, with its compliance
    interpretation, back onto an M0-04 document;
  * `solve_json` does both, and `JsonThermalSolver` exposes it as the
    `ThermalSolverInterface` the API layer depends on.

Unit conversion happens here and nowhere else (CR-ENG-013, M0-10): the M0-03
document speaks °C, the engine speaks kelvin (CR-ENG-003), and the M0-04
document reports both.

Coordinate convention (M0-01, docs/07-data-model.md §4): the origin is the
bottom-left-front corner, x runs along the enclosure width, y along its depth
and z vertically upward.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from thermal_core import __version__ as _engine_version
from thermal_core.benchmarks.iec60890 import (
    IEC60890Coefficients,
    check_iec60890_applicability,
)
from thermal_core.compliance import (
    ComplianceReport,
    LimitSet,
    StandardProfile,
    evaluate_compliance,
    iec_61439_limit_set,
)
from thermal_core.forced_convection.fan_model import FanCurvePoint, fan_operating_point
from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    HeatSourceGenerationType,
    HeatSourceMap,
    LossBreakdown,
    LossCalculationSource,
)
from thermal_core.interfaces import ThermalSolverInterface
from thermal_core.libraries import LossConfidence
from thermal_core.materials.air_properties import air_at
from thermal_core.result import NodeType, ResultSnapshot, SolverStatus
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
from thermal_core.solver.iterative import ZonalSolver, surface_outer_node

ENGINE_VERSION = _engine_version
"""Semantic version of thermpro_engine, echoed into every M0-04 result."""

CONTRACT_SCHEMA_VERSION = "1.0"
"""The only M0-03 / M0-04 schema version this adapter speaks."""

KELVIN_OFFSET = 273.15

# Namespace for deriving a deterministic run_id from the input document, so
# that solving the same input twice produces the same record (rule 6).
_RUN_ID_NAMESPACE = uuid.UUID("6f1d0f1e-6c2b-5a3e-9d44-7f0b2c8a1e55")

_DEFAULT_DISCHARGE_COEFFICIENT = 0.6
_DEFAULT_FAN_FREE_AREA_M2 = 0.01

# Fan states that pass no air at all: a closed damper or a blocked rotor.
_BLOCKING_FAN_STATES = frozenset({"STOPPED_WITH_DAMPER", "FAILED_BLOCKED"})
# Fan states that drive air. REVERSE_FLOW_ESTIMATED drives it the other way,
# which DR-005 requires be reported rather than clamped to zero.
_DRIVING_FAN_STATES = frozenset({"RUNNING_FORWARD", "REVERSE_FLOW_ESTIMATED"})

_CONFIDENCE_BY_DATA_CONFIDENCE = {
    "HIGH": LossConfidence.MANUFACTURER_CERTIFIED,
    "MEDIUM": LossConfidence.MANUFACTURER_TYPICAL,
    "LOW": LossConfidence.ESTIMATED,
    "UNKNOWN": LossConfidence.ASSUMED_DEFAULT,
}

# M0-04 calls the entity types by the name of the engineering object; the
# engine thinks in node types. This is the only place the two meet.
_M004_ENTITY_TYPE_BY_NODE_TYPE = {
    NodeType.DEVICE: "DEVICE",
    NodeType.BUSBAR: "BUSBAR_SEGMENT",
    NodeType.JOINT: "BUSBAR_JOINT",
    NodeType.CABLE: "CONDUCTOR",
    NodeType.SURFACE: "SURFACE",
}

# Geometric tolerance for deciding that a compartment reaches an enclosure
# face or abuts another compartment. Generous on purpose: whether a
# compartment is specified in interior or exterior coordinates should not
# change which wall it is behind.
_GEOMETRIC_TOLERANCE_M = 1e-6


class ContractError(ValueError):
    """
    Raised when an M0-03 document cannot be mapped onto a solvable model.

    This is a *mapping* failure — a missing resistivity, a joint with no
    contact resistance — not a solver failure. The caller should report it as
    an invalid input rather than as a thermal result.
    """

    def __init__(self, message: str, errors: Sequence[str] | None = None) -> None:
        super().__init__(message)
        self.errors: tuple[str, ...] = tuple(errors or (message,))


# ---------------------------------------------------------------------------
# Typed accessors — the payload is JSON, so everything arrives as Any
# ---------------------------------------------------------------------------


def _obj(parent: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ContractError(f"{where}.{key} must be an object")
    return value


def _objects(parent: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = parent.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContractError(f"{key} must be an array")
    out: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ContractError(f"{key}[{index}] must be an object")
        out.append(item)
    return out


def _req_str(parent: Mapping[str, Any], key: str, where: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value:
        raise ContractError(f"{where}.{key} is required and must be a non-empty string")
    return value


def _opt_str(parent: Mapping[str, Any], key: str) -> str | None:
    value = parent.get(key)
    return value if isinstance(value, str) and value else None


def _req_float(parent: Mapping[str, Any], key: str, where: str) -> float:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{where}.{key} is required and must be a number")
    return float(value)


def _opt_float(parent: Mapping[str, Any], key: str) -> float | None:
    value = parent.get(key)
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _float_or(parent: Mapping[str, Any], key: str, default: float) -> float:
    value = _opt_float(parent, key)
    return default if value is None else value


def _bool_or(parent: Mapping[str, Any], key: str, default: bool) -> bool:
    value = parent.get(key)
    return value if isinstance(value, bool) else default


# ---------------------------------------------------------------------------
# Boxes — the geometry the M0-03 document describes by position and size
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Box:
    """An axis-aligned box in enclosure coordinates [m]."""

    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float

    @property
    def centre(self) -> tuple[float, float, float]:
        return (
            0.5 * (self.x0 + self.x1),
            0.5 * (self.y0 + self.y1),
            0.5 * (self.z0 + self.z1),
        )

    def contains(self, x: float, y: float, z: float) -> bool:
        return (
            self.x0 - _GEOMETRIC_TOLERANCE_M <= x <= self.x1 + _GEOMETRIC_TOLERANCE_M
            and self.y0 - _GEOMETRIC_TOLERANCE_M <= y <= self.y1 + _GEOMETRIC_TOLERANCE_M
            and self.z0 - _GEOMETRIC_TOLERANCE_M <= z <= self.z1 + _GEOMETRIC_TOLERANCE_M
        )

    def distance_to(self, x: float, y: float, z: float) -> float:
        dx = max(self.x0 - x, 0.0, x - self.x1)
        dy = max(self.y0 - y, 0.0, y - self.y1)
        dz = max(self.z0 - z, 0.0, z - self.z1)
        return math.sqrt(dx * dx + dy * dy + dz * dz)


@dataclass(frozen=True)
class _Face:
    """One of the six external faces of the enclosure."""

    name: str
    area_m2: float
    orientation: SurfaceOrientation


@dataclass(frozen=True)
class _Adjacency:
    """Two compartments sharing a plane, and the area they share."""

    compartment_a: str
    compartment_b: str
    axis: str  # "x", "y" or "z"
    plane_coordinate_m: float
    overlap_area_m2: float
    centroid_height_m: float

    @property
    def key(self) -> tuple[str, str]:
        return (
            min(self.compartment_a, self.compartment_b),
            max(self.compartment_a, self.compartment_b),
        )


# ---------------------------------------------------------------------------
# The mapped input
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractInput:
    """
    An M0-03 document mapped onto the engine's own types.

    Beyond the `InputSnapshot` the solver consumes, this carries the lookup
    tables the result mapping needs to speak about the engineer's own objects
    rather than about internal node ids.
    """

    snapshot: InputSnapshot
    mode: str
    standard_profile: tuple[str, ...]
    #: entity_id → M0-04 entity_type.
    entity_types: dict[str, str]
    #: entity_id → absolute maximum permissible temperature [K].
    entity_limits_k: dict[str, float]
    #: entity_id → present load current / rated current.
    entity_loading_factors: dict[str, float]
    #: compartment_id → centroid, for the M0-04 thermal cells.
    compartment_centres_m: dict[str, tuple[float, float, float]]
    #: Problems found while mapping that do not prevent a solve.
    warnings: tuple[tuple[str, str], ...] = ()
    #: Reasons the requested mode may not be used at all.
    blocking_reasons: tuple[str, ...] = ()


def input_snapshot_from_json(
    payload: Mapping[str, Any],
    *,
    run_id: str | None = None,
    iec60890_coefficients: IEC60890Coefficients | None = None,
) -> ContractInput:
    """
    Map an M0-03 InputSnapshot document onto the engine's `InputSnapshot`.

    Parameters
    ----------
    payload:
        An M0-03 document. Validate it against the JSON Schema first
        (`thermpro_schemas.validate_input_snapshot`); this function assumes the
        shape is right and checks only what the schema cannot express, such as
        a conductor whose resistance was never resolved.
    run_id:
        The calculation's identity. When omitted it is derived deterministically
        from the document, so the same input always yields the same run_id.
    iec60890_coefficients:
        The licensed IEC TR 60890 dataset, required for MODE_1 and never
        shipped in this repository (CR-ENG-002).

    Raises
    ------
    ContractError
        If the document cannot be mapped onto a solvable model.
    """
    version = payload.get("schema_version")
    if version != CONTRACT_SCHEMA_VERSION:
        raise ContractError(
            f"Unsupported InputSnapshot schema_version {version!r}; this engine "
            f"speaks {CONTRACT_SCHEMA_VERSION!r}."
        )

    mode = _req_str(payload, "mode", "input")
    enclosure = _obj(payload, "enclosure", "input")
    service = _obj(payload, "service_conditions", "input")
    settings_json = _obj(payload, "solver_settings", "input")

    warnings: list[tuple[str, str]] = []
    builder = _GeometryBuilder(enclosure, warnings)
    geometry, forced_flows, fan_sources = builder.build(mode)

    sources: list[HeatSource] = list(fan_sources)
    entity_types: dict[str, str] = dict(builder.fan_entity_types)
    entity_limits_k: dict[str, float] = {}
    loading_factors: dict[str, float] = {}

    sources.extend(
        _device_sources(
            enclosure, builder, entity_types, entity_limits_k, loading_factors, warnings
        )
    )
    sources.extend(
        _busbar_sources(enclosure, builder, entity_types, loading_factors, warnings)
    )
    sources.extend(
        _conductor_sources(enclosure, builder, entity_types, loading_factors, warnings)
    )

    geometry = builder.attach_sources(geometry, sources)

    t_amb_k = _req_float(service, "ambient_temperature_max_C", "service_conditions") + (
        KELVIN_OFFSET
    )
    boundary = BoundaryConditions(
        ambient_temperature_k=t_amb_k,
        ambient_pressure_pa=_altitude_pressure_pa(_float_or(service, "altitude_m", 0.0)),
        ambient_relative_humidity=(
            _float_or(service, "relative_humidity_max_percent", 50.0) / 100.0
        ),
        forced_flow_m3_per_s=forced_flows,
    )

    solver_settings = SolverSettings(
        calculation_mode=CalculationMode(mode),
        max_iterations=int(_float_or(settings_json, "max_inner_iterations", 200.0)),
        convergence_tolerance_k=_float_or(settings_json, "convergence_T_K", 0.01),
        relaxation_factor=_float_or(settings_json, "relaxation_factor", 0.7),
        enable_ventilation=mode != "MODE_1",
        t_ref_k=t_amb_k,
    )

    blocking = _mode_blocking_reasons(mode, builder, enclosure, sources)

    snapshot = InputSnapshot(
        schema_version=CONTRACT_SCHEMA_VERSION,
        library_manifest=_library_manifest(payload),
        calculation_id=run_id or _derive_run_id(payload),
        geometry=geometry,
        heat_source_map=HeatSourceMap(
            enclosure_id=geometry.enclosure_id,
            sources=sources,
            library_manifest=_library_manifest(payload),
        ),
        boundary_conditions=boundary,
        solver_settings=solver_settings,
        iec60890_coefficients=iec60890_coefficients,
    )

    profiles = payload.get("standard_profile")
    profile_tuple = (
        tuple(p for p in profiles if isinstance(p, str))
        if isinstance(profiles, list)
        else ()
    )

    return ContractInput(
        snapshot=snapshot,
        mode=mode,
        standard_profile=profile_tuple or ("IEC_61439_2",),
        entity_types=entity_types,
        entity_limits_k=entity_limits_k,
        entity_loading_factors=loading_factors,
        compartment_centres_m=builder.compartment_centres,
        warnings=tuple(warnings),
        blocking_reasons=blocking,
    )


def _library_manifest(payload: Mapping[str, Any]) -> dict[str, str]:
    """Flatten the pinned library versions into library_type → version@hash."""
    manifest = payload.get("library_manifest")
    out: dict[str, str] = {}
    if not isinstance(manifest, Mapping):
        return out
    for name, pin in manifest.items():
        if not isinstance(pin, Mapping):
            continue
        version = pin.get("version")
        digest = pin.get("content_hash_sha256")
        if isinstance(version, str) and isinstance(digest, str):
            out[str(name)] = f"{version}@{digest}"
        elif isinstance(version, str):
            out[str(name)] = version
    return out


def _derive_run_id(payload: Mapping[str, Any]) -> str:
    """
    A run_id derived from the document itself.

    An explicit id from the API layer is preferred; this fallback keeps the
    engine deterministic when it is called directly, for instance from a test
    or a batch study, instead of minting a fresh random id each time.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return str(uuid.uuid5(_RUN_ID_NAMESPACE, canonical))


def _altitude_pressure_pa(altitude_m: float) -> float:
    """
    Barometric pressure at installation altitude [Pa] — ISA troposphere.

        p = p_0 · (1 − 2.25577×10⁻⁵ · h)^5.25588

    Air density falls with altitude, which weakens natural convection; IEC
    61439-1 clause 7.1.2 derates above 2000 m for the same reason.
    """
    if altitude_m <= 0.0:
        return 101325.0
    return 101325.0 * float((1.0 - 2.25577e-5 * altitude_m) ** 5.25588)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


class _GeometryBuilder:
    """
    Turns the M0-03 `enclosure` object into a `GeometrySnapshot`.

    The M0-03 document describes an enclosure the way a panel builder does:
    outside dimensions, a wall thickness, compartments at coordinates,
    partitions and louvres. The solver wants surfaces with areas and
    orientations, and openings between named compartments. Reconciling the two
    is this class's whole job.
    """

    def __init__(
        self, enclosure: Mapping[str, Any], warnings: list[tuple[str, str]]
    ) -> None:
        self._enclosure = enclosure
        self._warnings = warnings

        self.enclosure_id = _req_str(enclosure, "id", "enclosure")
        self.width_m = _req_float(enclosure, "external_width_m", "enclosure")
        self.depth_m = _req_float(enclosure, "external_depth_m", "enclosure")
        self.height_m = _req_float(enclosure, "external_height_m", "enclosure")
        self.wall_thickness_m = _req_float(enclosure, "wall_thickness_m", "enclosure")
        self.wall_k_w_per_m_k = _req_float(
            enclosure, "wall_thermal_conductivity_W_mK", "enclosure"
        )
        self.emissivity = _req_float(enclosure, "paint_emissivity", "enclosure")

        restricted = enclosure.get("restricted_surfaces")
        self.restricted_faces = frozenset(
            f for f in (restricted or []) if isinstance(f, str)
        )

        self.boxes: dict[str, _Box] = {}
        self.compartment_centres: dict[str, tuple[float, float, float]] = {}
        self.fan_entity_types: dict[str, str] = {}
        self._compartment_order: list[str] = []
        self._adjacencies: list[_Adjacency] = []
        self._openings: list[OpeningSnapshot] = []
        self._partitioned_pairs: set[tuple[str, str]] = set()
        self._partition_adjacency: dict[str, _Adjacency] = {}
        self._has_driving_fan = False

    # -- public -----------------------------------------------------------

    def build(
        self, mode: str
    ) -> tuple[GeometrySnapshot, dict[str, float], list[HeatSource]]:
        """Build the geometry, the forced flows and the fan motor losses."""
        compartments = self._compartments()
        surfaces = self._external_surfaces(compartments)
        self._adjacencies = self._find_adjacencies()
        surfaces.extend(self._partition_surfaces())
        self._openings.extend(self._internal_openings())
        self._openings.extend(self._external_openings())
        forced_flows, fan_sources = self._fans(mode)

        self._warn_about_unseparated_compartments()

        geometry = GeometrySnapshot(
            enclosure_id=self.enclosure_id,
            total_height_m=self.height_m,
            total_external_surface_area_m2=sum(f.area_m2 for f in self._faces()),
            compartments=tuple(compartments),
            surfaces=tuple(surfaces),
            openings=tuple(self._openings),
        )
        return geometry, forced_flows, fan_sources

    def attach_sources(
        self, geometry: GeometrySnapshot, sources: Sequence[HeatSource]
    ) -> GeometrySnapshot:
        """Re-emit the geometry with each compartment's heat-source ids filled in."""
        by_compartment: dict[str, list[str]] = {c: [] for c in self._compartment_order}
        for source in sources:
            if source.compartment_id in by_compartment:
                by_compartment[source.compartment_id].append(source.source_id)

        compartments = tuple(
            CompartmentSnapshot(
                compartment_id=c.compartment_id,
                volume_m3=c.volume_m3,
                height_m=c.height_m,
                width_m=c.width_m,
                depth_m=c.depth_m,
                surface_ids=c.surface_ids,
                heat_source_ids=tuple(by_compartment.get(c.compartment_id, ())),
            )
            for c in geometry.compartments
        )
        return GeometrySnapshot(
            enclosure_id=geometry.enclosure_id,
            total_height_m=geometry.total_height_m,
            total_external_surface_area_m2=geometry.total_external_surface_area_m2,
            compartments=compartments,
            surfaces=geometry.surfaces,
            openings=geometry.openings,
        )

    def compartment_for_point(
        self, x: float, y: float, z: float, declared: str | None = None
    ) -> str:
        """
        Which compartment an entity at (x, y, z) belongs to.

        A declared compartment_id always wins; otherwise the point is placed in
        the compartment that contains it, or failing that in the nearest one.
        """
        if declared is not None and declared in self.boxes:
            return declared
        for compartment_id in self._compartment_order:
            if self.boxes[compartment_id].contains(x, y, z):
                return compartment_id
        return min(
            self._compartment_order,
            key=lambda cid: self.boxes[cid].distance_to(x, y, z),
        )

    @property
    def has_driving_fan(self) -> bool:
        """True when at least one fan is actually moving air."""
        return self._has_driving_fan

    # -- compartments -----------------------------------------------------

    def _interior_box(self) -> _Box:
        t = self.wall_thickness_m
        return _Box(
            x0=t,
            y0=t,
            z0=t,
            x1=max(self.width_m - t, t + _GEOMETRIC_TOLERANCE_M),
            y1=max(self.depth_m - t, t + _GEOMETRIC_TOLERANCE_M),
            z1=max(self.height_m - t, t + _GEOMETRIC_TOLERANCE_M),
        )

    def _compartments(self) -> list[CompartmentSnapshot]:
        declared = _objects(self._enclosure, "compartments")
        if not declared:
            # An enclosure with no declared compartments is one open volume.
            # Modelling it as a single compartment is exact, not an
            # approximation: there is nothing inside to divide it.
            box = self._interior_box()
            compartment_id = f"{self.enclosure_id}:interior"
            self.boxes[compartment_id] = box
            self.compartment_centres[compartment_id] = box.centre
            self._compartment_order.append(compartment_id)
            return [
                CompartmentSnapshot(
                    compartment_id=compartment_id,
                    volume_m3=(box.x1 - box.x0) * (box.y1 - box.y0) * (box.z1 - box.z0),
                    height_m=box.z1 - box.z0,
                    width_m=box.x1 - box.x0,
                    depth_m=box.y1 - box.y0,
                    surface_ids=(),
                    heat_source_ids=(),
                )
            ]

        out: list[CompartmentSnapshot] = []
        for item in declared:
            compartment_id = _req_str(item, "id", "compartment")
            x0 = _req_float(item, "position_x_m", "compartment")
            y0 = _req_float(item, "position_y_m", "compartment")
            z0 = _req_float(item, "position_z_m", "compartment")
            width = _req_float(item, "width_m", "compartment")
            depth = _req_float(item, "depth_m", "compartment")
            height = _req_float(item, "height_m", "compartment")
            box = _Box(x0, y0, z0, x0 + width, y0 + depth, z0 + height)
            self.boxes[compartment_id] = box
            self.compartment_centres[compartment_id] = box.centre
            self._compartment_order.append(compartment_id)
            out.append(
                CompartmentSnapshot(
                    compartment_id=compartment_id,
                    volume_m3=width * depth * height,
                    height_m=height,
                    width_m=width,
                    depth_m=depth,
                    surface_ids=(),
                    heat_source_ids=(),
                )
            )
        return out

    # -- external faces ---------------------------------------------------

    def _faces(self) -> tuple[_Face, ...]:
        w, d, h = self.width_m, self.depth_m, self.height_m
        return (
            _Face("FRONT", w * h, SurfaceOrientation.VERTICAL),
            _Face("REAR", w * h, SurfaceOrientation.VERTICAL),
            _Face("LEFT", d * h, SurfaceOrientation.VERTICAL),
            _Face("RIGHT", d * h, SurfaceOrientation.VERTICAL),
            _Face("TOP", w * d, SurfaceOrientation.HORIZONTAL_UP),
            _Face("BOTTOM", w * d, SurfaceOrientation.HORIZONTAL_DOWN),
        )

    def _face_contact_area_m2(self, face: str, box: _Box) -> float:
        """
        How much of `face` this compartment sits behind [m²].

        Zero when the compartment does not reach that wall — a lower tier does
        not touch the roof, and pretending otherwise would hand it a cooling
        surface it does not have.
        """
        tol = self.wall_thickness_m + _GEOMETRIC_TOLERANCE_M
        if face == "FRONT":
            return (box.x1 - box.x0) * (box.z1 - box.z0) if box.y0 <= tol else 0.0
        if face == "REAR":
            return (
                (box.x1 - box.x0) * (box.z1 - box.z0)
                if box.y1 >= self.depth_m - tol
                else 0.0
            )
        if face == "LEFT":
            return (box.y1 - box.y0) * (box.z1 - box.z0) if box.x0 <= tol else 0.0
        if face == "RIGHT":
            return (
                (box.y1 - box.y0) * (box.z1 - box.z0)
                if box.x1 >= self.width_m - tol
                else 0.0
            )
        if face == "BOTTOM":
            return (box.x1 - box.x0) * (box.y1 - box.y0) if box.z0 <= tol else 0.0
        return (
            (box.x1 - box.x0) * (box.y1 - box.y0)
            if box.z1 >= self.height_m - tol
            else 0.0
        )

    def _face_shares(self, face: str) -> list[tuple[str, float]]:
        """Compartment ids and their fractions of one external face."""
        contacts = [
            (cid, self._face_contact_area_m2(face, self.boxes[cid]))
            for cid in self._compartment_order
        ]
        total = sum(area for _, area in contacts)
        if total <= 0.0:
            # No compartment reaches this wall — the nearest one still has to
            # own it, or the enclosure would lose part of its cooling surface.
            nearest = min(
                self._compartment_order,
                key=lambda cid: self._distance_to_face(face, self.boxes[cid]),
            )
            return [(nearest, 1.0)]
        return [(cid, area / total) for cid, area in contacts if area > 0.0]

    def _distance_to_face(self, face: str, box: _Box) -> float:
        if face == "FRONT":
            return box.y0
        if face == "REAR":
            return self.depth_m - box.y1
        if face == "LEFT":
            return box.x0
        if face == "RIGHT":
            return self.width_m - box.x1
        if face == "BOTTOM":
            return box.z0
        return self.height_m - box.z1

    def _external_surfaces(
        self, compartments: list[CompartmentSnapshot]
    ) -> list[SurfaceSnapshot]:
        surface_ids: dict[str, list[str]] = {
            c.compartment_id: [] for c in compartments
        }
        surfaces: list[SurfaceSnapshot] = []

        for face in self._faces():
            for compartment_id, share in self._face_shares(face.name):
                area = face.area_m2 * share
                if area <= 0.0:
                    continue
                surface_id = f"{self.enclosure_id}:{face.name}:{compartment_id}"
                surfaces.append(
                    SurfaceSnapshot(
                        surface_id=surface_id,
                        compartment_id=compartment_id,
                        area_m2=area,
                        orientation=face.orientation,
                        emissivity=self.emissivity,
                        thickness_m=self.wall_thickness_m,
                        thermal_conductivity_w_per_m_k=self.wall_k_w_per_m_k,
                        is_external=True,
                        internal_emissivity=self.emissivity,
                        is_restricted=face.name in self.restricted_faces,
                    )
                )
                surface_ids[compartment_id].append(surface_id)

        # CompartmentSnapshot is frozen, so the surface back-references are
        # written by rebuilding the tuple rather than mutating it.
        for index, compartment in enumerate(compartments):
            compartments[index] = CompartmentSnapshot(
                compartment_id=compartment.compartment_id,
                volume_m3=compartment.volume_m3,
                height_m=compartment.height_m,
                width_m=compartment.width_m,
                depth_m=compartment.depth_m,
                surface_ids=tuple(surface_ids[compartment.compartment_id]),
                heat_source_ids=compartment.heat_source_ids,
            )
        return surfaces

    # -- internal partitions ----------------------------------------------

    def _find_adjacencies(self) -> list[_Adjacency]:
        """Every pair of compartments that share a plane, and how much of it."""
        out: list[_Adjacency] = []
        order = self._compartment_order
        for i, a_id in enumerate(order):
            for b_id in order[i + 1 :]:
                adjacency = self._adjacency_between(a_id, b_id)
                if adjacency is not None:
                    out.append(adjacency)
        return out

    def _adjacency_between(self, a_id: str, b_id: str) -> _Adjacency | None:
        a, b = self.boxes[a_id], self.boxes[b_id]
        tol = _GEOMETRIC_TOLERANCE_M

        spans = {
            "x": ((a.x0, a.x1), (b.x0, b.x1)),
            "y": ((a.y0, a.y1), (b.y0, b.y1)),
            "z": ((a.z0, a.z1), (b.z0, b.z1)),
        }
        for axis, ((a0, a1), (b0, b1)) in spans.items():
            if abs(a1 - b0) <= tol:
                plane = 0.5 * (a1 + b0)
            elif abs(b1 - a0) <= tol:
                plane = 0.5 * (b1 + a0)
            else:
                continue

            others = [k for k in ("x", "y", "z") if k != axis]
            overlaps = []
            for other in others:
                (p0, p1), (q0, q1) = spans[other]
                overlaps.append(max(0.0, min(p1, q1) - max(p0, q0)))
            area = overlaps[0] * overlaps[1]
            if area <= 0.0:
                continue

            if axis == "z":
                height = plane
            else:
                low = max(a.z0, b.z0)
                high = min(a.z1, b.z1)
                height = 0.5 * (low + high)
            return _Adjacency(
                compartment_a=a_id,
                compartment_b=b_id,
                axis=axis,
                plane_coordinate_m=plane,
                overlap_area_m2=area,
                centroid_height_m=max(height, 0.0),
            )
        return None

    def _adjacencies_for(self, compartment_id: str) -> list[_Adjacency]:
        return [
            adj
            for adj in self._adjacencies
            if compartment_id in (adj.compartment_a, adj.compartment_b)
        ]

    def _partition_surfaces(self) -> list[SurfaceSnapshot]:
        """
        One conduction surface per *declared* partition.

        A partition is created only where the M0-03 document says there is
        one. Two compartments that merely abut get no conduction path: a heat
        route the engineer never drew is the kind of error that quietly cools
        a hot compartment, and understating a temperature rise is the one
        failure mode this platform must not have.
        """
        surfaces: list[SurfaceSnapshot] = []
        consumed: set[tuple[str, str]] = set()

        for compartment in _objects(self._enclosure, "compartments"):
            owner = _req_str(compartment, "id", "compartment")
            declared = _objects(compartment, "partitions")
            if not declared:
                continue

            candidates = sorted(
                self._adjacencies_for(owner), key=lambda a: a.plane_coordinate_m
            )
            by_axis: dict[str, list[_Adjacency]] = {"x": [], "y": [], "z": []}
            for candidate in candidates:
                by_axis[candidate.axis].append(candidate)

            for partition in sorted(
                declared, key=lambda p: _float_or(p, "position_m", 0.0)
            ):
                partition_id = _req_str(partition, "id", "partition")
                orientation = _req_str(partition, "orientation", "partition")
                # A HORIZONTAL partition separates compartments stacked along
                # z; a VERTICAL one separates them along x or y.
                axes = ("z",) if orientation == "HORIZONTAL" else ("x", "y")
                adjacency = _take_adjacency(by_axis, axes, consumed)
                if adjacency is None:
                    self._warnings.append(
                        (
                            "WARN-PARTITION-UNMATCHED",
                            f"Partition {partition_id!r} in compartment {owner!r} "
                            f"separates no two modelled compartments, so it carries "
                            f"no heat and was not added to the network.",
                        )
                    )
                    continue

                consumed.add(adjacency.key)
                self._partitioned_pairs.add(adjacency.key)
                self._partition_adjacency[partition_id] = adjacency

                open_fraction = (
                    _float_or(partition, "open_area_fraction", 0.0)
                    if _bool_or(partition, "is_perforated", False)
                    else 0.0
                )
                solid_area = adjacency.overlap_area_m2 * (1.0 - open_fraction)
                other = (
                    adjacency.compartment_b
                    if adjacency.compartment_a == owner
                    else adjacency.compartment_a
                )
                if solid_area > 0.0:
                    surfaces.append(
                        SurfaceSnapshot(
                            surface_id=f"partition:{partition_id}",
                            compartment_id=owner,
                            area_m2=solid_area,
                            orientation=(
                                SurfaceOrientation.HORIZONTAL_UP
                                if orientation == "HORIZONTAL"
                                else SurfaceOrientation.VERTICAL
                            ),
                            emissivity=self.emissivity,
                            thickness_m=_req_float(partition, "thickness_m", "partition"),
                            thermal_conductivity_w_per_m_k=_req_float(
                                partition, "thermal_conductivity_W_mK", "partition"
                            ),
                            is_external=False,
                            adjacent_compartment_id=other,
                            internal_emissivity=self.emissivity,
                        )
                    )

                # A perforated partition with no declared opening still passes
                # air; that free area is a ventilation path, not a wall.
                vent_area = adjacency.overlap_area_m2 * open_fraction
                if vent_area > 0.0 and not self._opening_declared_for(partition_id):
                    self._openings.append(
                        OpeningSnapshot(
                            opening_id=f"partition-vent:{partition_id}",
                            from_compartment_id=owner,
                            to_compartment_id=other,
                            free_area_m2=vent_area,
                            discharge_coefficient=_DEFAULT_DISCHARGE_COEFFICIENT,
                            centroid_height_m=adjacency.centroid_height_m,
                            is_forced=False,
                            fan_id=None,
                        )
                    )
        return surfaces

    def _opening_declared_for(self, partition_id: str) -> bool:
        for compartment in _objects(self._enclosure, "compartments"):
            for opening in _objects(compartment, "internal_openings"):
                if _opt_str(opening, "partition_id") == partition_id:
                    return True
        return False

    def _warn_about_unseparated_compartments(self) -> None:
        for adjacency in self._adjacencies:
            if adjacency.key in self._partitioned_pairs:
                continue
            if any(
                {o.from_compartment_id, o.to_compartment_id} == set(adjacency.key)
                for o in self._openings
            ):
                continue
            self._warnings.append(
                (
                    "WARN-NO-PARTITION",
                    f"Compartments {adjacency.compartment_a!r} and "
                    f"{adjacency.compartment_b!r} share a boundary of "
                    f"{adjacency.overlap_area_m2:.3f} m² but the model declares no "
                    f"partition and no opening between them. They were solved as "
                    f"thermally separate, which is the conservative reading; declare "
                    f"the partition if heat really does cross it.",
                )
            )

    # -- openings ----------------------------------------------------------

    def _internal_openings(self) -> list[OpeningSnapshot]:
        out: list[OpeningSnapshot] = []
        for compartment in _objects(self._enclosure, "compartments"):
            owner = _req_str(compartment, "id", "compartment")
            for opening in _objects(compartment, "internal_openings"):
                opening_id = _req_str(opening, "id", "internal_opening")
                partition_id = _opt_str(opening, "partition_id")
                adjacency = (
                    self._partition_adjacency.get(partition_id)
                    if partition_id is not None
                    else None
                )
                if adjacency is None:
                    neighbours = self._adjacencies_for(owner)
                    adjacency = neighbours[0] if neighbours else None
                if adjacency is None:
                    self._warnings.append(
                        (
                            "WARN-OPENING-UNMATCHED",
                            f"Internal opening {opening_id!r} in compartment "
                            f"{owner!r} connects to no other modelled compartment "
                            f"and was ignored.",
                        )
                    )
                    continue

                other = (
                    adjacency.compartment_b
                    if adjacency.compartment_a == owner
                    else adjacency.compartment_a
                )
                free_area = _req_float(
                    opening, "gross_area_m2", "internal_opening"
                ) * _req_float(opening, "open_area_fraction", "internal_opening")
                if free_area <= 0.0:
                    continue
                out.append(
                    OpeningSnapshot(
                        opening_id=opening_id,
                        from_compartment_id=owner,
                        to_compartment_id=other,
                        free_area_m2=free_area,
                        discharge_coefficient=_req_float(
                            opening, "discharge_coefficient", "internal_opening"
                        ),
                        centroid_height_m=adjacency.centroid_height_m,
                        is_forced=False,
                        fan_id=None,
                    )
                )
        return out

    def _external_openings(self) -> list[OpeningSnapshot]:
        out: list[OpeningSnapshot] = []
        for opening in _objects(self._enclosure, "external_openings"):
            opening_id = _req_str(opening, "id", "external_opening")
            free_area = _req_float(
                opening, "gross_area_m2", "external_opening"
            ) * _req_float(opening, "open_area_fraction", "external_opening")
            if free_area <= 0.0:
                continue
            x = _req_float(opening, "position_x_m", "external_opening")
            y = _req_float(opening, "position_y_m", "external_opening")
            z = _req_float(opening, "position_z_m", "external_opening")
            compartment_id = self._compartment_behind(
                _req_str(opening, "mounting_surface", "external_opening"), x, y, z
            )
            # opening_type classifies the hardware (louvre, gland plate),
            # not the flow: the buoyancy solver works out which way the air
            # actually goes from the stack pressure.
            out.append(
                OpeningSnapshot(
                    opening_id=opening_id,
                    from_compartment_id=None,
                    to_compartment_id=compartment_id,
                    free_area_m2=free_area,
                    discharge_coefficient=_float_or(
                        opening, "discharge_coefficient", _DEFAULT_DISCHARGE_COEFFICIENT
                    ),
                    centroid_height_m=max(z, 0.0),
                    is_forced=False,
                    fan_id=None,
                )
            )
        return out

    def _compartment_behind(self, face: str, x: float, y: float, z: float) -> str:
        """The compartment an opening in `face` at (x, y, z) ventilates."""
        touching = [
            cid
            for cid in self._compartment_order
            if self._face_contact_area_m2(face, self.boxes[cid]) > 0.0
        ]
        pool = touching or self._compartment_order
        return min(pool, key=lambda cid: self.boxes[cid].distance_to(x, y, z))

    # -- fans ---------------------------------------------------------------

    def _fans(self, mode: str) -> tuple[dict[str, float], list[HeatSource]]:
        """
        Turn the declared fans into openings, forced flows and motor losses.

        MODE_3 is the only mode that drives air: MODE_2 models natural
        convection, so a running fan there is reported as an open aperture and
        a warning rather than silently ignored or silently applied.
        """
        forced: dict[str, float] = {}
        sources: list[HeatSource] = []
        fans = _objects(self._enclosure, "fans")
        if not fans:
            return forced, sources

        rho = air_at(
            KELVIN_OFFSET + 20.0, _altitude_pressure_pa(0.0)
        ).density_kg_per_m3

        for fan in fans:
            fan_id = _req_str(fan, "id", "fan")
            state = _opt_str(fan, "operating_state") or "RUNNING_FORWARD"
            x = _req_float(fan, "position_x_m", "fan")
            y = _req_float(fan, "position_y_m", "fan")
            z = _req_float(fan, "position_z_m", "fan")
            compartment_id = self._compartment_behind(
                _req_str(fan, "mounting_surface", "fan"), x, y, z
            )

            motor_loss = _opt_float(fan, "motor_power_loss_W")
            if motor_loss is not None and motor_loss > 0.0:
                # IEC TR 60890 §11.1 counts the fan motor's own loss in P_tot,
                # and so does the nodal network: the motor sits in the airstream.
                sources.append(
                    HeatSource(
                        source_id=f"fan-motor:{fan_id}",
                        entity_type=HeatSourceEntityType.OTHER,
                        entity_id=fan_id,
                        power_loss_w=motor_loss,
                        location=Point3D(x=x, y=y, z=z),
                        volume_m3=None,
                        surface_area_m2=None,
                        confidence=LossConfidence.MANUFACTURER_TYPICAL,
                        calculation_source=LossCalculationSource.MANUFACTURER_RATED,
                        library_ref=_opt_str(fan, "ventilation_device_library_id"),
                        operating_current_a=None,
                        current_fraction=None,
                        generation_type=HeatSourceGenerationType.POINT,
                        name=f"Fan {fan_id} motor",
                        compartment_id=compartment_id,
                    )
                )
                self.fan_entity_types[fan_id] = "FAN"

            if state in _BLOCKING_FAN_STATES:
                # A closed damper or a blocked rotor is a wall, not an opening.
                continue

            free_area = _opt_float(fan, "free_area_m2") or _DEFAULT_FAN_FREE_AREA_M2
            opening_id = f"fan:{fan_id}"
            is_inlet = (_opt_str(fan, "orientation") or "INLET") == "INLET"
            # Reverse flow is a direction, not a negative number: the opening
            # is turned around and the flow stays positive (DR-005).
            if state == "REVERSE_FLOW_ESTIMATED":
                is_inlet = not is_inlet

            driving = state in _DRIVING_FAN_STATES and mode == "MODE_3"
            if state in _DRIVING_FAN_STATES and mode != "MODE_3":
                self._warnings.append(
                    (
                        "WARN-FAN-NOT-DRIVEN",
                        f"Fan {fan_id!r} is {state} but the run is {mode}, which "
                        f"models natural ventilation only. The fan aperture was "
                        f"modelled as an open vent and the fan was not driven; use "
                        f"MODE_3 to account for forced ventilation.",
                    )
                )

            flow = self._fan_flow_m3_per_s(fan, free_area, rho) if driving else None
            if driving and flow is None:
                raise ContractError(
                    f"Fan {fan_id!r} is {state} in a MODE_3 run but supplies neither "
                    f"a fan_curve nor a prescribed_flow_m3_s, so its flow is unknown. "
                    f"Resolve the ventilation device library entry at the API "
                    f"boundary and inline one of them (CR-TECH-001)."
                )

            if flow is not None:
                forced[opening_id] = flow
                self._has_driving_fan = True

            self._openings.append(
                OpeningSnapshot(
                    opening_id=opening_id,
                    from_compartment_id=None if is_inlet else compartment_id,
                    to_compartment_id=compartment_id if is_inlet else None,
                    free_area_m2=free_area,
                    discharge_coefficient=_fan_discharge_coefficient(fan),
                    centroid_height_m=max(z, 0.0),
                    is_forced=flow is not None,
                    fan_id=fan_id,
                )
            )
        return forced, sources

    def _fan_flow_m3_per_s(
        self, fan: Mapping[str, Any], free_area_m2: float, rho_kg_per_m3: float
    ) -> float | None:
        """
        The fan's operating flow [m³/s].

        A manufacturer curve is believed over a prescribed figure, because the
        curve and the enclosure's own resistance together decide what the fan
        actually delivers; a prescribed flow is what someone hoped for.
        """
        curve_json = fan.get("fan_curve")
        if isinstance(curve_json, list) and len(curve_json) >= 2:
            curve = [
                FanCurvePoint(
                    flow_m3_per_s=_req_float(point, "flow_m3_s", "fan_curve"),
                    static_pressure_pa=_req_float(
                        point, "static_pressure_Pa", "fan_curve"
                    ),
                    power_w=_float_or(point, "power_W", 0.0),
                    efficiency=_float_or(point, "efficiency", 0.0),
                )
                for point in _objects(fan, "fan_curve")
            ]
            resistance = self._system_resistance_pa_per_m3_per_s_sq(
                free_area_m2, rho_kg_per_m3
            )
            operating_point = fan_operating_point(curve, resistance)
            if operating_point is not None:
                return operating_point.flow_m3_per_s
            self._warnings.append(
                (
                    "WARN-FAN-NO-OPERATING-POINT",
                    f"The fan curve for {_req_str(fan, 'id', 'fan')!r} does not "
                    f"cross the system resistance of "
                    f"{resistance:.1f} Pa/(m³/s)²; the enclosure is too restrictive "
                    f"for this fan. The prescribed flow was used instead where one "
                    f"was given.",
                )
            )
        return _opt_float(fan, "prescribed_flow_m3_s")

    def _system_resistance_pa_per_m3_per_s_sq(
        self, fan_free_area_m2: float, rho_kg_per_m3: float
    ) -> float:
        """
        K_sys in ΔP_sys = K_sys · Q² [Pa/(m³/s)²].

        The openings the air passes through act in series, so their effective
        areas combine as 1/A_eff² = Σ 1/(C_d·A)², and ΔP = ρ·Q²/(2·A_eff²).
        """
        effective = [
            o.discharge_coefficient * o.free_area_m2
            for o in self._openings
            if not o.is_forced and o.free_area_m2 > 0.0
        ]
        effective.append(fan_free_area_m2)
        inverse_square = sum(1.0 / (a * a) for a in effective if a > 0.0)
        if inverse_square <= 0.0:
            return 0.0
        return rho_kg_per_m3 * inverse_square / 2.0


def _fan_discharge_coefficient(fan: Mapping[str, Any]) -> float:
    """
    C_d for a fan aperture, from its duct loss coefficient where one is given.

    With ΔP = K·½ρv² and Q = C_d·A·√(2ΔP/ρ), the two descriptions agree when
    C_d = 1/√K. A stopped fan with K = 4 therefore passes half the air an
    equivalent plain hole would.
    """
    k = _opt_float(fan, "fan_loss_coefficient_K")
    if k is None or k <= 0.0:
        return _DEFAULT_DISCHARGE_COEFFICIENT
    return min(1.0, 1.0 / math.sqrt(k))


def _take_adjacency(
    by_axis: dict[str, list[_Adjacency]],
    axes: Sequence[str],
    consumed: set[tuple[str, str]],
) -> _Adjacency | None:
    """The next unclaimed adjacency along any of `axes`."""
    for axis in axes:
        for adjacency in by_axis.get(axis, []):
            if adjacency.key not in consumed:
                return adjacency
    return None


# ---------------------------------------------------------------------------
# Heat sources
# ---------------------------------------------------------------------------


def _confidence(entry: Mapping[str, Any]) -> LossConfidence:
    key = _opt_str(entry, "data_confidence") or "UNKNOWN"
    return _CONFIDENCE_BY_DATA_CONFIDENCE.get(key, LossConfidence.ASSUMED_DEFAULT)


def _device_power_w(device: Mapping[str, Any], device_id: str) -> tuple[float, str]:
    """
    A device's dissipation at its load current [W], and how it was obtained.

    The three M0-03 thermal models are evaluated as written. A QUADRATIC model
    with no coefficients falls back to scaling the rated loss by (I/I_r)²,
    which is the same physics stated with less data.
    """
    model = _req_str(device, "thermal_model", "device")
    current = _req_float(device, "load_current_A", "device")
    rated = _req_float(device, "rated_current_A", "device")
    a = _opt_float(device, "power_coefficient_a")
    b = _opt_float(device, "power_coefficient_b")
    c = _opt_float(device, "power_coefficient_c")
    rated_loss = _opt_float(device, "power_at_rated_W")

    if model == "FIXED_POWER":
        if rated_loss is not None:
            return rated_loss, "MANUFACTURER_RATED"
        if c is not None:
            return c, "MANUFACTURER_RATED"
    elif model == "LINEAR":
        if b is not None or c is not None:
            return max((b or 0.0) * current + (c or 0.0), 0.0), "MANUFACTURER_CURVE"
    elif model == "QUADRATIC":
        if a is not None or b is not None or c is not None:
            value = (a or 0.0) * current * current + (b or 0.0) * current + (c or 0.0)
            return max(value, 0.0), "MANUFACTURER_CURVE"
        if rated_loss is not None and rated > 0.0:
            return rated_loss * (current / rated) ** 2, "MANUFACTURER_CURVE"

    raise ContractError(
        f"Device {device_id!r} declares thermal_model {model!r} but carries neither "
        f"the coefficients it needs nor a power_at_rated_W to fall back on. Resolve "
        f"the device library entry at the API boundary and inline the loss "
        f"(CR-TECH-001)."
    )


def _device_sources(
    enclosure: Mapping[str, Any],
    builder: _GeometryBuilder,
    entity_types: dict[str, str],
    entity_limits_k: dict[str, float],
    loading_factors: dict[str, float],
    warnings: list[tuple[str, str]],
) -> list[HeatSource]:
    out: list[HeatSource] = []
    for device in _objects(enclosure, "devices"):
        device_id = _req_str(device, "id", "device")
        x = _req_float(device, "position_x_m", "device")
        y = _req_float(device, "position_y_m", "device")
        z = _req_float(device, "position_z_m", "device")
        power_w, calc_source = _device_power_w(device, device_id)
        current = _req_float(device, "load_current_A", "device")
        rated = _req_float(device, "rated_current_A", "device")

        area = _opt_float(device, "surface_area_m2")
        if area is None:
            warnings.append(
                (
                    "WARN-NO-DEVICE-AREA",
                    f"Device {device_id!r} declares no surface_area_m2, so it has no "
                    f"body node: its loss heats the compartment air and it is "
                    f"reported at the air temperature. Supply the area to get a "
                    f"device temperature of its own.",
                )
            )

        limit_c = _opt_float(device, "max_operating_temp_C")
        if limit_c is not None:
            entity_limits_k[device_id] = limit_c + KELVIN_OFFSET

        loading_factors[device_id] = current / rated if rated > 0.0 else 0.0
        entity_types[device_id] = "DEVICE"

        out.append(
            HeatSource(
                source_id=f"device:{device_id}",
                entity_type=HeatSourceEntityType.DEVICE,
                entity_id=device_id,
                power_loss_w=power_w,
                location=Point3D(x=x, y=y, z=z),
                volume_m3=_opt_float(device, "volume_m3"),
                surface_area_m2=area,
                confidence=_confidence(device),
                calculation_source=LossCalculationSource(calc_source),
                library_ref=_opt_str(device, "device_library_id"),
                operating_current_a=current,
                current_fraction=current / rated if rated > 0.0 else None,
                breakdown=LossBreakdown(joule_loss_w=power_w),
                generation_type=(
                    HeatSourceGenerationType.SURFACE
                    if area is not None
                    else HeatSourceGenerationType.POINT
                ),
                name=_opt_str(device, "name"),
                compartment_id=builder.compartment_for_point(
                    x, y, z, _opt_str(device, "compartment_id")
                ),
                emissivity=_opt_float(device, "emissivity"),
                temperature_limit_k=(
                    limit_c + KELVIN_OFFSET if limit_c is not None else None
                ),
            )
        )
    return out


def _busbar_sources(
    enclosure: Mapping[str, Any],
    builder: _GeometryBuilder,
    entity_types: dict[str, str],
    loading_factors: dict[str, float],
    warnings: list[tuple[str, str]],
) -> list[HeatSource]:
    """
    One heat source per busbar segment, and one more per joint.

    CR-ENG-008: a joint's contact loss is never folded into the bar's bulk
    resistivity. A bolted connection is a separate entity with its own
    resistance, its own temperature and its own limit, because that is where
    busbar systems actually fail.
    """
    out: list[HeatSource] = []
    for run in _objects(enclosure, "busbar_runs"):
        run_id = _req_str(run, "id", "busbar_run")
        current = _req_float(run, "current_A", "busbar_run")
        area_m2 = _req_float(run, "cross_section_m2", "busbar_run")
        resistivity = _req_float(run, "resistivity_ohm_m", "busbar_run")
        alpha = _req_float(run, "temp_coefficient_1_K", "busbar_run")
        t_ref_k = _float_or(run, "temp_ref_C", 20.0) + KELVIN_OFFSET
        width = _req_float(run, "width_m", "busbar_run")
        thickness = _req_float(run, "thickness_m", "busbar_run")
        emissivity = _req_float(run, "emissivity", "busbar_run")
        declared_compartment = _opt_str(run, "compartment_id")
        run_name = _opt_str(run, "name")
        phase = _req_str(run, "phase_label", "busbar_run")

        segment_centres: dict[str, tuple[float, float, float]] = {}

        for segment in _objects(run, "segments"):
            segment_id = _req_str(segment, "id", "busbar_segment")
            length = _req_float(segment, "length_m", "busbar_segment")
            centre = (
                0.5
                * (
                    _req_float(segment, "start_x_m", "busbar_segment")
                    + _req_float(segment, "end_x_m", "busbar_segment")
                ),
                0.5
                * (
                    _req_float(segment, "start_y_m", "busbar_segment")
                    + _req_float(segment, "end_y_m", "busbar_segment")
                ),
                0.5
                * (
                    _req_float(segment, "start_z_m", "busbar_segment")
                    + _req_float(segment, "end_z_m", "busbar_segment")
                ),
            )
            segment_centres[segment_id] = centre

            k_ac = _opt_float(segment, "k_ac_factor")
            k_ac_source = _opt_str(segment, "k_ac_source")
            applied_k_ac = k_ac if k_ac is not None and k_ac >= 1.0 else 1.0
            # CR-ENG-011 / DR-003: the solver raises the K_AC warning off this
            # very distinction, so DC_RESISTANCE_CALC must mean exactly
            # "no qualified AC correction was available".
            corrected = (
                k_ac is not None
                and k_ac_source is not None
                and k_ac_source != "NOT_APPLIED"
            )
            resistance_ohm = resistivity * length / area_m2 * applied_k_ac
            power_w = current * current * resistance_ohm

            entity_types[segment_id] = "BUSBAR_SEGMENT"
            out.append(
                HeatSource(
                    source_id=f"busbar:{segment_id}",
                    entity_type=HeatSourceEntityType.BUSBAR,
                    entity_id=segment_id,
                    power_loss_w=power_w,
                    location=Point3D(x=centre[0], y=centre[1], z=centre[2]),
                    volume_m3=area_m2 * length,
                    surface_area_m2=(
                        _opt_float(segment, "surface_area_m2")
                        or 2.0 * (width + thickness) * length
                    ),
                    confidence=LossConfidence.CORRELATED,
                    calculation_source=(
                        LossCalculationSource.AC_RESISTANCE_CALC
                        if corrected
                        else LossCalculationSource.DC_RESISTANCE_CALC
                    ),
                    library_ref=None,
                    operating_current_a=current,
                    current_fraction=None,
                    breakdown=LossBreakdown(joule_loss_w=power_w),
                    generation_type=HeatSourceGenerationType.VOLUMETRIC,
                    name=f"{run_name or run_id} {phase} segment",
                    compartment_id=builder.compartment_for_point(
                        centre[0], centre[1], centre[2], declared_compartment
                    ),
                    temperature_coefficient_per_k=alpha,
                    reference_temperature_k=t_ref_k,
                    emissivity=emissivity,
                    characteristic_length_m=max(width, thickness),
                )
            )

        out.extend(
            _joint_sources(
                run,
                run_id,
                current,
                segment_centres,
                builder,
                declared_compartment,
                entity_types,
                warnings,
            )
        )
    return out


def _joint_sources(
    run: Mapping[str, Any],
    run_id: str,
    current_a: float,
    segment_centres: Mapping[str, tuple[float, float, float]],
    builder: _GeometryBuilder,
    declared_compartment: str | None,
    entity_types: dict[str, str],
    warnings: list[tuple[str, str]],
) -> list[HeatSource]:
    out: list[HeatSource] = []
    for joint in _objects(run, "joints"):
        joint_id = _req_str(joint, "id", "busbar_joint")
        condition = _req_str(joint, "joint_condition", "busbar_joint")
        resistance = _opt_float(joint, "contact_resistance_ref_ohm")

        if condition == "UNKNOWN":
            # CR-ENG-010 / DR-004: there is no universal default contact
            # resistance. An unknown joint is solved at its own declared
            # nominal and the engineer is told the answer rests on it.
            resistance = _opt_float(joint, "sensitivity_nominal_ohm")
            if resistance is None:
                raise ContractError(
                    f"Busbar joint {joint_id!r} has joint_condition UNKNOWN but no "
                    f"sensitivity_nominal_ohm. CR-ENG-010 forbids a default contact "
                    f"resistance, so the joint cannot be solved: measure it, or "
                    f"supply the sensitivity range from DR-004."
                )
            warnings.append(
                (
                    "WARN-010-JOINT-UNKNOWN",
                    f"Busbar joint {joint_id!r} has an unknown condition and was "
                    f"solved at its nominal contact resistance of {resistance:.3e} Ω. "
                    f"CR-ENG-010: run the sensitivity scenarios across "
                    f"sensitivity_min_ohm and sensitivity_max_ohm before relying on "
                    f"this joint's temperature.",
                )
            )
        elif resistance is None:
            raise ContractError(
                f"Busbar joint {joint_id!r} has condition {condition!r} but no "
                f"contact_resistance_ref_ohm. DR-004 requires a measured, "
                f"manufacturer or library value; there is no default (CR-ENG-010)."
            )

        x = _req_float(joint, "position_x_m", "busbar_joint")
        y = _req_float(joint, "position_y_m", "busbar_joint")
        z = _req_float(joint, "position_z_m", "busbar_joint")
        if (x, y, z) == (0.0, 0.0, 0.0):
            fallback = segment_centres.get(_req_str(joint, "segment_a_id", "joint"))
            if fallback is not None:
                x, y, z = fallback

        power_w = current_a * current_a * resistance
        entity_types[joint_id] = "BUSBAR_JOINT"
        out.append(
            HeatSource(
                source_id=f"joint:{joint_id}",
                entity_type=HeatSourceEntityType.JOINT,
                entity_id=joint_id,
                power_loss_w=power_w,
                location=Point3D(x=x, y=y, z=z),
                volume_m3=None,
                surface_area_m2=_opt_float(joint, "surface_area_m2"),
                confidence=_confidence(joint),
                calculation_source=LossCalculationSource.JOINT_RESISTANCE,
                library_ref=None,
                operating_current_a=current_a,
                current_fraction=None,
                breakdown=LossBreakdown(contact_loss_w=power_w),
                name=f"{run_id} joint {joint_id}",
                compartment_id=builder.compartment_for_point(
                    x, y, z, declared_compartment
                ),
                temperature_coefficient_per_k=_req_float(
                    joint, "temp_coefficient_contact_1_K", "busbar_joint"
                ),
                reference_temperature_k=(
                    _float_or(joint, "temp_ref_C", 20.0) + KELVIN_OFFSET
                ),
            )
        )
    return out


def _conductor_sources(
    enclosure: Mapping[str, Any],
    builder: _GeometryBuilder,
    entity_types: dict[str, str],
    loading_factors: dict[str, float],
    warnings: list[tuple[str, str]],
) -> list[HeatSource]:
    out: list[HeatSource] = []
    for conductor in _objects(enclosure, "conductors"):
        conductor_id = _req_str(conductor, "id", "conductor")
        resistance_per_m = _opt_float(conductor, "resistance_ohm_per_m")
        if resistance_per_m is None:
            raise ContractError(
                f"Conductor {conductor_id!r} has no resistance_ohm_per_m. "
                f"thermpro_engine never queries the conductor library "
                f"(CR-TECH-001), so the resolved resistance must be inlined on the "
                f"InputSnapshot before the engine is called."
            )
        length = _req_float(conductor, "length_m", "conductor")
        current = _req_float(conductor, "current_A", "conductor")
        power_w = current * current * resistance_per_m * length

        rated = _opt_float(conductor, "rated_current_A")
        if rated is not None and rated > 0.0:
            # Bundling derates what the cable may carry, not what it
            # dissipates, so it belongs in the loading factor and nowhere else.
            bundling = _float_or(conductor, "bundling_factor", 1.0)
            loading_factors[conductor_id] = current / (rated * max(bundling, 1e-6))

        area = _opt_float(conductor, "surface_area_m2")
        if area is None:
            warnings.append(
                (
                    "WARN-NO-CONDUCTOR-AREA",
                    f"Conductor {conductor_id!r} declares no surface_area_m2, so its "
                    f"loss heats the compartment air and it is reported at the air "
                    f"temperature rather than at a conductor temperature of its own.",
                )
            )

        # A conductor run has no coordinates in M0-03; it is placed by its
        # declared compartment, or in the first one when none is given.
        compartment_id = _opt_str(conductor, "compartment_id")
        centre = builder.compartment_centres.get(compartment_id or "", None)
        if centre is None:
            compartment_id = builder.compartment_for_point(0.0, 0.0, 0.0, None)
            centre = builder.compartment_centres[compartment_id]

        entity_types[conductor_id] = "CONDUCTOR"
        out.append(
            HeatSource(
                source_id=f"conductor:{conductor_id}",
                entity_type=HeatSourceEntityType.CABLE,
                entity_id=conductor_id,
                power_loss_w=power_w,
                location=Point3D(x=centre[0], y=centre[1], z=centre[2]),
                volume_m3=None,
                surface_area_m2=area,
                confidence=LossConfidence.CORRELATED,
                calculation_source=LossCalculationSource.DC_RESISTANCE_CALC,
                library_ref=_opt_str(conductor, "conductor_library_id"),
                operating_current_a=current,
                current_fraction=(
                    current / rated if rated is not None and rated > 0.0 else None
                ),
                breakdown=LossBreakdown(joule_loss_w=power_w),
                name=_opt_str(conductor, "name"),
                compartment_id=compartment_id,
                temperature_coefficient_per_k=_opt_float(
                    conductor, "temp_coefficient_1_K"
                ),
                reference_temperature_k=(
                    _float_or(conductor, "temp_ref_C", 20.0) + KELVIN_OFFSET
                ),
                emissivity=_opt_float(conductor, "emissivity"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Mode applicability
# ---------------------------------------------------------------------------


def _mode_blocking_reasons(
    mode: str,
    builder: _GeometryBuilder,
    enclosure: Mapping[str, Any],
    sources: Sequence[HeatSource],
) -> tuple[str, ...]:
    """
    Reasons the requested mode must not be used at all.

    CR-ENG-006 lives here: a fan that is actually running disqualifies the
    IEC TR 60890 empirical method, and no user setting overrides that, because
    the correlation was fitted to naturally ventilated enclosures and reports
    a rise that a forced-ventilation enclosure will not have.
    """
    reasons: list[str] = []
    fan_states = [
        _opt_str(fan, "operating_state") or "RUNNING_FORWARD"
        for fan in _objects(enclosure, "fans")
    ]
    has_forced = any(state in _DRIVING_FAN_STATES for state in fan_states)

    if mode == "MODE_1":
        applicability = check_iec60890_applicability(
            has_forced_ventilation=has_forced,
            has_busbars_with_unknown_losses=any(
                source.entity_type
                in (HeatSourceEntityType.BUSBAR, HeatSourceEntityType.JOINT)
                and source.confidence == LossConfidence.ASSUMED_DEFAULT
                for source in sources
            ),
            enclosure_height_m=builder.height_m,
        )
        reasons.extend(applicability.reasons)

    if mode == "MODE_3" and not builder.has_driving_fan:
        reasons.append(
            "MODE_3 models forced ventilation, but no fan in this model is "
            "running. Use MODE_2 for a naturally ventilated enclosure."
        )

    return tuple(reasons)


# ---------------------------------------------------------------------------
# M0-04 result mapping
# ---------------------------------------------------------------------------


def result_to_json(
    result: ResultSnapshot,
    mapped: ContractInput,
    *,
    compliance: ComplianceReport | None = None,
) -> dict[str, Any]:
    """
    Map a solved `ResultSnapshot` onto an M0-04 ResultSnapshot document.

    Parameters
    ----------
    result:
        The solver output, converged or not.
    mapped:
        The `ContractInput` the solve came from, which carries the entity
        lookup tables and the mapping-time warnings.
    compliance:
        The compliance interpretation. When omitted it is computed here
        against the input's standard profile.
    """
    ambient_k = mapped.snapshot.boundary_conditions.ambient_temperature_k
    report = compliance or evaluate_compliance(
        result,
        ambient_k=ambient_k,
        limit_set=limit_set_for_profiles(mapped.standard_profile),
        entity_limits_k=mapped.entity_limits_k,
        entity_loading_factors=mapped.entity_loading_factors,
    )

    document: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "run_id": result.calculation_id,
        "mode": mapped.mode,
        "status": result.status.value,
        "engine_version": ENGINE_VERSION,
        "standard_profile": list(mapped.standard_profile),
        "failure_reason": _failure_reason(result),
        "solver_summary": _solver_summary(result),
        "temperatures": {
            "ambient_K": ambient_k,
            "entities": _entity_temperatures(result, mapped, ambient_k),
            "thermal_cells": _thermal_cells(result, mapped),
        },
        "hotspots": [
            {
                "entity_id": h.entity_id,
                "entity_type": mapped.entity_types.get(h.entity_id, h.entity_type),
                "name": h.name,
                "temperature_K": h.temperature_k,
                "temperature_rise_K": h.temperature_rise_k,
                "limit_K": h.limit_k,
                "excess_K": h.excess_k,
                "severity": h.severity.value,
            }
            for h in report.hotspots
        ],
        "derating": [
            {
                "entity_id": d.entity_id,
                "entity_type": mapped.entity_types.get(d.entity_id, d.entity_type),
                "name": d.name,
                "current_loading_factor": d.current_loading_factor,
                "recommended_loading_factor": d.recommended_loading_factor,
                "margin_K": d.margin_k,
                "action_required": d.action_required,
            }
            for d in report.derating
        ],
        "compliance": {
            "overall_compliant": report.overall_compliant,
            "checks": [
                {
                    "check_id": c.check_id,
                    "entity_id": c.entity_id,
                    "entity_type": mapped.entity_types.get(c.entity_id, c.entity_type),
                    "name": c.name,
                    "standard": c.standard,
                    "clause": c.clause,
                    "limit_K": c.limit_k,
                    "actual_rise_K": c.actual_rise_k,
                    "margin_K": c.margin_k,
                    "status": c.status.value,
                    "note": c.note,
                }
                for c in report.checks
            ],
        },
        "airflow": _airflow(result),
        "library_manifest_echo": dict(mapped.snapshot.library_manifest),
        "sensitivity_summary": None,
        "k_ac_warnings": [
            {
                "segment_id": w.entity_id,
                "warning_code": "K_AC_UNITY_FALLBACK",
                "message": w.message,
            }
            for w in result.warnings
            if w.code == "K_AC_UNITY_FALLBACK" and w.entity_id is not None
        ],
        "mode_1_result": _mode_1_result(result),
    }
    return document


def limit_set_for_profiles(profiles: Sequence[str]) -> LimitSet:
    """
    The limit set a standard profile selects (CR-ENG-009).

    Each profile defines its own limits and report wording, so the choice is
    made explicitly rather than by applying one table to everything. IEC
    61439-2 is the assembly-specific standard and wins when both are named.
    """
    if "IEC_61439_2" in profiles:
        return iec_61439_limit_set(StandardProfile.IEC_61439_2)
    if "IEC_61439_1" in profiles:
        return iec_61439_limit_set(StandardProfile.IEC_61439_1)
    if "IEC_TR_60890" in profiles:
        return iec_61439_limit_set(StandardProfile.IEC_TR_60890)
    return iec_61439_limit_set()


def _failure_reason(result: ResultSnapshot) -> str | None:
    if result.status == SolverStatus.CONVERGED:
        return None
    relevant = [
        w.message
        for w in result.warnings
        if w.code in ("VAL-FAIL", "WARN-005-NON-CONVERGED", "WARN-012-DIVERGING")
    ]
    if relevant:
        return " ".join(relevant)
    return f"The calculation finished with status {result.status.value}."


def _solver_summary(result: ResultSnapshot) -> dict[str, Any]:
    trace = result.convergence_trace
    generation = result.total_heat_generation_w
    imbalance = (
        abs(generation - result.total_heat_dissipation_w) / generation
        if generation > 0.0
        else 0.0
    )
    return {
        # The engine runs one Picard loop rather than nested loops, so the
        # outer and inner counts are the same iteration count reported twice;
        # M0-04 asks for both and inventing a difference would be worse.
        "outer_iterations_used": len(trace),
        "inner_iterations_total": len(trace),
        "wall_clock_s": result.elapsed_seconds,
        "final_max_delta_T_K": trace[-1].max_delta_k if trace else 0.0,
        "final_energy_imbalance_fraction": imbalance,
        # The airflow network is solved directly from the stack pressure, not
        # iterated to a mass residual, so there is no mass imbalance to report.
        "final_mass_imbalance_fraction": None,
        "convergence_trace": [
            {
                # M0-04 numbers iterations from 1; the solver counts from 0.
                "iteration": index + 1,
                "max_delta_T_K": row.max_delta_k,
                "inner_iterations": 1,
                "energy_imbalance_W": row.energy_balance_error_w,
                "mass_imbalance_fraction": None,
            }
            for index, row in enumerate(trace)
        ],
    }


def _entity_temperatures(
    result: ResultSnapshot, mapped: ContractInput, ambient_k: float
) -> list[dict[str, Any]]:
    """
    One M0-04 entity row per user-visible object.

    Only the *outer* face of an external wall is reported as a SURFACE: the
    inner face is an internal node of the wall model, and reporting both under
    the same entity_id would put two different temperatures on one object.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in result.node_temperatures:
        if node.entity_id is None:
            continue
        if node.node_type == NodeType.INTERNAL_SURFACE:
            continue
        if node.node_type == NodeType.SURFACE and node.node_id != surface_outer_node(
            node.entity_id
        ):
            continue
        entity_type = mapped.entity_types.get(
            node.entity_id, _M004_ENTITY_TYPE_BY_NODE_TYPE.get(node.node_type, "DEVICE")
        )
        if node.entity_id in seen:
            continue
        seen.add(node.entity_id)
        rows.append(
            {
                "entity_id": node.entity_id,
                "entity_type": entity_type,
                "name": node.name,
                "temperature_K": node.temperature_k,
                "temperature_C": node.temperature_k - KELVIN_OFFSET,
                "temperature_rise_K": node.temperature_k - ambient_k,
                "power_loss_W": node.heat_generation_w,
            }
        )
    return rows


def _thermal_cells(result: ResultSnapshot, mapped: ContractInput) -> list[dict[str, Any]]:
    """
    Compartment air temperatures, as M0-04 thermal cells.

    M0-04's entity_type enum has no AIR member, which is correct — air is not
    an entity — so the zonal model's one air node per compartment is reported
    as one cell at the compartment's centroid.
    """
    cells: list[dict[str, Any]] = []
    for node in result.node_temperatures:
        if node.node_type != NodeType.AIR or node.compartment_id is None:
            continue
        centre = mapped.compartment_centres_m.get(node.compartment_id, (0.0, 0.0, 0.0))
        cells.append(
            {
                "cell_id": node.node_id,
                "compartment_id": node.compartment_id,
                "centre_x_m": centre[0],
                "centre_y_m": centre[1],
                "centre_z_m": centre[2],
                "temperature_K": node.temperature_k,
            }
        )
    return cells


def _airflow(result: ResultSnapshot) -> dict[str, Any] | None:
    if result.airflow is None:
        return None
    flows = result.airflow.opening_flows
    return {
        "total_flow_rate_m3s": result.airflow.total_flow_rate_m3_per_s,
        "fan_operating_points": [],
        "opening_flows": [
            {
                "opening_id": f.opening_id,
                "flow_rate_m3s": abs(f.volumetric_flow_m3_per_s),
                "direction": f.direction,
            }
            for f in flows
        ],
        "buoyancy_stack_pressure_Pa": result.airflow.buoyancy_stack_pressure_pa,
    }


def _mode_1_result(result: ResultSnapshot) -> dict[str, Any] | None:
    mode_1 = result.mode_1
    if mode_1 is None:
        return None
    return {
        "P_total_W": mode_1.p_total_w,
        # THERM-EQN-001 §11: Δθ_mid is the internal rise at mid-height and
        # Δθ_top the rise at the top, which is what the external surface sees.
        "delta_theta_i_K": mode_1.delta_theta_mid_k,
        "delta_theta_e_K": mode_1.delta_theta_top_k,
        "delta_theta_total_K": mode_1.delta_theta_total_k,
        "coefficient_c": mode_1.coefficient_c,
        "effective_cooling_area_m2": mode_1.effective_cooling_area_m2,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def solve_json(
    payload: Mapping[str, Any],
    *,
    run_id: str | None = None,
    iec60890_coefficients: IEC60890Coefficients | None = None,
) -> dict[str, Any]:
    """
    Solve an M0-03 document and return an M0-04 document (CR-TECH-001).

    This never raises on a modelling or convergence failure: a FAILED or
    NON_CONVERGED M0-04 document carrying the reason is more useful to the API
    layer, and to the engineer, than an exception. It does raise
    `ContractError` when the input cannot be mapped at all, because that is an
    invalid request rather than a thermal answer.
    """
    mapped = input_snapshot_from_json(
        payload, run_id=run_id, iec60890_coefficients=iec60890_coefficients
    )

    if mapped.blocking_reasons:
        return _blocked_document(mapped)

    result = ZonalSolver().solve(mapped.snapshot)
    document = result_to_json(result, mapped)
    _append_mapping_warnings(document, mapped)
    return document


def _blocked_document(mapped: ContractInput) -> dict[str, Any]:
    """An M0-04 document for a mode that may not be run at all."""
    ambient_k = mapped.snapshot.boundary_conditions.ambient_temperature_k
    reason = " ".join(mapped.blocking_reasons)
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "run_id": mapped.snapshot.calculation_id,
        "mode": mapped.mode,
        "status": SolverStatus.FAILED.value,
        "engine_version": ENGINE_VERSION,
        "standard_profile": list(mapped.standard_profile),
        "failure_reason": reason,
        "solver_summary": {
            "outer_iterations_used": 0,
            "inner_iterations_total": 0,
            "wall_clock_s": 0.0,
            "final_max_delta_T_K": 0.0,
            "final_energy_imbalance_fraction": 0.0,
            "final_mass_imbalance_fraction": None,
            "convergence_trace": [],
        },
        "temperatures": {"ambient_K": ambient_k, "entities": [], "thermal_cells": []},
        "hotspots": [],
        "derating": [],
        "compliance": {
            "overall_compliant": False,
            "checks": [
                {
                    "check_id": "MODE_NOT_APPLICABLE",
                    "entity_id": mapped.snapshot.calculation_id,
                    "entity_type": "CALCULATION",
                    "name": None,
                    "standard": mapped.standard_profile[0],
                    "clause": "—",
                    "limit_K": 0.0,
                    "actual_rise_K": 0.0,
                    "margin_K": 0.0,
                    "status": "NOT_APPLICABLE",
                    "note": reason,
                }
            ],
        },
        "airflow": None,
        "library_manifest_echo": dict(mapped.snapshot.library_manifest),
        "sensitivity_summary": None,
        "k_ac_warnings": [],
        "mode_1_result": None,
    }


def _append_mapping_warnings(
    document: dict[str, Any], mapped: ContractInput
) -> None:
    """
    Surface the mapping-time warnings in the compliance section.

    M0-04 has no free-form warning list, and a warning that reaches nobody is
    not a warning. Recording them as NOT_APPLICABLE checks puts them where the
    report and the UI already look.
    """
    if not mapped.warnings:
        return
    checks = document["compliance"]["checks"]
    for code, message in mapped.warnings:
        checks.append(
            {
                "check_id": code,
                "entity_id": mapped.snapshot.calculation_id,
                "entity_type": "MODEL",
                "name": None,
                "standard": mapped.standard_profile[0],
                "clause": "—",
                "limit_K": 0.0,
                "actual_rise_K": 0.0,
                "margin_K": 0.0,
                "status": "NOT_APPLICABLE",
                "note": message,
            }
        )


class JsonThermalSolver(ThermalSolverInterface):
    """
    The engine behind the API's `ThermalSolverInterface`.

    Replaces `NotImplementedSolver`: it accepts a versioned M0-03 document and
    returns a versioned M0-04 document, with no dependency on FastAPI,
    SQLAlchemy or any HTTP framework (CR-TECH-001).

    The licensed IEC TR 60890 coefficients, when the deployment has them, are
    injected here by the API layer; they are never read from this repository
    (CR-ENG-002).
    """

    def __init__(
        self,
        *,
        run_id: str | None = None,
        iec60890_coefficients: IEC60890Coefficients | None = None,
    ) -> None:
        self._run_id = run_id
        self._coefficients = iec60890_coefficients

    def solve(self, input_snapshot: dict[str, Any]) -> dict[str, Any]:
        """Solve an M0-03 document; see `solve_json`."""
        return solve_json(
            input_snapshot,
            run_id=self._run_id,
            iec60890_coefficients=self._coefficients,
        )


def content_hash(document: Mapping[str, Any]) -> str:
    """
    SHA-256 of a canonical JSON rendering, for the audit trail (M0-09).

    Used to prove that a stored result belongs to the input it claims, and
    that neither has been edited since.
    """
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

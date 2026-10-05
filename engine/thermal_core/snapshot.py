"""
M4 InputSnapshot — the immutable, versioned boundary between M3 and the solver.

All values in SI base units (CR-ENG-013, M0-10).
Temperatures in kelvin (CR-ENG-003).
No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).

The solver accepts an InputSnapshot and returns a ResultSnapshot.
It never queries databases, libraries, or any external system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from thermal_core.benchmarks.iec60890 import IEC60890Coefficients
from thermal_core.heat_source import HeatSourceMap

# ---------------------------------------------------------------------------
# Calculation modes (must match API-layer enum)
# ---------------------------------------------------------------------------


class CalculationMode(str, Enum):
    """
    The four thermal calculation modes supported by the platform.

    MODE_1 and MODE_2 apply to naturally ventilated enclosures.
    MODE_3 requires forced ventilation.
    CR-ENG-006: if any opening is forced, MODE_1 is automatically disabled.
    """
    MODE_1 = "MODE_1"   # IEC TR 60890 empirical
    MODE_2 = "MODE_2"   # Nodal thermal network (CT145)
    MODE_3 = "MODE_3"   # Forced-ventilation airflow network
    MODE_4 = "MODE_4"   # CFD export/import adapter


# ---------------------------------------------------------------------------
# Surface orientation (needed for convection correlation selection)
# ---------------------------------------------------------------------------


class SurfaceOrientation(str, Enum):
    """Orientation of an enclosure surface relative to gravity."""
    VERTICAL = "VERTICAL"
    HORIZONTAL_UP = "HORIZONTAL_UP"     # heated face points upward
    HORIZONTAL_DOWN = "HORIZONTAL_DOWN" # heated face points downward
    INCLINED = "INCLINED"               # non-standard; treated as vertical


# ---------------------------------------------------------------------------
# Geometry snapshot — lightweight copy for the solver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfaceSnapshot:
    """
    One enclosure wall or partition surface.

    All physical dimensions in SI (m, m², dimensionless).
    """
    surface_id: str
    compartment_id: str          # compartment this surface bounds (interior side)
    area_m2: float               # net area in m²
    orientation: SurfaceOrientation
    emissivity: float            # radiative emissivity ε ∈ [0, 1]
    thickness_m: float           # wall/partition thickness [m]; 0 = thin partition
    thermal_conductivity_w_per_m_k: float  # wall material k [W/(m·K)]
    is_external: bool            # True → exterior surface; external convection applies
    # For an internal partition, the compartment on the far side. None means the
    # partition faces no modelled compartment, in which case it is adiabatic and
    # carries no heat in steady state.
    adjacent_compartment_id: str | None = None
    # Emissivity of the interior face, if it differs from `emissivity` (which
    # describes the face that radiates to the surroundings).
    internal_emissivity: float | None = None
    # True when the surface is listed in the enclosure's `restricted_surfaces`
    # (wall-mounted, abutting another cubicle). Such a surface exchanges no heat
    # with the surroundings, the conservative treatment required by M0-06.
    is_restricted: bool = False
    # Human-readable label, e.g. "Front panel — Device chamber". The surface_id
    # is a key and reads like one; a result that names surfaces by key is a
    # result nobody can check.
    name: str | None = None

    def __post_init__(self) -> None:
        if self.area_m2 <= 0:
            raise ValueError(f"SurfaceSnapshot.area_m2 must be > 0; got {self.area_m2}")
        if not (0.0 <= self.emissivity <= 1.0):
            raise ValueError(f"SurfaceSnapshot.emissivity must be in [0, 1]; got {self.emissivity}")
        if self.thickness_m < 0:
            raise ValueError(f"SurfaceSnapshot.thickness_m must be >= 0; got {self.thickness_m}")
        if self.thermal_conductivity_w_per_m_k <= 0:
            raise ValueError(
                f"SurfaceSnapshot.thermal_conductivity_w_per_m_k must be > 0; "
                f"got {self.thermal_conductivity_w_per_m_k}"
            )
        if self.internal_emissivity is not None and not (0.0 <= self.internal_emissivity <= 1.0):
            raise ValueError(
                f"SurfaceSnapshot.internal_emissivity must be in [0, 1]; "
                f"got {self.internal_emissivity}"
            )
        if self.is_external and self.adjacent_compartment_id is not None:
            raise ValueError(
                f"SurfaceSnapshot {self.surface_id!r} is external and therefore cannot "
                f"also border compartment {self.adjacent_compartment_id!r}"
            )


@dataclass(frozen=True)
class OpeningSnapshot:
    """
    A ventilation opening connecting two compartments, or a compartment to ambient.

    Used for both natural openings (orifice flow) and forced openings (fan outlets).
    """
    opening_id: str
    from_compartment_id: str | None  # None → from external ambient
    to_compartment_id: str | None    # None → to external ambient
    free_area_m2: float                 # net open area [m²]
    discharge_coefficient: float        # Cd, dimensionless ∈ (0, 1]
    centroid_height_m: float            # height of centroid above enclosure base [m]
    is_forced: bool                     # True → fan-driven; flow given in BoundaryConditions
    fan_id: str | None               # library fan id if forced

    def __post_init__(self) -> None:
        if self.free_area_m2 <= 0:
            raise ValueError(f"OpeningSnapshot.free_area_m2 must be > 0; got {self.free_area_m2}")
        if not (0.0 < self.discharge_coefficient <= 1.0):
            raise ValueError(
                f"OpeningSnapshot.discharge_coefficient must be in (0, 1]; "
                f"got {self.discharge_coefficient}"
            )
        if self.centroid_height_m < 0:
            raise ValueError(
                f"OpeningSnapshot.centroid_height_m must be >= 0; got {self.centroid_height_m}"
            )


@dataclass(frozen=True)
class CompartmentSnapshot:
    """
    One thermally isolated compartment inside the enclosure.

    The solver computes one mean air temperature per compartment in MODE 2/3.
    """
    compartment_id: str
    volume_m3: float
    height_m: float              # internal clear height [m] — used for buoyancy length scale
    width_m: float               # internal clear width [m]
    depth_m: float               # internal clear depth [m]
    surface_ids: tuple[str, ...] # IDs of SurfaceSnapshot objects bounding this compartment
    heat_source_ids: tuple[str, ...]  # IDs of HeatSource objects in this compartment

    def __post_init__(self) -> None:
        if self.volume_m3 <= 0:
            raise ValueError(f"CompartmentSnapshot.volume_m3 must be > 0; got {self.volume_m3}")
        if self.height_m <= 0:
            raise ValueError(f"CompartmentSnapshot.height_m must be > 0; got {self.height_m}")
        if self.width_m <= 0:
            raise ValueError(f"CompartmentSnapshot.width_m must be > 0; got {self.width_m}")
        if self.depth_m <= 0:
            raise ValueError(f"CompartmentSnapshot.depth_m must be > 0; got {self.depth_m}")


@dataclass(frozen=True)
class GeometrySnapshot:
    """
    Complete enclosure geometry for the solver.

    This is a pure-python, database-free snapshot of the M2 geometry model.
    """
    enclosure_id: str
    total_height_m: float            # overall enclosure height [m] — for stack-effect calc
    total_external_surface_area_m2: float  # total outer surface [m²] — for global UA
    compartments: tuple[CompartmentSnapshot, ...]
    surfaces: tuple[SurfaceSnapshot, ...]
    openings: tuple[OpeningSnapshot, ...]

    def __post_init__(self) -> None:
        if self.total_height_m <= 0:
            raise ValueError(
                f"GeometrySnapshot.total_height_m must be > 0; got {self.total_height_m}"
            )
        if self.total_external_surface_area_m2 <= 0:
            raise ValueError(
                f"GeometrySnapshot.total_external_surface_area_m2 must be > 0; "
                f"got {self.total_external_surface_area_m2}"
            )
        if not self.compartments:
            raise ValueError("GeometrySnapshot must have at least one compartment")

    def surface_by_id(self, surface_id: str) -> SurfaceSnapshot | None:
        """Look up a surface by its ID."""
        for s in self.surfaces:
            if s.surface_id == surface_id:
                return s
        return None

    def compartment_by_id(self, compartment_id: str) -> CompartmentSnapshot | None:
        """Look up a compartment by its ID."""
        for c in self.compartments:
            if c.compartment_id == compartment_id:
                return c
        return None

    def openings_for_compartment(self, compartment_id: str) -> list[OpeningSnapshot]:
        """Return all openings that connect to the given compartment."""
        return [
            o for o in self.openings
            if o.from_compartment_id == compartment_id
            or o.to_compartment_id == compartment_id
        ]


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryConditions:
    """
    External environmental conditions imposed on the enclosure boundary.

    Temperatures in kelvin (CR-ENG-003).
    """
    ambient_temperature_k: float        # T_amb [K] — must be > 0
    ambient_pressure_pa: float          # P_amb [Pa], typically 101 325
    ambient_relative_humidity: float    # φ ∈ [0, 1], dimensionless
    forced_flow_m3_per_s: dict[str, float] = field(default_factory=dict)
    # ^ opening_id → volumetric flow rate [m³/s], positive = into enclosure

    def __post_init__(self) -> None:
        if self.ambient_temperature_k <= 0:
            raise ValueError(
                f"BoundaryConditions.ambient_temperature_k must be > 0 K; "
                f"got {self.ambient_temperature_k}"
            )
        if self.ambient_pressure_pa <= 0:
            raise ValueError(
                f"BoundaryConditions.ambient_pressure_pa must be > 0 Pa; "
                f"got {self.ambient_pressure_pa}"
            )
        if not (0.0 <= self.ambient_relative_humidity <= 1.0):
            raise ValueError(
                f"BoundaryConditions.ambient_relative_humidity must be in [0, 1]; "
                f"got {self.ambient_relative_humidity}"
            )
        for opening_id, flow in self.forced_flow_m3_per_s.items():
            if flow < 0:
                raise ValueError(
                    f"BoundaryConditions.forced_flow_m3_per_s[{opening_id!r}] must be >= 0; "
                    f"got {flow}"
                )


# ---------------------------------------------------------------------------
# Solver settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverSettings:
    """
    Numerical solver configuration.

    Default values reflect the engineering guideline for typical switchboard models.
    """
    calculation_mode: CalculationMode
    max_iterations: int = 200
    convergence_tolerance_k: float = 0.01       # |ΔT| < this → converged [K]
    relaxation_factor: float = 0.7              # ω for successive substitution
    enable_radiation: bool = True
    enable_natural_convection: bool = True
    enable_forced_convection: bool = True
    enable_ventilation: bool = True             # buoyancy / fan air transport
    t_ref_k: float = 293.15                     # reference temperature for material props
    # THERM-NET-001 §12: stop early rather than grind to max_iterations when the
    # residual grows for this many consecutive iterations.
    divergence_patience: int = 5

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1; got {self.max_iterations}")
        if self.convergence_tolerance_k <= 0:
            raise ValueError(
                f"convergence_tolerance_k must be > 0 K; got {self.convergence_tolerance_k}"
            )
        if not (0.0 < self.relaxation_factor <= 1.0):
            raise ValueError(
                f"relaxation_factor must be in (0, 1]; got {self.relaxation_factor}"
            )


# ---------------------------------------------------------------------------
# InputSnapshot — the complete, versioned solver input
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InputSnapshot:
    """
    The immutable, versioned input to the M4 thermal solver.

    The solver:
    - accepts an InputSnapshot
    - returns a ResultSnapshot
    - never queries databases, libraries, or any external system (CR-TECH-001)
    - produces bit-identical results for identical inputs (deterministic, rule 6)

    schema_version and library_manifest are required (CR-TECH-002).
    """
    schema_version: str                  # e.g. "4.0.0"
    library_manifest: dict[str, str]     # library_type → sha256 / version_tag
    calculation_id: str                  # UUID string — for audit trail
    geometry: GeometrySnapshot
    heat_source_map: HeatSourceMap       # from M3
    boundary_conditions: BoundaryConditions
    solver_settings: SolverSettings
    # MODE_1 only. CR-ENG-002: the IEC TR 60890 coefficient tables are licensed
    # and never shipped in this repository, so they arrive here from the
    # administrator-imported dataset. None means MODE_1 cannot run.
    iec60890_coefficients: IEC60890Coefficients | None = None

    def __post_init__(self) -> None:
        if not self.schema_version:
            raise ValueError("InputSnapshot.schema_version must not be empty")
        if not self.calculation_id:
            raise ValueError("InputSnapshot.calculation_id must not be empty")
        # Consistency: forced openings must be declared in geometry
        geo_opening_ids = {o.opening_id for o in self.geometry.openings}
        for oid in self.boundary_conditions.forced_flow_m3_per_s:
            if oid not in geo_opening_ids:
                raise ValueError(
                    f"forced_flow opening {oid!r} not found in geometry.openings"
                )

"""
M4 ResultSnapshot — the immutable, versioned thermal solver output.

All temperatures in kelvin (CR-ENG-003).
All values in SI base units (CR-ENG-013, M0-10).
No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).

CR-ENG-005: unconverged results have status=NON_CONVERGED and the UI
must display a "RESULT INVALID" watermark.  The solver always returns a
ResultSnapshot — it never raises on convergence failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------


class SolverStatus(str, Enum):
    """Final status of a thermal solver run."""
    CONVERGED = "CONVERGED"             # solution accepted; temperatures valid
    NON_CONVERGED = "NON_CONVERGED"     # iteration limit reached; CR-ENG-005
    FAILED = "FAILED"                   # solver could not proceed (bad inputs, singular matrix)


class NodeType(str, Enum):
    """Type of thermal network node in the result."""
    AIR = "AIR"            # compartment mean air temperature
    SURFACE = "SURFACE"    # outer face of an external wall — operator-accessible
    # Inner wall faces and internal partitions. Kept distinct from SURFACE
    # because the IEC 61439 accessible-surface limit applies to what an
    # operator can touch, and nobody touches the inside of a closed enclosure.
    INTERNAL_SURFACE = "INTERNAL_SURFACE"
    DEVICE = "DEVICE"      # device casing temperature
    BUSBAR = "BUSBAR"      # busbar conductor temperature
    JOINT = "JOINT"        # busbar joint / bolted connection
    CABLE = "CABLE"        # cable or conductor run
    ENTITY = "ENTITY"      # any other heat-generating entity body
    AMBIENT = "AMBIENT"    # external environment (fixed boundary)


# ---------------------------------------------------------------------------
# Per-node results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeTemperature:
    """
    Temperature result for a single thermal network node.

    temperature_k is in kelvin (CR-ENG-003).
    """
    node_id: str
    node_type: NodeType
    temperature_k: float
    heat_generation_w: float        # power injected at this node [W]
    net_heat_flux_w_per_m2: float | None  # None for non-surface nodes
    # Links the node back to the engineering entity it represents, so the API
    # layer can report temperatures against the user's own objects rather than
    # against internal node ids.
    entity_id: str | None = None
    name: str | None = None
    compartment_id: str | None = None

    def temperature_celsius(self) -> float:
        """Convenience accessor — NOT used inside the solver (CR-ENG-013)."""
        return self.temperature_k - 273.15

    def __post_init__(self) -> None:
        if self.temperature_k <= 0:
            raise ValueError(
                f"NodeTemperature.temperature_k must be > 0 K; got {self.temperature_k}"
            )


# ---------------------------------------------------------------------------
# Convergence diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConvergenceTrace:
    """One row of the convergence history for a solver iteration."""
    iteration: int
    max_delta_k: float       # max |ΔT| across all nodes this iteration [K]
    rms_delta_k: float       # RMS |ΔT| across all nodes [K]
    energy_balance_error_w: float   # |Q_in - Q_out| summed over all nodes [W]
    ua_total_w_per_k: float | None  # total conductance (diagnostic) [W/K]

    def __post_init__(self) -> None:
        if self.iteration < 0:
            raise ValueError(f"ConvergenceTrace.iteration must be >= 0; got {self.iteration}")
        if self.max_delta_k < 0:
            raise ValueError(f"ConvergenceTrace.max_delta_k must be >= 0; got {self.max_delta_k}")
        if self.rms_delta_k < 0:
            raise ValueError(f"ConvergenceTrace.rms_delta_k must be >= 0; got {self.rms_delta_k}")


# ---------------------------------------------------------------------------
# Compartment-level aggregates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompartmentResult:
    """
    Aggregated thermal results for one compartment.

    All temperatures in kelvin (CR-ENG-003).
    """
    compartment_id: str
    mean_air_temperature_k: float
    max_device_temperature_k: float | None
    max_surface_temperature_k: float | None
    total_heat_generation_w: float
    heat_to_ambient_w: float

    def mean_air_temperature_celsius(self) -> float:
        return self.mean_air_temperature_k - 273.15


# ---------------------------------------------------------------------------
# Warnings — structured engineering messages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OpeningFlow:
    """
    Volumetric air flow through one ventilation opening.

    Sign convention: positive means air flows *into* the enclosure (or into
    `to_compartment_id`), negative means it flows out. Reverse flow is reported
    rather than clamped to zero, per DR-005.
    """
    opening_id: str
    volumetric_flow_m3_per_s: float
    mass_flow_kg_per_s: float
    is_forced: bool

    @property
    def direction(self) -> str:
        """\"IN\" when air enters, \"OUT\" when it leaves."""
        return "IN" if self.volumetric_flow_m3_per_s >= 0.0 else "OUT"


@dataclass(frozen=True)
class AirflowSummary:
    """
    Airflow-network results for MODE 2 (buoyancy) and MODE 3 (forced).

    None on a result means no airflow network was solved.
    """
    total_flow_rate_m3_per_s: float
    buoyancy_stack_pressure_pa: float | None
    opening_flows: tuple[OpeningFlow, ...]


@dataclass(frozen=True)
class SolverWarning:
    """
    A structured engineering warning from the solver.

    Warnings are informational — they do not stop the solver but must be
    surfaced to the engineer in the UI and report (CR-ENG-011 etc.).
    """
    code: str           # e.g. "WARN-011-KAC-ONE", "WARN-005-NON-CONVERGED"
    message: str        # human-readable description
    entity_id: str | None = None   # which entity triggered this warning


# ---------------------------------------------------------------------------
# ResultSnapshot — the complete, versioned solver output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultSnapshot:
    """
    The immutable, versioned output from the M4 thermal solver.

    CR-ENG-005: if status is NON_CONVERGED, the consumer (API / UI) MUST
    display a "RESULT INVALID" watermark and refuse to generate a compliance
    report.

    schema_version must match the InputSnapshot.schema_version that produced
    this result — the pair forms an auditable calculation record.
    """
    schema_version: str
    calculation_id: str              # matches InputSnapshot.calculation_id
    status: SolverStatus

    # Per-node temperature field
    node_temperatures: tuple[NodeTemperature, ...]

    # Compartment aggregates
    compartment_results: tuple[CompartmentResult, ...]

    # Convergence diagnostics (one entry per iteration)
    convergence_trace: tuple[ConvergenceTrace, ...]

    # Global energy audit
    total_heat_generation_w: float   # sum of all HeatSource.power_loss_w
    total_heat_dissipation_w: float  # total heat leaving via all surfaces + openings
    energy_balance_error_percent: float  # |gen - diss| / gen × 100

    # Elapsed wall-clock time
    elapsed_seconds: float

    # Structured warnings (ordered by severity)
    warnings: tuple[SolverWarning, ...]

    # Airflow network results; None when no ventilation was modelled.
    airflow: AirflowSummary | None = None

    # IEC TR 60890 outputs; populated only for MODE_1.
    mode_1: Mode1Result | None = None

    @property
    def is_valid(self) -> bool:
        """True only if the result is converged and may be used for compliance."""
        return self.status == SolverStatus.CONVERGED

    def entity_temperatures(self) -> tuple[NodeTemperature, ...]:
        """Node temperatures that correspond to a user-visible entity."""
        return tuple(n for n in self.node_temperatures if n.entity_id is not None)

    def max_air_temperature_k(self) -> float | None:
        """Maximum compartment air temperature across all compartments [K]."""
        air_nodes = [n for n in self.node_temperatures if n.node_type == NodeType.AIR]
        if not air_nodes:
            return None
        return max(n.temperature_k for n in air_nodes)

    def node_by_id(self, node_id: str) -> NodeTemperature | None:
        """Look up a node temperature by ID."""
        for n in self.node_temperatures:
            if n.node_id == node_id:
                return n
        return None

    def compartment_result_by_id(self, compartment_id: str) -> CompartmentResult | None:
        """Look up compartment results by compartment ID."""
        for cr in self.compartment_results:
            if cr.compartment_id == compartment_id:
                return cr
        return None


# ---------------------------------------------------------------------------
# IEC TR 60890 (MODE 1) outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Mode1Result:
    """
    IEC TR 60890 empirical results (MODE 1).

    CR-ENG-002: every coefficient behind these numbers comes from the
    administrator-imported licensed dataset, never from this repository.
    All temperature rises in kelvin (CR-ENG-003).
    """
    p_total_w: float
    effective_cooling_area_m2: float
    coefficient_c: float
    delta_theta_mid_k: float
    delta_theta_top_k: float
    delta_theta_total_k: float

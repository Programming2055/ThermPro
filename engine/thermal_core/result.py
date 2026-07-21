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

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
    SURFACE = "SURFACE"    # enclosure wall / partition surface
    DEVICE = "DEVICE"      # device casing temperature (where computed)
    BUSBAR = "BUSBAR"      # busbar conductor temperature
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
    net_heat_flux_w_per_m2: Optional[float]  # None for non-surface nodes

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
    ua_total_w_per_k: Optional[float]  # total conductance (diagnostic) [W/K]

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
    max_device_temperature_k: Optional[float]
    max_surface_temperature_k: Optional[float]
    total_heat_generation_w: float
    heat_to_ambient_w: float

    def mean_air_temperature_celsius(self) -> float:
        return self.mean_air_temperature_k - 273.15


# ---------------------------------------------------------------------------
# Warnings — structured engineering messages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverWarning:
    """
    A structured engineering warning from the solver.

    Warnings are informational — they do not stop the solver but must be
    surfaced to the engineer in the UI and report (CR-ENG-011 etc.).
    """
    code: str           # e.g. "WARN-011-KAC-ONE", "WARN-005-NON-CONVERGED"
    message: str        # human-readable description
    entity_id: Optional[str] = None   # which entity triggered this warning


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

    @property
    def is_valid(self) -> bool:
        """True only if the result is converged and may be used for compliance."""
        return self.status == SolverStatus.CONVERGED

    def max_air_temperature_k(self) -> Optional[float]:
        """Maximum compartment air temperature across all compartments [K]."""
        air_nodes = [n for n in self.node_temperatures if n.node_type == NodeType.AIR]
        if not air_nodes:
            return None
        return max(n.temperature_k for n in air_nodes)

    def node_by_id(self, node_id: str) -> Optional[NodeTemperature]:
        """Look up a node temperature by ID."""
        for n in self.node_temperatures:
            if n.node_id == node_id:
                return n
        return None

    def compartment_result_by_id(self, compartment_id: str) -> Optional[CompartmentResult]:
        """Look up compartment results by compartment ID."""
        for cr in self.compartment_results:
            if cr.compartment_id == compartment_id:
                return cr
        return None

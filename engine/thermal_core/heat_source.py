"""
HeatSource — the central M3 engineering object.

Every placed entity (device, busbar, joint, cable) exposes a HeatSource
that quantifies WHERE heat is generated and HOW MUCH, but never WHAT
TEMPERATURE results (that is M4's responsibility).

All values are in SI base units (CR-ENG-013, M0-10).
No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from thermal_core.geometry import Point3D


# ---------------------------------------------------------------------------
# Classification enumerations
# ---------------------------------------------------------------------------


class HeatSourceEntityType(str, Enum):
    """The category of engineering object that generates heat."""

    DEVICE = "DEVICE"          # circuit breaker, contactor, relay, VFD, etc.
    BUSBAR = "BUSBAR"          # main busbars, sub-busbars, riser bars
    JOINT = "JOINT"            # bolted or clamped busbar connections
    CABLE = "CABLE"            # power cable run within the enclosure
    TRANSFORMER = "TRANSFORMER"
    RESISTOR = "RESISTOR"      # braking resistors, neutral earthing resistors
    OTHER = "OTHER"


class LossCalculationSource(str, Enum):
    """
    How the power loss figure was computed for this HeatSource.

    This drives the audit trail required by the engineering methodology.
    """

    MANUFACTURER_CURVE = "MANUFACTURER_CURVE"       # interpolated from device library curve
    MANUFACTURER_RATED = "MANUFACTURER_RATED"       # single rated-loss figure from datasheet
    IEC_60890_TABLE = "IEC_60890_TABLE"             # IEC TR 60890 empirical coefficient
    DC_RESISTANCE_CALC = "DC_RESISTANCE_CALC"       # I²·R_DC(T_ref) computation
    AC_RESISTANCE_CALC = "AC_RESISTANCE_CALC"       # I²·R_AC with K_AC correction
    JOINT_RESISTANCE = "JOINT_RESISTANCE"           # I²·R_joint from connection library
    USER_OVERRIDE = "USER_OVERRIDE"                 # engineer has manually specified
    ESTIMATED_FRACTION = "ESTIMATED_FRACTION"       # fraction of upstream device loss
    UNKNOWN = "UNKNOWN"                             # source not determined


# ---------------------------------------------------------------------------
# Loss breakdown (optional detailed sub-allocation)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LossBreakdown:
    """
    Optional sub-allocation of a total power loss into physical mechanisms.

    All values in watts (SI). Any field may be None if not disaggregated.
    """

    joule_loss_w: Optional[float] = None        # I²R resistive loss
    switching_loss_w: Optional[float] = None    # semi-conductor switching (for electronics)
    iron_loss_w: Optional[float] = None         # magnetic core loss (transformers)
    contact_loss_w: Optional[float] = None      # contact resistance contribution
    other_w: Optional[float] = None


# ---------------------------------------------------------------------------
# HeatSource — the primary M3 output object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeatSource:
    """
    Power heat emitted by a single placed engineering entity.

    This is the central M3 object.  Every device, busbar segment, joint,
    and cable placement produces exactly one HeatSource.  The M4 solver
    consumes these as boundary conditions for the thermal network.

    Attributes
    ----------
    source_id:
        UUID string — unique identifier for this HeatSource instance.
    entity_type:
        Category of the generating object (HeatSourceEntityType).
    entity_id:
        UUID string of the placed entity (DevicePlacement, BusbarPlacement, …).
    power_loss_w:
        Total power dissipated in watts (SI).  Must be ≥ 0.
    location:
        Centroid of the heat source in the enclosure coordinate system (metres).
    volume_m3:
        Heat-generation volume in m³ (SI).  Used by M4 for volumetric source
        density (W/m³).  None for point sources.
    surface_area_m2:
        Exposed surface area in m² (SI).  Used by M4 for surface heat flux
        density (W/m²).  None if not applicable.
    confidence:
        Engineering confidence level of the loss figure (LossConfidence).
    calculation_source:
        How the loss was derived (LossCalculationSource).
    library_ref:
        Identifier of the library entry used, format "entry_id@version".
        None if computed without a library entry.
    operating_current_a:
        Actual operating current in amperes (SI) used for the loss calculation.
        None if the loss figure is current-independent (e.g. fixed overhead loss).
    current_fraction:
        operating_current_a / rated_current_a (dimensionless).
        None if not applicable.
    breakdown:
        Optional fine-grained loss sub-allocation.
    """

    source_id: str
    entity_type: HeatSourceEntityType
    entity_id: str
    power_loss_w: float
    location: Point3D
    volume_m3: Optional[float]
    surface_area_m2: Optional[float]
    confidence: "LossConfidence"  # imported from libraries.py at call site
    calculation_source: LossCalculationSource
    library_ref: Optional[str]
    operating_current_a: Optional[float]
    current_fraction: Optional[float]
    breakdown: Optional[LossBreakdown] = None

    def __post_init__(self) -> None:
        if self.power_loss_w < 0:
            raise ValueError(
                f"HeatSource.power_loss_w must be >= 0 (watts); got {self.power_loss_w}"
            )
        if self.volume_m3 is not None and self.volume_m3 <= 0:
            raise ValueError(
                f"HeatSource.volume_m3 must be > 0 (m³); got {self.volume_m3}"
            )
        if self.surface_area_m2 is not None and self.surface_area_m2 <= 0:
            raise ValueError(
                f"HeatSource.surface_area_m2 must be > 0 (m²); got {self.surface_area_m2}"
            )
        if self.operating_current_a is not None and self.operating_current_a < 0:
            raise ValueError(
                f"HeatSource.operating_current_a must be >= 0 (A); got {self.operating_current_a}"
            )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    def volumetric_power_density_w_per_m3(self) -> Optional[float]:
        """W/m³ — None if volume is not set."""
        if self.volume_m3 is None or self.volume_m3 == 0:
            return None
        return self.power_loss_w / self.volume_m3

    def surface_heat_flux_w_per_m2(self) -> Optional[float]:
        """W/m² — None if surface_area is not set."""
        if self.surface_area_m2 is None or self.surface_area_m2 == 0:
            return None
        return self.power_loss_w / self.surface_area_m2


# ---------------------------------------------------------------------------
# HeatSourceMap — query interface for M3 output
# ---------------------------------------------------------------------------


@dataclass
class HeatSourceMap:
    """
    Collection of all HeatSource objects for a single enclosure.

    This is the primary M3 output that M4 consumes.
    No temperatures are computed here.

    Answers the M3 query questions:
      - Where are all heat sources?         → iterate sources
      - How much heat?                      → sum(s.power_loss_w for s in sources)
      - Which sources are in a compartment? → by_compartment()
    """

    enclosure_id: str
    sources: list[HeatSource] = field(default_factory=list)

    # Metadata about how this map was constructed
    library_manifest: dict[str, str] = field(default_factory=dict)
    # ^ maps library_type → version_tag, e.g. {"device": "1.0.0", "busbar": "1.0.0"}

    # ------------------------------------------------------------------
    # Aggregate queries (pure, no side-effects)
    # ------------------------------------------------------------------

    def total_power_loss_w(self) -> float:
        """Sum of all heat source power in watts."""
        return sum(s.power_loss_w for s in self.sources)

    def by_entity_type(self, entity_type: HeatSourceEntityType) -> list[HeatSource]:
        """Filter sources by entity type."""
        return [s for s in self.sources if s.entity_type == entity_type]

    def by_entity_id(self, entity_id: str) -> Optional[HeatSource]:
        """Look up the HeatSource for a specific placed entity."""
        for s in self.sources:
            if s.entity_id == entity_id:
                return s
        return None

    def confidence_summary(self) -> dict[str, int]:
        """Count sources by confidence level for audit reporting."""
        from thermal_core.libraries import LossConfidence
        result: dict[str, int] = {c.value: 0 for c in LossConfidence}
        for s in self.sources:
            key = s.confidence if isinstance(s.confidence, str) else s.confidence.value
            result[key] = result.get(key, 0) + 1
        return result

    def has_low_confidence_sources(self) -> bool:
        """True if any source is ESTIMATED or ASSUMED_DEFAULT."""
        from thermal_core.libraries import LossConfidence
        low = {LossConfidence.ESTIMATED, LossConfidence.ASSUMED_DEFAULT}
        return any(s.confidence in low for s in self.sources)

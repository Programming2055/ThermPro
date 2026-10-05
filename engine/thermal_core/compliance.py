"""
Standards compliance interpretation.

CR-ENG-009: compliance is standard-profile-aware. The thermal solution is the
same whichever standard is being claimed; only the limits, the clause
references and the report wording change. This module is that interpretation
layer, and it is kept strictly separate from the solver so that adding a
profile never touches the physics.

Limits are *configurable reference values*, as THERM-STD-001 §6 requires. The
defaults below reproduce the table in that document, but a project may pass its
own `LimitSet`, and a device's own manufacturer limit always takes precedence
over a generic one (CR-ENG-010's data hierarchy applied to temperature limits).

CR-ENG-005: a result that did not converge yields no compliance verdict. The
caller gets `overall_compliant = False` and a single explanatory check rather
than a pass built on invalid temperatures.

All temperatures in kelvin; all rises in kelvin above ambient (CR-ENG-003).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from thermal_core.result import NodeTemperature, NodeType, ResultSnapshot, SolverStatus

# A rise within this margin of its limit is reported as a WARNING hotspot:
# close enough that normal modelling uncertainty could put it over.
HOTSPOT_WARNING_MARGIN_K = 5.0


class ComplianceStatus(str, Enum):
    """Outcome of a single compliance check (M0-04 ComplianceCheck.status)."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class HotspotSeverity(str, Enum):
    """Severity of an entity against its own limit (M0-04 Hotspot.severity)."""

    CRITICAL = "CRITICAL"  # limit exceeded
    WARNING = "WARNING"  # within HOTSPOT_WARNING_MARGIN_K of the limit
    OK = "OK"


class StandardProfile(str, Enum):
    """Standards profiles in MVP scope (DR-007). UL/ANSI deferred to Phase 3."""

    IEC_61439_1 = "IEC_61439_1"
    IEC_61439_2 = "IEC_61439_2"
    IEC_TR_60890 = "IEC_TR_60890"
    MANUFACTURER_LIMITS = "MANUFACTURER_LIMITS"
    PROJECT_DEFINED = "PROJECT_DEFINED"


# ---------------------------------------------------------------------------
# Limit definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemperatureLimit:
    """
    One temperature-rise limit from a standard.

    limit_rise_k is a rise *above ambient*, which is how IEC 61439-1 states its
    limits; absolute temperatures are derived from the ambient the run used.
    """

    check_id: str
    standard: str
    clause: str
    description: str
    limit_rise_k: float

    def __post_init__(self) -> None:
        if self.limit_rise_k <= 0:
            raise ValueError(
                f"TemperatureLimit.limit_rise_k must be > 0 K; got {self.limit_rise_k}"
            )


@dataclass(frozen=True)
class LimitSet:
    """
    The limits a standard profile applies, keyed by result node type.

    `air_top` is kept separate because it applies to the enclosure air rather
    than to any single component.
    """

    profile: StandardProfile
    by_node_type: dict[NodeType, TemperatureLimit] = field(default_factory=dict)
    air_top: TemperatureLimit | None = None

    def for_node_type(self, node_type: NodeType) -> TemperatureLimit | None:
        return self.by_node_type.get(node_type)


def iec_61439_limit_set(
    profile: StandardProfile = StandardProfile.IEC_61439_2,
) -> LimitSet:
    """
    Default IEC 61439 temperature-rise limits (THERM-STD-001 §6).

    These are the shipped reference values. The engineer is responsible for
    confirming the edition and amendment current at the time of design, and a
    project may override any of them.
    """
    standard = profile.value
    return LimitSet(
        profile=profile,
        by_node_type={
            NodeType.BUSBAR: TemperatureLimit(
                check_id="TEMP_RISE_BUSBAR_IEC61439",
                standard=standard,
                clause="IEC 61439-1 Table 6",
                description="Busbars and conductors, bare or insulated copper",
                limit_rise_k=70.0,
            ),
            NodeType.JOINT: TemperatureLimit(
                check_id="TEMP_RISE_JOINT_IEC61439",
                standard=standard,
                clause="IEC 61439-1 Table 6",
                description="Terminals and bolted connections for external conductors",
                limit_rise_k=70.0,
            ),
            NodeType.CABLE: TemperatureLimit(
                check_id="TEMP_RISE_CONDUCTOR_IEC61439",
                standard=standard,
                clause="IEC 61439-1 Table 6",
                description="Insulated conductors within the assembly",
                limit_rise_k=70.0,
            ),
            NodeType.SURFACE: TemperatureLimit(
                check_id="TEMP_RISE_ACCESSIBLE_SURFACE_IEC61439",
                standard=standard,
                clause="IEC 61439-1 Table 6",
                description="Operator-accessible external metal surfaces",
                limit_rise_k=55.0,
            ),
        },
        air_top=TemperatureLimit(
            check_id="TEMP_RISE_INTERNAL_AIR_IEC61439",
            standard=standard,
            clause="IEC 61439-1 Table 6 (internal air)",
            description="Internal air at the top of the enclosure",
            limit_rise_k=40.0,
        ),
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComplianceCheck:
    """One evaluated check against one entity."""

    check_id: str
    entity_id: str
    entity_type: str
    name: str | None
    standard: str
    clause: str
    limit_k: float  # limit expressed as a rise [K]
    actual_rise_k: float
    margin_k: float  # limit − actual; positive is compliant
    status: ComplianceStatus
    note: str | None = None


@dataclass(frozen=True)
class Hotspot:
    """An entity at or over its limit."""

    entity_id: str
    entity_type: str
    name: str | None
    temperature_k: float
    temperature_rise_k: float
    limit_k: float
    excess_k: float
    severity: HotspotSeverity


@dataclass(frozen=True)
class DeratingRecommendation:
    """
    Loading advice for an entity.

    `recommended_loading_factor` is a first-order estimate: it assumes the
    temperature rise scales with dissipated power, and that a conductor's power
    scales with the square of its current, so

        I_max / I_now = sqrt(Δθ_limit / Δθ_actual)

    It is a starting point for the engineer, not a substitute for re-running
    the calculation at the reduced current.
    """

    entity_id: str
    entity_type: str
    name: str | None
    current_loading_factor: float
    recommended_loading_factor: float
    margin_k: float
    action_required: bool


@dataclass(frozen=True)
class ComplianceReport:
    """Everything the interpretation layer concluded about one result."""

    overall_compliant: bool
    checks: tuple[ComplianceCheck, ...]
    hotspots: tuple[Hotspot, ...]
    derating: tuple[DeratingRecommendation, ...]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_compliance(
    result: ResultSnapshot,
    ambient_k: float,
    limit_set: LimitSet | None = None,
    entity_limits_k: dict[str, float] | None = None,
    entity_loading_factors: dict[str, float] | None = None,
) -> ComplianceReport:
    """
    Interpret a solved temperature field against a standards profile.

    Parameters
    ----------
    result:
        The solver output. A non-CONVERGED result produces no verdict.
    ambient_k:
        The ambient temperature the run used [K], the datum for every rise.
    limit_set:
        Limits to apply. Defaults to IEC 61439-2.
    entity_limits_k:
        Per-entity absolute limits [K], typically a device's own maximum
        operating temperature. These override the generic limit for that
        entity, because a manufacturer's figure outranks a table default.
    entity_loading_factors:
        entity_id → present load current / rated current, used for derating.

    Returns
    -------
    ComplianceReport
    """
    limits = limit_set or iec_61439_limit_set()
    entity_limits_k = entity_limits_k or {}
    entity_loading_factors = entity_loading_factors or {}

    if result.status != SolverStatus.CONVERGED:
        return ComplianceReport(
            overall_compliant=False,
            checks=(
                ComplianceCheck(
                    check_id="RESULT_NOT_CONVERGED",
                    entity_id=result.calculation_id,
                    entity_type="CALCULATION",
                    name=None,
                    standard=limits.profile.value,
                    clause="—",
                    limit_k=0.0,
                    actual_rise_k=0.0,
                    margin_k=0.0,
                    status=ComplianceStatus.NOT_APPLICABLE,
                    note=(
                        f"The calculation finished with status {result.status.value}. "
                        f"CR-ENG-005: no compliance verdict can be issued from a "
                        f"result that is not converged."
                    ),
                ),
            ),
            hotspots=(),
            derating=(),
        )

    checks: list[ComplianceCheck] = []
    hotspots: list[Hotspot] = []
    derating: list[DeratingRecommendation] = []

    for node in result.node_temperatures:
        limit = _limit_for(node, limits, entity_limits_k, ambient_k)
        if limit is None:
            continue
        entity_id, entity_type, name = _identify(node)
        rise = node.temperature_k - ambient_k
        margin = limit.limit_rise_k - rise
        status = ComplianceStatus.PASS if margin >= 0 else ComplianceStatus.FAIL

        checks.append(
            ComplianceCheck(
                check_id=limit.check_id,
                entity_id=entity_id,
                entity_type=entity_type,
                name=name,
                standard=limit.standard,
                clause=limit.clause,
                limit_k=limit.limit_rise_k,
                actual_rise_k=rise,
                margin_k=margin,
                status=status,
                note=limit.description,
            )
        )

        severity = _severity(margin)
        if severity != HotspotSeverity.OK:
            hotspots.append(
                Hotspot(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    name=name,
                    temperature_k=node.temperature_k,
                    temperature_rise_k=rise,
                    limit_k=limit.limit_rise_k,
                    excess_k=max(-margin, 0.0),
                    severity=severity,
                )
            )

        if node.entity_id is not None and node.node_type != NodeType.SURFACE:
            recommendation = _derating_for(
                entity_id=entity_id,
                entity_type=entity_type,
                name=name,
                rise_k=rise,
                limit_rise_k=limit.limit_rise_k,
                loading_factor=entity_loading_factors.get(entity_id, 1.0),
            )
            if recommendation is not None:
                derating.append(recommendation)

    checks.extend(_air_checks(result, limits, ambient_k))

    overall = all(c.status != ComplianceStatus.FAIL for c in checks)
    # A verdict with nothing to check is not a pass.
    if not checks:
        overall = False

    hotspots.sort(key=lambda h: h.excess_k, reverse=True)
    return ComplianceReport(
        overall_compliant=overall,
        checks=tuple(checks),
        hotspots=tuple(hotspots),
        derating=tuple(derating),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _limit_for(
    node: NodeTemperature,
    limits: LimitSet,
    entity_limits_k: dict[str, float],
    ambient_k: float,
) -> TemperatureLimit | None:
    """
    Pick the limit that governs this node, or None if nothing applies.

    A manufacturer limit for the specific entity wins over the profile table.
    """
    if node.node_type in (NodeType.AMBIENT, NodeType.AIR):
        return None

    if node.entity_id is not None and node.entity_id in entity_limits_k:
        absolute = entity_limits_k[node.entity_id]
        return TemperatureLimit(
            check_id="TEMP_LIMIT_MANUFACTURER",
            standard=StandardProfile.MANUFACTURER_LIMITS.value,
            clause="Device library maximum operating temperature",
            description=(
                f"Manufacturer limit {absolute - 273.15:.1f} °C for this device, "
                f"applied in preference to the generic table value"
            ),
            limit_rise_k=max(absolute - ambient_k, 1e-6),
        )

    if node.node_type == NodeType.DEVICE:
        # Without a manufacturer figure there is no defensible device limit.
        # CR-ENG-010's principle: no universal default is better than a wrong
        # one, so the device is reported with no check rather than a guess.
        return None

    return limits.for_node_type(node.node_type)


def _identify(node: NodeTemperature) -> tuple[str, str, str | None]:
    entity_id = node.entity_id or node.node_id
    return entity_id, node.node_type.value, node.name


def _severity(margin_k: float) -> HotspotSeverity:
    if margin_k < 0:
        return HotspotSeverity.CRITICAL
    if margin_k <= HOTSPOT_WARNING_MARGIN_K:
        return HotspotSeverity.WARNING
    return HotspotSeverity.OK


def _derating_for(
    entity_id: str,
    entity_type: str,
    name: str | None,
    rise_k: float,
    limit_rise_k: float,
    loading_factor: float,
) -> DeratingRecommendation | None:
    if rise_k <= 0:
        return None
    ratio = math.sqrt(limit_rise_k / rise_k)
    recommended = min(loading_factor * ratio, 1.0)
    return DeratingRecommendation(
        entity_id=entity_id,
        entity_type=entity_type,
        name=name,
        current_loading_factor=loading_factor,
        recommended_loading_factor=recommended,
        margin_k=limit_rise_k - rise_k,
        action_required=recommended < loading_factor,
    )


def _air_checks(
    result: ResultSnapshot, limits: LimitSet, ambient_k: float
) -> list[ComplianceCheck]:
    """Check the hottest compartment air against the internal-air limit."""
    if limits.air_top is None:
        return []
    air_nodes = [n for n in result.node_temperatures if n.node_type == NodeType.AIR]
    if not air_nodes:
        return []
    hottest = max(air_nodes, key=lambda n: n.temperature_k)
    rise = hottest.temperature_k - ambient_k
    margin = limits.air_top.limit_rise_k - rise
    return [
        ComplianceCheck(
            check_id=limits.air_top.check_id,
            entity_id=hottest.compartment_id or hottest.node_id,
            entity_type="COMPARTMENT_AIR",
            name=hottest.name,
            standard=limits.air_top.standard,
            clause=limits.air_top.clause,
            limit_k=limits.air_top.limit_rise_k,
            actual_rise_k=rise,
            margin_k=margin,
            status=ComplianceStatus.PASS if margin >= 0 else ComplianceStatus.FAIL,
            note=limits.air_top.description,
        )
    ]

"""
Fan operating point from a pressure-flow (fan) curve and a system curve.

All values in SI base units (CR-ENG-013).
Temperatures in kelvin (CR-ENG-003) where applicable.

The fan library entry stores a `fan_curve` list of
  {flow_m3_per_s, static_pressure_pa, power_w, efficiency}
points.  The LibraryResolver delivers these as a resolved list to the
solver so the solver never queries the library.

System resistance:
    ΔP_sys = K_sys × Q²            [Pa]

Operating point: Q* and ΔP* where ΔP_fan(Q*) = ΔP_sys(Q*)

Equation reference: THERM-EQN-001 §6.7 (Forced Ventilation)
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FanCurvePoint:
    """One point on a fan pressure-flow curve."""
    flow_m3_per_s: float
    static_pressure_pa: float
    power_w: float
    efficiency: float  # dimensionless ∈ [0, 1]


@dataclass(frozen=True)
class FanOperatingPoint:
    """Result of fan-system operating point calculation."""
    flow_m3_per_s: float
    static_pressure_pa: float
    power_w: float       # fan shaft power at this operating point
    efficiency: float    # fan efficiency at this operating point


def _validate_fan_curve(curve: list[FanCurvePoint]) -> None:
    if len(curve) < 2:
        raise ValueError("fan curve must have at least 2 points")
    flows = [p.flow_m3_per_s for p in curve]
    if flows != sorted(flows):
        raise ValueError("fan curve points must be sorted by flow_m3_per_s ascending")
    for p in curve:
        if p.flow_m3_per_s < 0:
            raise ValueError(f"fan curve flow_m3_per_s must be >= 0; got {p.flow_m3_per_s}")
        if p.static_pressure_pa < 0:
            raise ValueError(
                f"fan curve static_pressure_pa must be >= 0; got {p.static_pressure_pa}"
            )


def interpolate_fan_curve(
    curve: list[FanCurvePoint],
    flow_m3_per_s: float,
) -> Optional[FanCurvePoint]:
    """
    Linearly interpolate a fan curve at a given volumetric flow rate.

    Returns None if flow is outside the curve range (extrapolation refused).
    Clamps to endpoints if flow is exactly at the boundary.
    """
    _validate_fan_curve(curve)
    flows = [p.flow_m3_per_s for p in curve]

    if flow_m3_per_s < flows[0] or flow_m3_per_s > flows[-1]:
        return None  # outside range

    # Binary search for the segment
    idx = bisect.bisect_left(flows, flow_m3_per_s)
    if idx == 0:
        return curve[0]
    if idx >= len(curve):
        return curve[-1]
    if flows[idx] == flow_m3_per_s:
        return curve[idx]

    # Linear interpolation
    p0 = curve[idx - 1]
    p1 = curve[idx]
    t = (flow_m3_per_s - p0.flow_m3_per_s) / (p1.flow_m3_per_s - p0.flow_m3_per_s)

    return FanCurvePoint(
        flow_m3_per_s=flow_m3_per_s,
        static_pressure_pa=p0.static_pressure_pa + t * (p1.static_pressure_pa - p0.static_pressure_pa),
        power_w=p0.power_w + t * (p1.power_w - p0.power_w),
        efficiency=p0.efficiency + t * (p1.efficiency - p0.efficiency),
    )


def fan_operating_point(
    curve: list[FanCurvePoint],
    system_resistance_pa_per_m3_per_s_sq: float,
    n_search_points: int = 500,
) -> Optional[FanOperatingPoint]:
    """
    Find the fan-system operating point by bracketed linear search.

    ΔP_fan(Q) = ΔP_sys(Q) = K_sys × Q²

    The system curve must intersect the fan curve within its range.
    Returns None if no intersection is found (e.g. system resistance too high).

    Parameters
    ----------
    curve:
        Fan pressure-flow curve (sorted by flow ascending).
    system_resistance_pa_per_m3_per_s_sq:
        System resistance coefficient K_sys [Pa/(m³/s)²].
    n_search_points:
        Number of equally-spaced flow points to search for the crossing.
    """
    _validate_fan_curve(curve)
    if system_resistance_pa_per_m3_per_s_sq < 0:
        raise ValueError(
            "system_resistance_pa_per_m3_per_s_sq must be >= 0; "
            f"got {system_resistance_pa_per_m3_per_s_sq}"
        )

    flows = [p.flow_m3_per_s for p in curve]
    q_min, q_max = flows[0], flows[-1]
    K = system_resistance_pa_per_m3_per_s_sq

    def residual(q: float) -> float:
        pt = interpolate_fan_curve(curve, q)
        if pt is None:
            return float("nan")
        return pt.static_pressure_pa - K * q * q

    dq = (q_max - q_min) / n_search_points
    q_prev = q_min
    r_prev = residual(q_prev)

    for i in range(1, n_search_points + 1):
        q = q_min + i * dq
        r = residual(q)
        if r_prev * r <= 0.0:
            # Sign change → linear interpolation of crossing
            t = r_prev / (r_prev - r) if (r_prev - r) != 0 else 0.5
            q_star = q_prev + t * dq
            pt = interpolate_fan_curve(curve, q_star)
            if pt is None:
                return None
            return FanOperatingPoint(
                flow_m3_per_s=q_star,
                static_pressure_pa=pt.static_pressure_pa,
                power_w=pt.power_w,
                efficiency=pt.efficiency,
            )
        q_prev = q
        r_prev = r

    return None  # no intersection found


def fan_mass_flow_kg_per_s(
    flow_m3_per_s: float,
    air_density_kg_per_m3: float,
) -> float:
    """
    Convert volumetric fan flow to mass flow rate.

    ṁ = Q × ρ   [kg/s]

    Parameters
    ----------
    flow_m3_per_s:
        Volumetric flow Q [m³/s].
    air_density_kg_per_m3:
        Air density ρ at the fan inlet [kg/m³].
    """
    if flow_m3_per_s < 0:
        raise ValueError(f"flow_m3_per_s must be >= 0; got {flow_m3_per_s}")
    if air_density_kg_per_m3 <= 0:
        raise ValueError(
            f"air_density_kg_per_m3 must be > 0; got {air_density_kg_per_m3}"
        )
    return flow_m3_per_s * air_density_kg_per_m3

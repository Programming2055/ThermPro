"""
Power-loss calculation models for M3 heat source generation.

These functions compute HOW MUCH heat each engineering entity generates
given its library specification and operating current.

Rules enforced:
  - All inputs and outputs in SI base units (CR-ENG-013).
  - No temperatures computed here (that is M4 scope).
  - Temperature coefficient corrections use a reference temperature of
    20 °C (293.15 K) as the standard reference state.
  - Joint losses are NEVER subsumed into bulk busbar resistivity (CR-ENG-008).
  - K_AC = 1.0 warning is raised when AC correction is potentially significant
    but not applied (CR-ENG-011).
  - No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001).
"""
from __future__ import annotations

import math
import uuid
import warnings
from typing import Optional

from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    LossBreakdown,
    LossCalculationSource,
)
from thermal_core.libraries import (
    BusbarProfileLibraryEntry,
    CableLibraryEntry,
    ConnectionLibraryEntry,
    DeviceLibraryEntry,
    LossConfidence,
    LossCurvePoint,
)

# Reference temperature for DC resistance tables (IEC standard reference)
T_REF_K: float = 293.15  # 20 °C in kelvin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _interpolate_loss_curve(
    curve: tuple[LossCurvePoint, ...],
    current_fraction: float,
) -> float:
    """
    Linear interpolation of power loss from a device loss curve.

    Clamps to the end points if current_fraction is outside the curve range.
    """
    if not curve:
        raise ValueError("Loss curve is empty.")
    sorted_curve = sorted(curve, key=lambda p: p.current_fraction)
    if current_fraction <= sorted_curve[0].current_fraction:
        return sorted_curve[0].power_loss_w
    if current_fraction >= sorted_curve[-1].current_fraction:
        return sorted_curve[-1].power_loss_w
    for i in range(len(sorted_curve) - 1):
        lo = sorted_curve[i]
        hi = sorted_curve[i + 1]
        if lo.current_fraction <= current_fraction <= hi.current_fraction:
            frac = (current_fraction - lo.current_fraction) / (
                hi.current_fraction - lo.current_fraction
            )
            return lo.power_loss_w + frac * (hi.power_loss_w - lo.power_loss_w)
    return sorted_curve[-1].power_loss_w  # unreachable, but satisfies type checker


# ---------------------------------------------------------------------------
# Device heat source
# ---------------------------------------------------------------------------


def device_heat_source(
    *,
    device: DeviceLibraryEntry,
    entity_id: str,
    location: Point3D,
    operating_current_a: float,
    volume_m3: Optional[float] = None,
    surface_area_m2: Optional[float] = None,
) -> HeatSource:
    """
    Compute a HeatSource for a placed protective device.

    Uses the device loss curve via linear interpolation.  If no rated-current
    loss point exists, raises ValueError.

    Args:
        device:              DeviceLibraryEntry from the library.
        entity_id:           UUID of the DevicePlacement.
        location:            Centroid of the device in enclosure coordinates (m).
        operating_current_a: Actual operating current in amperes (SI).
        volume_m3:           Optional bounding volume for M4 (m³).
        surface_area_m2:     Optional exposed surface area for M4 (m²).
    """
    if operating_current_a < 0:
        raise ValueError(
            f"operating_current_a must be >= 0 A; got {operating_current_a}"
        )
    current_fraction = (
        operating_current_a / device.rated_current_a
        if device.rated_current_a > 0
        else 0.0
    )
    power_loss_w = _interpolate_loss_curve(device.power_loss_curve, current_fraction)
    library_ref = f"{device.entry_id}@{device.library_version}"

    return HeatSource(
        source_id=str(uuid.uuid4()),
        entity_type=HeatSourceEntityType.DEVICE,
        entity_id=entity_id,
        power_loss_w=power_loss_w,
        location=location,
        volume_m3=volume_m3,
        surface_area_m2=surface_area_m2,
        confidence=device.loss_confidence,
        calculation_source=LossCalculationSource.MANUFACTURER_CURVE,
        library_ref=library_ref,
        operating_current_a=operating_current_a,
        current_fraction=current_fraction,
        breakdown=LossBreakdown(joule_loss_w=power_loss_w),
    )


# ---------------------------------------------------------------------------
# Busbar heat source
# ---------------------------------------------------------------------------


def busbar_heat_source(
    *,
    profile: BusbarProfileLibraryEntry,
    entity_id: str,
    location: Point3D,
    length_m: float,
    operating_current_a: float,
    k_ac: float = 1.0,
    k_ac_source: str = "NOT_APPLIED",
    volume_m3: Optional[float] = None,
    surface_area_m2: Optional[float] = None,
) -> HeatSource:
    """
    Compute a HeatSource for a placed busbar segment using I²R_DC × K_AC.

    Resistance is evaluated at the 20 °C reference temperature (T_REF_K).
    Temperature correction of resistance is M4 scope (iterative).

    K_AC warning (CR-ENG-011):
        If k_ac == 1.0 and the busbar cross-section exceeds 400 mm²
        (a geometry where skin/proximity effects may be significant at 50 Hz),
        a warning is issued.  The calculation still proceeds — the warning
        is informational for the engineer.

    Args:
        profile:             BusbarProfileLibraryEntry.
        entity_id:           UUID of the BusbarPlacement.
        location:            Centroid of the segment (m).
        length_m:            Length of this segment (m, SI).
        operating_current_a: Actual current in amperes (SI).
        k_ac:                AC correction factor (dimensionless, ≥ 1.0).
        k_ac_source:         KAcSource value string for the audit trail.
        volume_m3:           Optional bounding volume.
        surface_area_m2:     Optional exposed surface area.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be > 0 m; got {length_m}")
    if operating_current_a < 0:
        raise ValueError(f"operating_current_a must be >= 0 A; got {operating_current_a}")
    if k_ac < 1.0:
        raise ValueError(f"k_ac must be >= 1.0; got {k_ac}")

    # CR-ENG-011 warning
    if k_ac == 1.0 and profile.cross_section_area_m2 > 400e-6:
        warnings.warn(
            f"CR-ENG-011: K_AC = 1.0 (DC-only) applied to busbar with "
            f"cross-section {profile.cross_section_area_m2 * 1e6:.0f} mm² "
            f"(entity_id={entity_id}). AC effects may be significant. "
            f"Confirm with engineer.",
            stacklevel=2,
        )

    # From MaterialLibraryEntry: resistivity at T_REF_K
    # We store resistivity in the material, but BusbarProfileLibraryEntry
    # only has a material_ref (UUID). The caller must resolve it.
    # Here we use a simplified approach: the profile carries enough info
    # via its material_ref to be resolved externally. For the loss model,
    # we need resistivity. We accept it as a resolved parameter.
    raise NotImplementedError(
        "busbar_heat_source requires resolved material resistivity. "
        "Use busbar_heat_source_resolved() with the resolved resistivity value."
    )


def busbar_heat_source_resolved(
    *,
    profile: BusbarProfileLibraryEntry,
    material_resistivity_ohm_m: float,
    entity_id: str,
    location: Point3D,
    length_m: float,
    operating_current_a: float,
    k_ac: float = 1.0,
    k_ac_source: str = "NOT_APPLIED",
    volume_m3: Optional[float] = None,
    surface_area_m2: Optional[float] = None,
) -> HeatSource:
    """
    Compute busbar HeatSource with caller-supplied material resistivity.

    material_resistivity_ohm_m:
        Electrical resistivity at T_REF_K (20 °C) in Ω·m (SI).
        Must be obtained from the MaterialLibraryEntry.electrical_resistivity_ohm_m.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be > 0 m; got {length_m}")
    if operating_current_a < 0:
        raise ValueError(f"operating_current_a must be >= 0 A; got {operating_current_a}")
    if k_ac < 1.0:
        raise ValueError(f"k_ac must be >= 1.0; got {k_ac}")
    if material_resistivity_ohm_m <= 0:
        raise ValueError(
            f"material_resistivity_ohm_m must be > 0; got {material_resistivity_ohm_m}"
        )

    # CR-ENG-011 warning
    if k_ac == 1.0 and profile.cross_section_area_m2 > 400e-6:
        warnings.warn(
            f"CR-ENG-011: K_AC = 1.0 (DC-only) applied to busbar with "
            f"cross-section {profile.cross_section_area_m2 * 1e6:.0f} mm² "
            f"(entity_id={entity_id}). AC effects may be significant.",
            stacklevel=2,
        )

    # DC resistance at reference temperature
    r_dc_ohm = material_resistivity_ohm_m * length_m / profile.cross_section_area_m2

    # Apply AC correction (CR-ENG-004)
    r_ac_ohm = r_dc_ohm * k_ac

    # Power loss: P = I² × R_AC  (watts, SI)
    power_loss_w = (operating_current_a ** 2) * r_ac_ohm

    calc_source = (
        LossCalculationSource.AC_RESISTANCE_CALC
        if k_ac > 1.0
        else LossCalculationSource.DC_RESISTANCE_CALC
    )
    library_ref = f"{profile.entry_id}@{profile.library_version}"

    return HeatSource(
        source_id=str(uuid.uuid4()),
        entity_type=HeatSourceEntityType.BUSBAR,
        entity_id=entity_id,
        power_loss_w=power_loss_w,
        location=location,
        volume_m3=volume_m3,
        surface_area_m2=surface_area_m2,
        confidence=LossConfidence.CORRELATED,
        calculation_source=calc_source,
        library_ref=library_ref,
        operating_current_a=operating_current_a,
        current_fraction=(
            operating_current_a / profile.max_continuous_current_a
            if profile.max_continuous_current_a
            else None
        ),
        breakdown=LossBreakdown(joule_loss_w=power_loss_w),
    )


# ---------------------------------------------------------------------------
# Joint (connection) heat source — CR-ENG-008
# ---------------------------------------------------------------------------


def joint_heat_source(
    *,
    connection: ConnectionLibraryEntry,
    entity_id: str,
    location: Point3D,
    operating_current_a: float,
) -> HeatSource:
    """
    Compute a HeatSource for a single busbar joint.

    Joint losses are NEVER subsumed into bulk busbar resistivity (CR-ENG-008).
    Each joint is always a separate HeatSource.

    P_joint = I² × R_joint × age_factor
    """
    if operating_current_a < 0:
        raise ValueError(
            f"operating_current_a must be >= 0 A; got {operating_current_a}"
        )

    effective_resistance = connection.joint_resistance_ohm * connection.age_factor
    power_loss_w = (operating_current_a ** 2) * effective_resistance

    library_ref = f"{connection.entry_id}@{connection.library_version}"
    return HeatSource(
        source_id=str(uuid.uuid4()),
        entity_type=HeatSourceEntityType.JOINT,
        entity_id=entity_id,
        power_loss_w=power_loss_w,
        location=location,
        volume_m3=None,
        surface_area_m2=None,
        confidence=LossConfidence.MANUFACTURER_TYPICAL,
        calculation_source=LossCalculationSource.JOINT_RESISTANCE,
        library_ref=library_ref,
        operating_current_a=operating_current_a,
        current_fraction=None,
        breakdown=LossBreakdown(contact_loss_w=power_loss_w),
    )


# ---------------------------------------------------------------------------
# Cable heat source
# ---------------------------------------------------------------------------


def cable_heat_source(
    *,
    cable: CableLibraryEntry,
    entity_id: str,
    location: Point3D,
    length_m: float,
    operating_current_a: float,
    volume_m3: Optional[float] = None,
    surface_area_m2: Optional[float] = None,
) -> HeatSource:
    """
    Compute a HeatSource for a cable run at reference temperature (20 °C).

    P_cable = I² × R_per_metre(T_ref) × length_m

    Temperature correction of resistance is M4 scope.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be > 0 m; got {length_m}")
    if operating_current_a < 0:
        raise ValueError(
            f"operating_current_a must be >= 0 A; got {operating_current_a}"
        )

    r_total_ohm = cable.resistance_ohm_per_m * length_m
    power_loss_w = (operating_current_a ** 2) * r_total_ohm

    library_ref = f"{cable.entry_id}@{cable.library_version}"
    current_fraction = (
        operating_current_a / cable.rated_current_a if cable.rated_current_a > 0 else None
    )
    return HeatSource(
        source_id=str(uuid.uuid4()),
        entity_type=HeatSourceEntityType.CABLE,
        entity_id=entity_id,
        power_loss_w=power_loss_w,
        location=location,
        volume_m3=volume_m3,
        surface_area_m2=surface_area_m2,
        confidence=LossConfidence.CORRELATED,
        calculation_source=LossCalculationSource.DC_RESISTANCE_CALC,
        library_ref=library_ref,
        operating_current_a=operating_current_a,
        current_fraction=current_fraction,
        breakdown=LossBreakdown(joule_loss_w=power_loss_w),
    )

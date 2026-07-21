"""
Natural-ventilation airflow network for the M4 zonal solver.

For MODE 2 (natural ventilation), buoyancy-driven air movement through
openings is calculated using the pressure-balance method:

  Stack pressure:  ΔP_stack = ρ_amb × g × H × (T_air - T_amb) / T_avg   [Pa]
  Orifice flow:    Q = Cd × A × sqrt(2 × |ΔP| / ρ)                       [m³/s]
  Mass balance:    Σ ṁ_in = Σ ṁ_out  at each compartment

All values in SI base units (CR-ENG-013).
Temperatures in kelvin (CR-ENG-003).

Equation reference: THERM-EQN-001 §6.5 (Airflow Network)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from thermal_core.materials.air_properties import air_at

_G = 9.80665    # gravitational acceleration [m/s²]


# ---------------------------------------------------------------------------
# Stack-effect pressure
# ---------------------------------------------------------------------------


def stack_pressure_pa(
    t_air_k: float,
    t_ambient_k: float,
    height_difference_m: float,
    air_density_kg_per_m3: Optional[float] = None,
    pressure_pa: float = 101_325.0,
) -> float:
    """
    Buoyancy stack pressure driving natural ventilation [Pa].

    ΔP_stack = ρ_amb × g × H × (T_air - T_amb) / T_avg

    Derived from ideal-gas density difference:
        Δρ = ρ_amb - ρ_air ≈ ρ_amb × (T_air - T_amb) / T_avg

    Positive ΔP_stack means warm inside air rises (upward flow through top opening).

    Parameters
    ----------
    t_air_k:
        Mean compartment air temperature [K] (CR-ENG-003).
    t_ambient_k:
        External ambient temperature [K] (CR-ENG-003).
    height_difference_m:
        Vertical distance between inlet and outlet centroids H [m].
    air_density_kg_per_m3:
        Ambient air density [kg/m³]. If None, computed from ideal gas at T_amb.
    pressure_pa:
        Ambient pressure [Pa]; used only if air_density is None.

    Returns
    -------
    float
        Stack pressure ΔP_stack [Pa].  Negative → reverse flow.
    """
    if t_air_k <= 0:
        raise ValueError(f"t_air_k must be > 0 K; got {t_air_k}")
    if t_ambient_k <= 0:
        raise ValueError(f"t_ambient_k must be > 0 K; got {t_ambient_k}")
    if height_difference_m <= 0:
        raise ValueError(f"height_difference_m must be > 0; got {height_difference_m}")

    if air_density_kg_per_m3 is None:
        air_density_kg_per_m3 = air_at(t_ambient_k, pressure_pa).density_kg_per_m3

    t_avg = 0.5 * (t_air_k + t_ambient_k)
    return air_density_kg_per_m3 * _G * height_difference_m * (t_air_k - t_ambient_k) / t_avg


# ---------------------------------------------------------------------------
# Orifice flow
# ---------------------------------------------------------------------------


def orifice_flow_m3_per_s(
    delta_pressure_pa: float,
    discharge_coefficient: float,
    free_area_m2: float,
    air_density_kg_per_m3: float,
) -> float:
    """
    Volumetric airflow through a ventilation opening (orifice model) [m³/s].

    Q = Cd × A × sqrt(2 × |ΔP| / ρ)

    A positive delta_pressure_pa means pressure drives flow through the opening.

    Parameters
    ----------
    delta_pressure_pa:
        Pressure differential across the opening [Pa].
    discharge_coefficient:
        Orifice discharge coefficient Cd ∈ (0, 1].
    free_area_m2:
        Net free opening area A [m²].
    air_density_kg_per_m3:
        Air density at the opening ρ [kg/m³].

    Returns
    -------
    float
        Magnitude of volumetric flow Q [m³/s] (always ≥ 0).
    """
    if not (0.0 < discharge_coefficient <= 1.0):
        raise ValueError(
            f"discharge_coefficient must be in (0, 1]; got {discharge_coefficient}"
        )
    if free_area_m2 <= 0:
        raise ValueError(f"free_area_m2 must be > 0; got {free_area_m2}")
    if air_density_kg_per_m3 <= 0:
        raise ValueError(
            f"air_density_kg_per_m3 must be > 0; got {air_density_kg_per_m3}"
        )

    abs_dp = abs(delta_pressure_pa)
    if abs_dp == 0.0:
        return 0.0
    return discharge_coefficient * free_area_m2 * math.sqrt(2.0 * abs_dp / air_density_kg_per_m3)


# ---------------------------------------------------------------------------
# Simple two-opening natural ventilation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NaturalVentilationResult:
    """
    Result of a single-zone natural ventilation calculation.

    Used for MODE 2 single-compartment analysis.
    """
    stack_pressure_pa: float
    volumetric_flow_m3_per_s: float
    mass_flow_kg_per_s: float
    air_changes_per_hour: float   # ACH = Q × 3600 / V_compartment
    is_buoyancy_driven: bool


def natural_ventilation_flow(
    t_air_k: float,
    t_ambient_k: float,
    inlet_height_m: float,
    outlet_height_m: float,
    inlet_area_m2: float,
    outlet_area_m2: float,
    inlet_cd: float,
    outlet_cd: float,
    compartment_volume_m3: float,
    pressure_pa: float = 101_325.0,
) -> NaturalVentilationResult:
    """
    Single-zone natural ventilation through two openings (inlet and outlet).

    Uses the combined inlet/outlet effective area:
        1/A_eff² = 1/(Cd_in × A_in)² + 1/(Cd_out × A_out)²

    The pressure difference driving flow is the stack pressure between the
    inlet and outlet centroid heights.

    Parameters
    ----------
    t_air_k:
        Compartment air temperature [K] (CR-ENG-003).
    t_ambient_k:
        Ambient temperature [K] (CR-ENG-003).
    inlet_height_m / outlet_height_m:
        Height of inlet / outlet centroids above enclosure base [m].
    inlet_area_m2 / outlet_area_m2:
        Free areas of inlet / outlet openings [m²].
    inlet_cd / outlet_cd:
        Discharge coefficients of inlet / outlet openings.
    compartment_volume_m3:
        Internal compartment volume V [m³] for ACH calculation.
    pressure_pa:
        Ambient pressure [Pa].

    Returns
    -------
    NaturalVentilationResult
    """
    height_diff = outlet_height_m - inlet_height_m
    if height_diff <= 0:
        height_diff = max(abs(height_diff), 0.01)  # minimum 1 cm to avoid /0

    dp_stack = stack_pressure_pa(t_air_k, t_ambient_k, height_diff, pressure_pa=pressure_pa)

    props_amb = air_at(t_ambient_k, pressure_pa)
    rho = props_amb.density_kg_per_m3

    # Effective area: series combination of inlet and outlet
    ea_in = inlet_cd * inlet_area_m2
    ea_out = outlet_cd * outlet_area_m2
    a_eff_sq = 1.0 / (1.0 / (ea_in ** 2) + 1.0 / (ea_out ** 2))
    a_eff = math.sqrt(a_eff_sq)

    abs_dp = abs(dp_stack)
    if abs_dp < 1e-6:
        q = 0.0
    else:
        q = a_eff * math.sqrt(2.0 * abs_dp / rho)

    mdot = q * rho
    ach = (q * 3600.0) / compartment_volume_m3 if compartment_volume_m3 > 0 else 0.0

    return NaturalVentilationResult(
        stack_pressure_pa=dp_stack,
        volumetric_flow_m3_per_s=q,
        mass_flow_kg_per_s=mdot,
        air_changes_per_hour=ach,
        is_buoyancy_driven=abs_dp > 1e-6,
    )

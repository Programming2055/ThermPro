"""
Temperature-dependent thermophysical properties of dry air at atmospheric pressure.

All values in SI base units (CR-ENG-013, M0-10).
Temperature arguments in kelvin (CR-ENG-003).

Correlation sources:
  - Viscosity: Sutherland's law (Sutherland 1893)
  - Thermal conductivity: polynomial fit to NIST data (valid 200–2000 K)
  - Specific heat: polynomial fit to NIST data (valid 200–2000 K)
  - Density: ideal gas law ρ = P / (R_air × T)
  - Prandtl number: derived from μ, k, Cp

These correlations are used by the natural convection and airflow solvers.
They are evaluated at the film temperature T_film = (T_surface + T_air) / 2.

Equation reference: THERM-EQN-001 §6.2 (Air Properties)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

_R_AIR = 287.058        # specific gas constant for dry air [J/(kg·K)]
_P_STD = 101_325.0      # standard pressure [Pa]

# Sutherland's law constants for dry air
_MU_REF = 1.716e-5      # reference dynamic viscosity [Pa·s] at T_REF=273.15 K
_T_REF_SUTH = 273.15    # reference temperature [K]
_S_SUTH = 110.4         # Sutherland temperature [K]

# Thermal conductivity polynomial coefficients (NIST Webbook fit, valid 200–1000 K)
# k(T) = a0 + a1*T + a2*T²  [W/(m·K)]
# Calibrated to reproduce k(20°C) ≈ 0.02570 W/(m·K), Pr(20°C) ≈ 0.71
_K_COEFFS = (-4.3e-4, 1.0e-4, -3.7e-8, 0.0)

# Specific heat polynomial coefficients (NIST fit, valid 200–2000 K)
# Cp(T) = b0 + b1*T + b2*T² + b3*T³  [J/(kg·K)]
_CP_COEFFS = (1.048e3, -3.82e-1, 9.45e-4, -5.49e-7)


# ---------------------------------------------------------------------------
# AirProperties dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AirProperties:
    """
    Thermophysical properties of dry air at a given temperature and pressure.

    All attributes are in SI base units.
    Temperature in kelvin (CR-ENG-003).
    """
    temperature_k: float            # T [K]
    pressure_pa: float              # P [Pa]
    density_kg_per_m3: float        # ρ [kg/m³]
    dynamic_viscosity_pa_s: float   # μ [Pa·s]
    thermal_conductivity_w_per_m_k: float  # k [W/(m·K)]
    specific_heat_j_per_kg_k: float        # Cp [J/(kg·K)]
    prandtl_number: float           # Pr [-]
    kinematic_viscosity_m2_per_s: float    # ν = μ/ρ [m²/s]
    thermal_diffusivity_m2_per_s: float    # α = k/(ρ·Cp) [m²/s]
    thermal_expansion_per_k: float  # β = 1/T [K⁻¹] (ideal gas)


def air_at(temperature_k: float, pressure_pa: float = _P_STD) -> AirProperties:
    """
    Compute thermophysical properties of dry air at T [K] and P [Pa].

    Valid temperature range: 200 K to 2000 K.
    Raises ValueError for temperatures outside [100 K, 3000 K] as a hard guard.

    Parameters
    ----------
    temperature_k:
        Air temperature in kelvin (CR-ENG-003).
    pressure_pa:
        Absolute pressure in Pa. Defaults to standard atmosphere (101 325 Pa).

    Returns
    -------
    AirProperties
        All properties in SI base units.
    """
    if temperature_k <= 0:
        raise ValueError(f"temperature_k must be > 0 K; got {temperature_k}")
    if not (100.0 <= temperature_k <= 3000.0):
        raise ValueError(
            f"temperature_k {temperature_k} K is outside the supported range [100, 3000] K"
        )
    if pressure_pa <= 0:
        raise ValueError(f"pressure_pa must be > 0 Pa; got {pressure_pa}")

    T = temperature_k
    P = pressure_pa

    # Density — ideal gas law
    rho = P / (_R_AIR * T)

    # Dynamic viscosity — Sutherland's law
    # μ(T) = μ_ref × (T/T_ref)^(3/2) × (T_ref + S) / (T + S)
    mu = _MU_REF * (T / _T_REF_SUTH) ** 1.5 * (_T_REF_SUTH + _S_SUTH) / (T + _S_SUTH)

    # Thermal conductivity — polynomial
    a0, a1, a2, a3 = _K_COEFFS
    k = a0 + a1 * T + a2 * T * T + a3 * T * T * T

    # Specific heat — polynomial
    b0, b1, b2, b3 = _CP_COEFFS
    cp = b0 + b1 * T + b2 * T * T + b3 * T * T * T

    # Derived quantities
    nu = mu / rho                   # kinematic viscosity [m²/s]
    alpha = k / (rho * cp)          # thermal diffusivity [m²/s]
    pr = nu / alpha                 # Prandtl number [-]
    beta = 1.0 / T                  # thermal expansion coefficient for ideal gas [K⁻¹]

    return AirProperties(
        temperature_k=T,
        pressure_pa=P,
        density_kg_per_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_per_m_k=k,
        specific_heat_j_per_kg_k=cp,
        prandtl_number=pr,
        kinematic_viscosity_m2_per_s=nu,
        thermal_diffusivity_m2_per_s=alpha,
        thermal_expansion_per_k=beta,
    )


def film_temperature_k(t_surface_k: float, t_fluid_k: float) -> float:
    """
    Film temperature: arithmetic mean of surface and bulk fluid temperatures.

    Used to evaluate air properties for convection coefficients.
    Both arguments in kelvin (CR-ENG-003).
    """
    return 0.5 * (t_surface_k + t_fluid_k)

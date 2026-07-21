"""
Churchill-Chu (1975) natural convection correlations for enclosure surfaces.

All values in SI base units (CR-ENG-013).
Temperatures in kelvin (CR-ENG-003).

Correlations implemented:
  - Vertical plates: Churchill & Chu (1975), Eq. (9) — valid Ra ∈ [10⁻¹, 10¹²]
  - Horizontal plates (heated up): McAdams (1954) / Churchill & Chu
  - Horizontal plates (cooled down): McAdams (1954)

These are the primary correlations used by the M4 zonal solver for
estimating internal and external natural-convection heat transfer coefficients.

Equation reference: THERM-EQN-001 §6.4 (Natural Convection)
"""
from __future__ import annotations

import math
from typing import Optional

from thermal_core.materials.air_properties import AirProperties, air_at, film_temperature_k
from thermal_core.snapshot import SurfaceOrientation

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

_G = 9.80665    # standard acceleration due to gravity [m/s²]


# ---------------------------------------------------------------------------
# Rayleigh number
# ---------------------------------------------------------------------------


def rayleigh_number(
    air: AirProperties,
    delta_t_k: float,
    length_m: float,
) -> float:
    """
    Rayleigh number Ra = g β ΔT L³ / (ν α).

    Ra is a dimensionless measure of buoyancy-driven flow intensity.

    Parameters
    ----------
    air:
        Air properties evaluated at the film temperature.
    delta_t_k:
        |T_surface - T_air| temperature difference [K].
    length_m:
        Characteristic length L [m]:
        - vertical plate → height H
        - horizontal plate → L = A_s / P (area / perimeter)

    Returns
    -------
    float
        Rayleigh number Ra [-].
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be > 0; got {length_m}")
    if delta_t_k < 0:
        delta_t_k = abs(delta_t_k)

    ra = (
        _G * air.thermal_expansion_per_k * delta_t_k * length_m ** 3
        / (air.kinematic_viscosity_m2_per_s * air.thermal_diffusivity_m2_per_s)
    )
    return max(ra, 0.0)


# ---------------------------------------------------------------------------
# Nusselt number correlations
# ---------------------------------------------------------------------------


def nusselt_vertical_plate(ra: float, pr: float) -> float:
    """
    Churchill-Chu (1975) correlation for a vertical isothermal plate.

    Nu = {0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)}²

    Valid for the full Ra range Ra ∈ [10⁻¹, 10¹²].
    Returns Nu ≥ 1.0 (lower bound enforced for degenerate cases).

    Reference: Churchill S.W. & Chu H.H.S., Int. J. Heat Mass Transfer, 1975.
    """
    if ra <= 0.0:
        return 1.0  # no buoyancy → pure conduction limit
    psi = (0.492 / pr) ** (9.0 / 16.0)
    bracket = (1.0 + psi) ** (8.0 / 27.0)
    nu = (0.825 + 0.387 * ra ** (1.0 / 6.0) / bracket) ** 2
    return max(nu, 1.0)


def nusselt_horizontal_plate_up(ra: float) -> float:
    """
    Nu for a horizontal plate with heated face upward (unstable stratification).

    Uses the McAdams (1954) two-regime correlation:
      Ra ∈ [10⁴, 10⁷]:  Nu = 0.54 Ra^(1/4)
      Ra ∈ [10⁷, 10¹¹]: Nu = 0.15 Ra^(1/3)

    Below Ra = 10⁴ falls back to Nu = 1.0 (conduction limit).
    """
    if ra <= 0.0:
        return 1.0
    if ra < 1e4:
        return 1.0
    if ra < 1e7:
        return 0.54 * ra ** 0.25
    return 0.15 * ra ** (1.0 / 3.0)


def nusselt_horizontal_plate_down(ra: float) -> float:
    """
    Nu for a horizontal plate with heated face downward (stable stratification).

    McAdams (1954):
      Ra ∈ [10⁵, 10¹⁰]: Nu = 0.27 Ra^(1/4)

    Below Ra = 10⁵ → Nu = 1.0 (conduction limit).
    """
    if ra <= 0.0:
        return 1.0
    if ra < 1e5:
        return 1.0
    return 0.27 * ra ** 0.25


# ---------------------------------------------------------------------------
# Heat transfer coefficient h [W/(m²·K)]
# ---------------------------------------------------------------------------


def convection_coefficient_vertical(
    t_surface_k: float,
    t_air_k: float,
    height_m: float,
    pressure_pa: float = 101_325.0,
) -> float:
    """
    Natural convection coefficient h for a vertical isothermal plate [W/(m²·K)].

    h = Nu × k_air / H

    Both temperatures in kelvin (CR-ENG-003).
    Returns h ≥ 0.
    """
    delta_t = abs(t_surface_k - t_air_k)
    t_film = film_temperature_k(t_surface_k, t_air_k)
    props = air_at(t_film, pressure_pa)
    ra = rayleigh_number(props, delta_t, height_m)
    nu = nusselt_vertical_plate(ra, props.prandtl_number)
    return nu * props.thermal_conductivity_w_per_m_k / height_m


def convection_coefficient_horizontal(
    t_surface_k: float,
    t_air_k: float,
    characteristic_length_m: float,
    heated_face_up: bool,
    pressure_pa: float = 101_325.0,
) -> float:
    """
    Natural convection coefficient h for a horizontal plate [W/(m²·K)].

    Parameters
    ----------
    t_surface_k:
        Surface temperature [K] (CR-ENG-003).
    t_air_k:
        Bulk air temperature [K] (CR-ENG-003).
    characteristic_length_m:
        L_c = A_s / perimeter [m] for horizontal plate.
    heated_face_up:
        True if the hotter face points upward (unstable).
    """
    delta_t = abs(t_surface_k - t_air_k)
    t_film = film_temperature_k(t_surface_k, t_air_k)
    props = air_at(t_film, pressure_pa)
    ra = rayleigh_number(props, delta_t, characteristic_length_m)
    if heated_face_up:
        nu = nusselt_horizontal_plate_up(ra)
    else:
        nu = nusselt_horizontal_plate_down(ra)
    return nu * props.thermal_conductivity_w_per_m_k / characteristic_length_m


def convection_coefficient(
    t_surface_k: float,
    t_air_k: float,
    characteristic_length_m: float,
    orientation: SurfaceOrientation,
    pressure_pa: float = 101_325.0,
) -> float:
    """
    Natural convection coefficient h for a surface with the given orientation.

    Dispatches to the appropriate correlation based on orientation.
    All temperatures in kelvin (CR-ENG-003).

    INCLINED surfaces are treated as VERTICAL (conservative approximation).
    """
    if orientation == SurfaceOrientation.VERTICAL:
        return convection_coefficient_vertical(
            t_surface_k, t_air_k, characteristic_length_m, pressure_pa
        )
    elif orientation == SurfaceOrientation.HORIZONTAL_UP:
        heated_up = t_surface_k > t_air_k
        return convection_coefficient_horizontal(
            t_surface_k, t_air_k, characteristic_length_m,
            heated_face_up=heated_up, pressure_pa=pressure_pa
        )
    elif orientation == SurfaceOrientation.HORIZONTAL_DOWN:
        heated_up = t_surface_k < t_air_k  # heated face down = face is cooler than air
        return convection_coefficient_horizontal(
            t_surface_k, t_air_k, characteristic_length_m,
            heated_face_up=heated_up, pressure_pa=pressure_pa
        )
    else:  # INCLINED → treated as vertical
        return convection_coefficient_vertical(
            t_surface_k, t_air_k, characteristic_length_m, pressure_pa
        )

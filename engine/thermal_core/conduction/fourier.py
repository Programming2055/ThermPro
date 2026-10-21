"""
Fourier conduction through planar walls and composite assemblies.

Governing equation (planar wall, steady state):
    Q = k × A / L × ΔT  [W]

Thermal resistance (K/W):
    R = L / (k × A)

All values in SI base units (CR-ENG-013).
Temperature differences in kelvin (equivalent to °C differences, but
all absolute temperatures must be in K — CR-ENG-003).

Equation reference: THERM-EQN-001 §6.3 (Conduction)
"""
from __future__ import annotations


def wall_resistance_k_per_w(
    thickness_m: float,
    thermal_conductivity_w_per_m_k: float,
    area_m2: float,
) -> float:
    """
    Thermal resistance of a uniform planar wall [K/W].

    R = L / (k × A)

    Parameters
    ----------
    thickness_m:
        Wall thickness L [m].
    thermal_conductivity_w_per_m_k:
        Material thermal conductivity k [W/(m·K)].
    area_m2:
        Wall cross-sectional area A [m²].

    Returns
    -------
    float
        Thermal resistance [K/W].
    """
    if thickness_m < 0:
        raise ValueError(f"thickness_m must be >= 0; got {thickness_m}")
    if thermal_conductivity_w_per_m_k <= 0:
        raise ValueError(
            f"thermal_conductivity_w_per_m_k must be > 0; got {thermal_conductivity_w_per_m_k}"
        )
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be > 0; got {area_m2}")
    if thickness_m == 0.0:
        return 0.0
    return thickness_m / (thermal_conductivity_w_per_m_k * area_m2)


def wall_conductance_w_per_k(
    thickness_m: float,
    thermal_conductivity_w_per_m_k: float,
    area_m2: float,
) -> float:
    """
    Thermal conductance of a uniform planar wall [W/K].

    UA = k × A / L

    A wall of zero thickness has infinite conductance; returns a very large
    number (1e12 W/K) to avoid division by zero in the conductance matrix.
    """
    if thickness_m == 0.0:
        return 1e12
    return 1.0 / wall_resistance_k_per_w(thickness_m, thermal_conductivity_w_per_m_k, area_m2)


def composite_wall_resistance_k_per_w(
    layers: list[tuple[float, float]],
    area_m2: float,
) -> float:
    """
    Total thermal resistance of a composite wall (series layers) [K/W].

    R_total = Σ L_i / (k_i × A)

    Parameters
    ----------
    layers:
        Sequence of (thickness_m, thermal_conductivity_w_per_m_k) tuples,
        one per layer from interior to exterior.
    area_m2:
        Common cross-sectional area shared by all layers [m²].

    Returns
    -------
    float
        Total thermal resistance [K/W].
    """
    if not layers:
        raise ValueError("composite_wall_resistance_k_per_w: layers must not be empty")
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be > 0; got {area_m2}")
    return sum(
        wall_resistance_k_per_w(L, k, area_m2)
        for L, k in layers
    )


def contact_resistance_k_per_w(
    contact_resistance_m2_k_per_w: float,
    area_m2: float,
) -> float:
    """
    Thermal resistance of an interface contact layer [K/W].

    R_contact = r'' / A   where r'' is contact resistance [m²·K/W]

    Parameters
    ----------
    contact_resistance_m2_k_per_w:
        Specific interface thermal resistance r'' [m²·K/W].
    area_m2:
        Contact area A [m²].
    """
    if contact_resistance_m2_k_per_w < 0:
        raise ValueError(
            f"contact_resistance_m2_k_per_w must be >= 0; got {contact_resistance_m2_k_per_w}"
        )
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be > 0; got {area_m2}")
    return contact_resistance_m2_k_per_w / area_m2

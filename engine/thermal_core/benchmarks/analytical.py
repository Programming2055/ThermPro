"""
Analytical benchmark solutions for M4 physics verification.

These are exact (closed-form) solutions against which the solver modules
are validated.  They serve as BM-001 through BM-004 in THERM-VAL-001.

All values in SI base units (CR-ENG-013).
Temperatures in kelvin (CR-ENG-003).

BM-001: Steady-state conduction through a plane wall
BM-002: Newton's law of cooling (convection only)
BM-003: Radiation between two parallel plates (exact)
BM-004: Combined convection + radiation (single surface to ambient)

These benchmarks have known analytical solutions and must match
solver results to within the tolerances specified in THERM-VAL-001.

Equation reference: THERM-EQN-001 §7 (Validation Benchmarks)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from thermal_core.radiation.gray_body import STEFAN_BOLTZMANN


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Result of an analytical benchmark comparison.

    All temperatures in kelvin (CR-ENG-003).
    """
    benchmark_id: str
    description: str
    analytical_value: float    # exact theoretical value
    solver_value: float        # value from the numerical solver
    tolerance: float           # acceptance tolerance (absolute)
    units: str
    passed: bool               # |analytical - solver| <= tolerance

    @property
    def absolute_error(self) -> float:
        return abs(self.analytical_value - self.solver_value)

    @property
    def relative_error_percent(self) -> float:
        if self.analytical_value == 0:
            return 0.0
        return 100.0 * self.absolute_error / abs(self.analytical_value)


def conduction_through_plate(
    q_w: float,
    thickness_m: float,
    thermal_conductivity_w_per_m_k: float,
    area_m2: float,
    t_hot_k: float,
) -> float:
    """
    BM-001: Temperature on the cold face of a plane wall with given heat flux.

    Fourier's law (1D steady conduction):
        T_cold = T_hot - Q × L / (k × A)

    Parameters
    ----------
    q_w:
        Heat flow through the wall [W].
    thickness_m:
        Wall thickness L [m].
    thermal_conductivity_w_per_m_k:
        Thermal conductivity k [W/(m·K)].
    area_m2:
        Wall cross-sectional area A [m²].
    t_hot_k:
        Hot-face temperature T_hot [K] (CR-ENG-003).

    Returns
    -------
    float
        Cold-face temperature T_cold [K].
    """
    return t_hot_k - q_w * thickness_m / (thermal_conductivity_w_per_m_k * area_m2)


def convection_cooling(
    q_w: float,
    h_w_per_m2_k: float,
    area_m2: float,
    t_fluid_k: float,
) -> float:
    """
    BM-002: Surface temperature from Newton's law of cooling.

    Q = h × A × (T_s - T_fluid)
    T_s = T_fluid + Q / (h × A)

    Parameters
    ----------
    q_w:
        Total convective heat loss [W].
    h_w_per_m2_k:
        Convection heat transfer coefficient h [W/(m²·K)].
    area_m2:
        Surface area A [m²].
    t_fluid_k:
        Fluid temperature T_fluid [K] (CR-ENG-003).

    Returns
    -------
    float
        Surface temperature T_s [K].
    """
    return t_fluid_k + q_w / (h_w_per_m2_k * area_m2)


def radiation_exchange(
    t_surface_k: float,
    t_surroundings_k: float,
    emissivity: float,
    area_m2: float,
) -> float:
    """
    BM-003: Exact radiation heat flux from a gray surface.

    Q_rad = ε × σ × A × (T_s⁴ - T_surr⁴)

    CR-ENG-003: temperatures must be in kelvin.

    Parameters
    ----------
    t_surface_k:
        Surface temperature T_s [K].
    t_surroundings_k:
        Surrounding temperature T_surr [K].
    emissivity:
        Gray body emissivity ε ∈ [0, 1].
    area_m2:
        Radiating surface area A [m²].

    Returns
    -------
    float
        Net outgoing radiation power [W].
    """
    from thermal_core.radiation.gray_body import gray_body_heat_flux
    return gray_body_heat_flux(t_surface_k, t_surroundings_k, emissivity) * area_m2


def combined_heat_loss(
    q_w: float,
    h_conv_w_per_m2_k: float,
    emissivity: float,
    area_m2: float,
    t_ambient_k: float,
    tol_k: float = 1e-6,
    max_iter: int = 200,
) -> float:
    """
    BM-004: Surface temperature from combined convection + radiation to ambient.

    Solve iteratively:
        Q = (h_conv + h_rad(T_s)) × A × (T_s - T_amb)

    where h_rad = ε σ (T_s + T_amb)(T_s² + T_amb²) is linearised at each step.

    All temperatures in kelvin (CR-ENG-003).

    Returns
    -------
    float
        Surface temperature T_s [K].
    """
    if t_ambient_k <= 0:
        raise ValueError("t_ambient_k must be > 0 K (CR-ENG-003)")

    # Initial guess
    T_s = t_ambient_k + q_w / ((h_conv_w_per_m2_k + 5.0) * area_m2)

    for _ in range(max_iter):
        h_rad = (
            emissivity
            * STEFAN_BOLTZMANN
            * (T_s + t_ambient_k)
            * (T_s ** 2 + t_ambient_k ** 2)
        )
        h_total = h_conv_w_per_m2_k + h_rad
        T_s_new = t_ambient_k + q_w / (h_total * area_m2)
        if abs(T_s_new - T_s) < tol_k:
            return T_s_new
        T_s = T_s_new

    return T_s  # best estimate even if not converged

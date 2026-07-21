"""
Gray-body radiation heat transfer for enclosure surfaces.

CR-ENG-003: ALL radiation calculations use absolute temperature in kelvin.
             Using °C here is a code defect — unit test UT-UNITS-003 and
             UT-UNITS-004 enforce this constraint.

Governing equations:
  q = ε σ (T_s⁴ - T_surr⁴)           [W/m²]  — gray body total emissive power
  h_rad = ε σ (T_s + T_surr)(T_s² + T_surr²)   [W/(m²·K)] — linearised coefficient

Linearisation is exact (not an approximation) and permits the radiation term
to enter the linear conductance matrix at each iteration:
  Q_rad = h_rad × A × (T_s - T_surr)   [W]

Equation reference: THERM-EQN-001 §6.6 (Radiation)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Physical constant — CODATA 2018 exact value
# ---------------------------------------------------------------------------

STEFAN_BOLTZMANN: float = 5.670374419e-8
"""Stefan-Boltzmann constant σ [W/(m²·K⁴)]. CODATA 2018 exact value."""


# ---------------------------------------------------------------------------
# Gray body radiation functions
# ---------------------------------------------------------------------------


def gray_body_heat_flux(
    t_surface_k: float,
    t_surroundings_k: float,
    emissivity: float,
) -> float:
    """
    Net radiation heat flux from a gray surface to its surroundings [W/m²].

    q = ε σ (T_s⁴ - T_surr⁴)

    A positive value means the surface loses heat to surroundings.
    All temperatures in kelvin (CR-ENG-003).

    Parameters
    ----------
    t_surface_k:
        Surface temperature T_s [K].
    t_surroundings_k:
        Effective radiation enclosure/sky temperature T_surr [K].
    emissivity:
        Gray body total hemispherical emissivity ε ∈ [0, 1].

    Returns
    -------
    float
        Net outgoing radiation heat flux [W/m²].
    """
    _validate_temperatures(t_surface_k, t_surroundings_k)
    _validate_emissivity(emissivity)
    return emissivity * STEFAN_BOLTZMANN * (t_surface_k ** 4 - t_surroundings_k ** 4)


def linearised_radiation_coefficient(
    t_surface_k: float,
    t_surroundings_k: float,
    emissivity: float,
) -> float:
    """
    Linearised radiation heat transfer coefficient h_rad [W/(m²·K)].

    Derived by factoring (T_s⁴ - T_surr⁴) = (T_s - T_surr)(T_s + T_surr)(T_s² + T_surr²):

        h_rad = ε σ (T_s + T_surr)(T_s² + T_surr²)

    This allows radiation to be handled as a linear conductance term in the
    energy-balance matrix at each Newton-linearisation iteration.

    All temperatures in kelvin (CR-ENG-003).
    """
    _validate_temperatures(t_surface_k, t_surroundings_k)
    _validate_emissivity(emissivity)
    return (
        emissivity
        * STEFAN_BOLTZMANN
        * (t_surface_k + t_surroundings_k)
        * (t_surface_k ** 2 + t_surroundings_k ** 2)
    )


def radiation_conductance_w_per_k(
    t_surface_k: float,
    t_surroundings_k: float,
    emissivity: float,
    area_m2: float,
) -> float:
    """
    Radiation thermal conductance G_rad = h_rad × A [W/K].

    Used to populate the thermal conductance matrix in the zonal solver.

    Parameters
    ----------
    t_surface_k:
        Surface temperature [K] (CR-ENG-003).
    t_surroundings_k:
        Surrounding temperature [K] (CR-ENG-003).
    emissivity:
        Gray body emissivity ε ∈ [0, 1].
    area_m2:
        Radiating surface area A [m²].

    Returns
    -------
    float
        Radiation conductance [W/K].
    """
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be > 0; got {area_m2}")
    h_rad = linearised_radiation_coefficient(t_surface_k, t_surroundings_k, emissivity)
    return h_rad * area_m2


def effective_emissivity_two_surfaces(
    emissivity_1: float,
    emissivity_2: float,
) -> float:
    """
    Effective emissivity for radiation exchange between two infinite parallel plates.

    1/ε_eff = 1/ε₁ + 1/ε₂ - 1

    Used when both surfaces have non-unity emissivity (enclosure interior walls).
    """
    _validate_emissivity(emissivity_1)
    _validate_emissivity(emissivity_2)
    if emissivity_1 == 0.0 or emissivity_2 == 0.0:
        return 0.0
    return 1.0 / (1.0 / emissivity_1 + 1.0 / emissivity_2 - 1.0)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


_T_RAD_MIN_K = 100.0  # below this, the caller almost certainly passed °C instead of K

def _validate_temperatures(t_surface_k: float, t_surroundings_k: float) -> None:
    if t_surface_k < _T_RAD_MIN_K:
        raise ValueError(
            f"t_surface_k must be >= {_T_RAD_MIN_K} K (CR-ENG-003 — use kelvin, not °C); "
            f"got {t_surface_k}. Did you pass a Celsius value?"
        )
    if t_surroundings_k < _T_RAD_MIN_K:
        raise ValueError(
            f"t_surroundings_k must be >= {_T_RAD_MIN_K} K (CR-ENG-003 — use kelvin, not °C); "
            f"got {t_surroundings_k}. Did you pass a Celsius value?"
        )


def _validate_emissivity(emissivity: float) -> None:
    if not (0.0 <= emissivity <= 1.0):
        raise ValueError(f"emissivity must be in [0, 1]; got {emissivity}")

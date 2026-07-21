"""
IEC TR 60890 empirical method benchmark framework.

CR-ENG-002: The IEC TR 60890 coefficient tables are NEVER shipped in the
             repository.  Administrators import the licensed dataset via
             the admin upload endpoint.

This module provides the calculation framework (equations and structure)
WITHOUT the licensed coefficient values.  The coefficients are injected
at runtime from the database-backed library.

IEC TR 60890 Method (MODE 1):
  ΔT_e = b × P_total^c × (A_eff / A_ref)^d

where:
  ΔT_e     = estimated mean temperature rise above ambient [K]
  P_total  = total power loss [W]
  A_eff    = effective ventilation area [m²]
  b, c, d  = empirically determined coefficients (LICENSED — not in repo)
  A_ref    = reference area [m²] (LICENSED)

This module implements:
  1. The formula structure (with placeholder coefficient injection)
  2. Effective area calculation from geometry
  3. Applicability check (CR-ENG-006: MODE 1 disabled for forced ventilation)

Equation reference: THERM-EQN-001 §8 (IEC TR 60890 Method)
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# IEC TR 60890 applicability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC60890Applicability:
    """
    Applicability check result for IEC TR 60890 empirical method.

    CR-ENG-006: forced ventilation → MODE_1 must not be used.
    """
    is_applicable: bool
    reasons: tuple[str, ...]   # non-empty if not applicable


def check_iec60890_applicability(
    has_forced_ventilation: bool,
    has_busbars_with_unknown_losses: bool,
    form_type: Optional[str] = None,
) -> IEC60890Applicability:
    """
    Check whether IEC TR 60890 (MODE 1) applies to the given configuration.

    Returns an applicability result.  A non-applicable result means MODE_1
    must not be used (CR-ENG-006).
    """
    reasons: list[str] = []

    if has_forced_ventilation:
        reasons.append(
            "CR-ENG-006: IEC TR 60890 MODE 1 does not apply when forced ventilation "
            "is active. Use MODE 3 (forced ventilation airflow network) instead."
        )

    if has_busbars_with_unknown_losses:
        reasons.append(
            "IEC TR 60890 requires known busbar power losses. "
            "Unknown busbar losses must be estimated before applying MODE 1."
        )

    if form_type and form_type.upper() in ("4B",):
        reasons.append(
            f"IEC TR 60890 applicability for Form {form_type} requires "
            "project-specific assessment. Consult the standard."
        )

    return IEC60890Applicability(
        is_applicable=len(reasons) == 0,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# Effective ventilation area
# ---------------------------------------------------------------------------


def effective_ventilation_area_m2(
    inlet_area_m2: float,
    outlet_area_m2: float,
) -> float:
    """
    Effective ventilation area A_eff for IEC TR 60890 formula.

    A_eff = sqrt(A_inlet × A_outlet)   (geometric mean of inlet and outlet areas)

    Both areas in m². Returns 0 if either is zero (no ventilation path).
    """
    if inlet_area_m2 < 0 or outlet_area_m2 < 0:
        raise ValueError("ventilation areas must be >= 0")
    if inlet_area_m2 == 0 or outlet_area_m2 == 0:
        return 0.0
    import math
    return math.sqrt(inlet_area_m2 * outlet_area_m2)


# ---------------------------------------------------------------------------
# Temperature-rise formula (coefficients injected at runtime)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC60890Coefficients:
    """
    IEC TR 60890 empirical coefficients.

    CR-ENG-002: these values are NEVER hard-coded in this module.
    They must be loaded from the licensed dataset at runtime.
    Only the structure is defined here; coefficients default to sentinel values
    that will raise ValueError if mistakenly used without a licensed dataset.
    """
    b: float   # temperature rise coefficient
    c: float   # power exponent
    d: float   # area exponent
    a_ref_m2: float  # reference area [m²]

    # Sentinel check: if b is exactly 0.0, the dataset has not been loaded
    def __post_init__(self) -> None:
        if self.b == 0.0:
            raise ValueError(
                "IEC60890Coefficients.b = 0 indicates the licensed coefficient "
                "dataset has not been loaded.  CR-ENG-002: import the dataset "
                "via the admin upload endpoint before using MODE 1."
            )


@dataclass(frozen=True)
class IEC60890Result:
    """Result of an IEC TR 60890 temperature rise calculation."""
    delta_t_k: float            # estimated temperature rise above ambient [K]
    p_total_w: float            # total power loss used in calculation [W]
    a_eff_m2: float             # effective ventilation area used [m²]
    coefficients: IEC60890Coefficients  # coefficients used
    warnings: tuple[str, ...]


def iec60890_temperature_rise(
    p_total_w: float,
    a_eff_m2: float,
    coefficients: IEC60890Coefficients,
) -> IEC60890Result:
    """
    Calculate IEC TR 60890 empirical temperature rise above ambient.

    ΔT_e = b × P_total^c × (A_eff / A_ref)^d

    CR-ENG-002: the coefficients (b, c, d, A_ref) must be loaded from
    the licensed dataset — they are never hard-coded here.

    Parameters
    ----------
    p_total_w:
        Total power loss in the enclosure [W].
    a_eff_m2:
        Effective ventilation area [m²].
    coefficients:
        Licensed empirical coefficients loaded from the dataset.

    Returns
    -------
    IEC60890Result
        Estimated temperature rise above ambient [K].
    """
    if p_total_w < 0:
        raise ValueError(f"p_total_w must be >= 0 W; got {p_total_w}")
    if a_eff_m2 < 0:
        raise ValueError(f"a_eff_m2 must be >= 0 m²; got {a_eff_m2}")

    warns: list[str] = []

    if a_eff_m2 == 0.0:
        warns.append(
            "IEC TR 60890: A_eff = 0 (no ventilation openings). "
            "The empirical formula may not apply to sealed enclosures. "
            "Verify applicability with the standard."
        )
        # For a sealed enclosure, the formula still applies with A_eff/A_ref → 0
        # but the result is non-physical.  Return 0 with a warning.
        return IEC60890Result(
            delta_t_k=0.0,
            p_total_w=p_total_w,
            a_eff_m2=a_eff_m2,
            coefficients=coefficients,
            warnings=tuple(warns),
        )

    area_ratio = a_eff_m2 / coefficients.a_ref_m2
    delta_t = coefficients.b * (p_total_w ** coefficients.c) * (area_ratio ** coefficients.d)

    return IEC60890Result(
        delta_t_k=delta_t,
        p_total_w=p_total_w,
        a_eff_m2=a_eff_m2,
        coefficients=coefficients,
        warnings=tuple(warns),
    )

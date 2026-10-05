"""
IEC TR 60890 empirical temperature-rise method (MODE 1) — calculation framework.

CR-ENG-002: the IEC TR 60890 coefficient tables are licensed and are NEVER
shipped in this repository. This module implements only the *structure* of the
method, exactly as set out in THERM-EQN-001 §11; every number it needs is
injected through `IEC60890Coefficients`, which an administrator populates from
the imported dataset.

Structure (THERM-EQN-001 §11):

    P_tot      = Σ P_i                                   [W]      §11.1
    A_e        = Σ (b_j · A_j)                           [m²]     §11.2
    Δθ_mid     = c_0 · (P_tot / A_e)^n                   [K]      §11.3
    Δθ_top     = d · Δθ_mid                              [K]      §11.4
    Δθ(y)      = Δθ_mid · f(y / H)                       [K]      §11.5

where b_j is the installation factor for surface j, and c_0, n, d and f all
come from the licensed dataset.

Note that A_e is the *effective cooling surface*, not the ventilation opening
area. The two are different quantities and conflating them understates the
temperature rise of a sealed enclosure, which is the very case the method is
most often used to check.

All values in SI base units (CR-ENG-013); all temperature rises in kelvin
(CR-ENG-003).
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# IEC TR 60890 applicability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC60890Applicability:
    """
    Applicability check result for the IEC TR 60890 empirical method.

    CR-ENG-006: forced ventilation → MODE_1 must not be used.
    """

    is_applicable: bool
    reasons: tuple[str, ...]  # non-empty if not applicable


def check_iec60890_applicability(
    has_forced_ventilation: bool,
    has_busbars_with_unknown_losses: bool,
    form_type: str | None = None,
    enclosure_height_m: float | None = None,
) -> IEC60890Applicability:
    """
    Check whether IEC TR 60890 (MODE 1) applies to the given configuration.

    A non-applicable result means MODE_1 must not be used (CR-ENG-006).
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

    # ASS-M1-003: the empirical correlation was derived for enclosures up to 2 m.
    if enclosure_height_m is not None and enclosure_height_m > 2.0:
        reasons.append(
            f"IEC TR 60890 was derived for enclosures up to 2 m high; this enclosure "
            f"is {enclosure_height_m:.2f} m (ASS-M1-003). Use MODE 2 instead."
        )

    return IEC60890Applicability(is_applicable=not reasons, reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------


def effective_cooling_area_m2(
    surfaces: Sequence[tuple[float, float]],
) -> float:
    """
    Effective cooling surface A_e = Σ (b_j · A_j) [m²] — THERM-EQN-001 §11.2.

    Parameters
    ----------
    surfaces:
        (area_m2, installation_factor) for each surface that can dissipate heat.
        Restricted surfaces (wall-mounted, abutting another cubicle) are either
        omitted by the caller or passed with their own reduced factor.

    Returns
    -------
    float
        Effective cooling surface in m². Zero when no surface dissipates.
    """
    total = 0.0
    for area_m2, factor in surfaces:
        if area_m2 < 0:
            raise ValueError(f"surface area must be >= 0 m²; got {area_m2}")
        if factor < 0:
            raise ValueError(f"installation factor must be >= 0; got {factor}")
        total += area_m2 * factor
    return total


def ventilation_opening_area_m2(
    inlet_area_m2: float,
    outlet_area_m2: float,
) -> float:
    """
    Ventilation opening area used to select the ventilated branch of the method.

    A_vent = sqrt(A_inlet × A_outlet), the geometric mean of the inlet and
    outlet free areas. This is *not* the effective cooling surface A_e; see
    `effective_cooling_area_m2` for that.

    Returns 0 when either opening is absent, i.e. the enclosure is sealed.
    """
    if inlet_area_m2 < 0 or outlet_area_m2 < 0:
        raise ValueError("ventilation areas must be >= 0")
    if inlet_area_m2 == 0 or outlet_area_m2 == 0:
        return 0.0
    return math.sqrt(inlet_area_m2 * outlet_area_m2)


# ---------------------------------------------------------------------------
# Licensed coefficients
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC60890Coefficients:
    """
    IEC TR 60890 empirical coefficients, from the licensed dataset.

    CR-ENG-002: these values are never hard-coded in this repository. The
    administrator imports them, and the API layer attaches them to the
    InputSnapshot for a MODE_1 run.

    Attributes
    ----------
    c0:
        Enclosure constant in Δθ_mid = c_0 · (P_tot / A_e)^n [K·(m²/W)^n].
    n:
        Power-density exponent [-].
    d:
        Temperature-distribution factor, Δθ_top = d · Δθ_mid [-]. Must be ≥ 1:
        the top of an enclosure is never cooler than its mid-height.
    installation_factors:
        Installation factor b_j per surface orientation key, e.g.
        {"VERTICAL": 0.9, "HORIZONTAL_UP": 1.4, "HORIZONTAL_DOWN": 0.5}.
    default_installation_factor:
        Factor applied to a surface whose orientation key is absent.
    height_distribution:
        Optional (y/H, f) pairs for Δθ(y) = Δθ_mid · f(y/H) (§11.5),
        interpolated linearly. Empty disables the height profile.
    dataset_version:
        Version tag of the imported dataset, carried into the audit trail.
    """

    c0: float
    n: float
    d: float
    installation_factors: dict[str, float] = field(default_factory=dict)
    default_installation_factor: float = 1.0
    height_distribution: tuple[tuple[float, float], ...] = ()
    dataset_version: str = ""

    def __post_init__(self) -> None:
        # A zero c_0 means the import produced an empty template rather than a
        # populated dataset; computing with it would silently report no rise.
        if self.c0 <= 0.0:
            raise ValueError(
                "IEC60890Coefficients.c0 must be > 0. A non-positive value means the "
                "licensed coefficient dataset has not been imported. CR-ENG-002: an "
                "administrator must import it before MODE 1 can run."
            )
        if self.n <= 0.0:
            raise ValueError(f"IEC60890Coefficients.n must be > 0; got {self.n}")
        if self.d < 1.0:
            raise ValueError(
                f"IEC60890Coefficients.d must be >= 1 (the top of an enclosure cannot "
                f"be cooler than its mid-height); got {self.d}"
            )
        if self.default_installation_factor < 0.0:
            raise ValueError(
                f"default_installation_factor must be >= 0; "
                f"got {self.default_installation_factor}"
            )
        for key, value in self.installation_factors.items():
            if value < 0.0:
                raise ValueError(
                    f"installation factor for {key!r} must be >= 0; got {value}"
                )
        previous = -1.0
        for ratio, _ in self.height_distribution:
            if not (0.0 <= ratio <= 1.0):
                raise ValueError(
                    f"height_distribution y/H must be in [0, 1]; got {ratio}"
                )
            if ratio <= previous:
                raise ValueError("height_distribution must be sorted by ascending y/H")
            previous = ratio

    def installation_factor(self, orientation_key: str) -> float:
        """Installation factor b_j for a surface orientation."""
        return self.installation_factors.get(
            orientation_key, self.default_installation_factor
        )

    def height_factor(self, height_ratio: float) -> float:
        """
        f(y/H) from §11.5, linearly interpolated.

        Returns 1.0 (the mid-height value) when the dataset carries no profile.
        """
        points = self.height_distribution
        if not points:
            return 1.0
        ratio = min(max(height_ratio, 0.0), 1.0)
        if ratio <= points[0][0]:
            return points[0][1]
        if ratio >= points[-1][0]:
            return points[-1][1]
        for (x0, y0), (x1, y1) in itertools.pairwise(points):
            if x0 <= ratio <= x1:
                span = x1 - x0
                if span == 0.0:
                    return y0
                return y0 + (ratio - x0) * (y1 - y0) / span
        return points[-1][1]


# ---------------------------------------------------------------------------
# Temperature rise
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC60890Result:
    """Result of an IEC TR 60890 temperature-rise calculation."""

    delta_theta_mid_k: float  # Δθ at mid-height [K]
    delta_theta_top_k: float  # Δθ at the top of the enclosure [K]
    p_total_w: float  # total internal power loss used [W]
    effective_cooling_area_m2: float  # A_e used [m²]
    coefficients: IEC60890Coefficients
    warnings: tuple[str, ...]

    def delta_theta_at_height_k(self, height_ratio: float) -> float:
        """Δθ(y) = Δθ_mid · f(y/H) [K] — THERM-EQN-001 §11.5."""
        return self.delta_theta_mid_k * self.coefficients.height_factor(height_ratio)


def iec60890_temperature_rise(
    p_total_w: float,
    effective_cooling_area_m2: float,
    coefficients: IEC60890Coefficients,
) -> IEC60890Result:
    """
    Temperature rise above ambient by the IEC TR 60890 empirical method.

        Δθ_mid = c_0 · (P_tot / A_e)^n        [K]
        Δθ_top = d · Δθ_mid                   [K]

    Parameters
    ----------
    p_total_w:
        Total internal power loss [W].
    effective_cooling_area_m2:
        Effective cooling surface A_e [m²], from `effective_cooling_area_m2`.
    coefficients:
        Licensed coefficients. See CR-ENG-002.

    Raises
    ------
    ValueError
        If A_e is not positive. An enclosure with no cooling surface has no
        steady state, so returning a finite rise — least of all zero — would be
        a dangerously wrong answer for a sealed box.
    """
    if p_total_w < 0:
        raise ValueError(f"p_total_w must be >= 0 W; got {p_total_w}")
    if effective_cooling_area_m2 <= 0:
        raise ValueError(
            f"effective_cooling_area_m2 must be > 0 m²; got {effective_cooling_area_m2}. "
            "An enclosure with no effective cooling surface cannot reach a steady "
            "state, so IEC TR 60890 does not apply to it."
        )

    warns: list[str] = []
    power_density = p_total_w / effective_cooling_area_m2
    delta_mid = coefficients.c0 * float(power_density**coefficients.n)
    delta_top = coefficients.d * delta_mid

    if not coefficients.dataset_version:
        warns.append(
            "The IEC TR 60890 coefficient dataset carries no version tag; the "
            "calculation cannot be traced back to a specific licensed release "
            "(M0-09)."
        )

    return IEC60890Result(
        delta_theta_mid_k=delta_mid,
        delta_theta_top_k=delta_top,
        p_total_w=p_total_w,
        effective_cooling_area_m2=effective_cooling_area_m2,
        coefficients=coefficients,
        warnings=tuple(warns),
    )

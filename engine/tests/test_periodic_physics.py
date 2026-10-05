"""
Periodic physics verification — CR-TECH-003 / DR-010.

These are not regression tests. They ask whether the model is *right*,
against solutions obtained independently of the code, over a range of
conditions rather than at one point. A failure here means the physics is
wrong, which is not something a commit usually breaks and not something a
developer can act on in a pull request — so they run weekly and before a
release, not on every push (M0-05 §3).

Everything here carries @pytest.mark.periodic_physics, which the every-push
CI job deselects.
"""
from __future__ import annotations

import itertools
import math

import pytest
from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    HeatSourceMap,
    LossCalculationSource,
)
from thermal_core.libraries import LossConfidence
from thermal_core.natural_convection.churchill_chu import (
    convection_coefficient_vertical,
    nusselt_vertical_plate,
)
from thermal_core.radiation.gray_body import linearised_radiation_coefficient
from thermal_core.result import SolverStatus
from thermal_core.snapshot import (
    BoundaryConditions,
    CalculationMode,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    SolverSettings,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.solver.iterative import solve, surface_outer_node

pytestmark = pytest.mark.periodic_physics

STEFAN_BOLTZMANN = 5.670374419e-8


# ---------------------------------------------------------------------------
# BM-005 (extended): the solver against an analytical single-zone solution
# ---------------------------------------------------------------------------


def _single_surface_model(
    power_w: float,
    ambient_k: float,
    area_m2: float,
    emissivity: float,
) -> InputSnapshot:
    """
    One compartment in a box whose walls are a single lumped surface.

    Deliberately the simplest model with a closed-form answer: the solver's
    network reduces to air → wall → ambient, so the steady state can be
    written down without it.
    """
    side = math.sqrt(area_m2 / 6.0)
    surfaces = tuple(
        SurfaceSnapshot(
            surface_id=f"face-{index}",
            compartment_id="zone",
            area_m2=area_m2 / 6.0,
            orientation=orientation,
            emissivity=emissivity,
            thickness_m=0.002,
            thermal_conductivity_w_per_m_k=50.0,
            is_external=True,
            internal_emissivity=emissivity,
        )
        for index, orientation in enumerate(
            (
                SurfaceOrientation.VERTICAL,
                SurfaceOrientation.VERTICAL,
                SurfaceOrientation.VERTICAL,
                SurfaceOrientation.VERTICAL,
                SurfaceOrientation.HORIZONTAL_UP,
                SurfaceOrientation.HORIZONTAL_DOWN,
            )
        )
    )
    return InputSnapshot(
        schema_version="1.0",
        library_manifest={"test": "periodic"},
        calculation_id="periodic-physics",
        geometry=GeometrySnapshot(
            enclosure_id="box",
            total_height_m=side,
            total_external_surface_area_m2=area_m2,
            compartments=(
                CompartmentSnapshot(
                    compartment_id="zone",
                    volume_m3=side**3,
                    height_m=side,
                    width_m=side,
                    depth_m=side,
                    surface_ids=tuple(s.surface_id for s in surfaces),
                    heat_source_ids=("src",),
                ),
            ),
            surfaces=surfaces,
            openings=(),
        ),
        heat_source_map=HeatSourceMap(
            enclosure_id="box",
            sources=[
                HeatSource(
                    source_id="src",
                    entity_type=HeatSourceEntityType.OTHER,
                    entity_id="load",
                    power_loss_w=power_w,
                    location=Point3D(x=side / 2, y=side / 2, z=side / 2),
                    volume_m3=None,
                    surface_area_m2=None,
                    confidence=LossConfidence.MEASURED,
                    calculation_source=LossCalculationSource.USER_OVERRIDE,
                    library_ref=None,
                    operating_current_a=None,
                    current_fraction=None,
                    compartment_id="zone",
                )
            ],
        ),
        boundary_conditions=BoundaryConditions(
            ambient_temperature_k=ambient_k,
            ambient_pressure_pa=101325.0,
            ambient_relative_humidity=0.5,
        ),
        solver_settings=SolverSettings(
            calculation_mode=CalculationMode.MODE_2,
            max_iterations=400,
            convergence_tolerance_k=1e-4,
            relaxation_factor=0.5,
            enable_ventilation=False,
        ),
    )


def _analytical_outer_surface_k(
    power_w: float, ambient_k: float, area_m2: float, emissivity: float
) -> float:
    """
    Solve P = A·[h_conv(T)·(T − T_amb) + εσ(T⁴ − T_amb⁴)] for T, by bisection.

    Written independently of the solver: it uses the published correlation
    directly rather than the network, so agreement means the network is
    assembling the physics correctly rather than that two copies of the same
    bug agree.
    """
    side = math.sqrt(area_m2 / 6.0)

    def residual(t_s: float) -> float:
        h_conv = convection_coefficient_vertical(
            t_surface_k=t_s,
            t_air_k=ambient_k,
            height_m=side,
        )
        q_conv = h_conv * area_m2 * (t_s - ambient_k)
        q_rad = emissivity * STEFAN_BOLTZMANN * area_m2 * (t_s**4 - ambient_k**4)
        return q_conv + q_rad - power_w

    low, high = ambient_k + 1e-6, ambient_k + 400.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        if residual(mid) > 0.0:
            high = mid
        else:
            low = mid
    return 0.5 * (low + high)


@pytest.mark.parametrize("power_w", [25.0, 100.0, 400.0, 1200.0])
@pytest.mark.parametrize("ambient_c", [10.0, 35.0, 55.0])
def test_solver_matches_the_analytical_enclosure(power_w: float, ambient_c: float) -> None:
    """
    The solved wall temperature against a closed-form balance.

    A sweep rather than a point: an error in a correlation's exponent hides
    at one operating point and shows across a decade of power.

    The tolerance is 15 %, which sounds loose and is not: the solver splits
    the enclosure into six faces with their own orientations and solves each
    one's inner and outer node, while the closed form lumps all six into a
    single vertical plate. They are different models of the same box, and
    agreeing to within 15 % over a 48× power range is the agreement that
    means something.
    """
    ambient_k = ambient_c + 273.15
    area_m2 = 6.0
    emissivity = 0.9

    result = solve(_single_surface_model(power_w, ambient_k, area_m2, emissivity))
    assert result.status == SolverStatus.CONVERGED

    outer_ids = {
        surface_outer_node(surface.surface_id)
        for surface in _single_surface_model(
            power_w, ambient_k, area_m2, emissivity
        ).geometry.surfaces
    }
    outer = [
        node.temperature_k
        for node in result.node_temperatures
        if node.node_id in outer_ids
    ]
    assert outer, "the model must expose outer surface nodes"
    solved_rise = sum(outer) / len(outer) - ambient_k

    expected_rise = (
        _analytical_outer_surface_k(power_w, ambient_k, area_m2, emissivity) - ambient_k
    )
    assert solved_rise == pytest.approx(expected_rise, rel=0.15)


@pytest.mark.parametrize("power_w", [25.0, 100.0, 400.0, 1200.0])
def test_energy_closes_across_the_power_range(power_w: float) -> None:
    """
    Everything generated leaves through the boundary, at every load.

    Energy conservation is the one check that cannot be satisfied by a
    plausible-looking wrong answer.
    """
    result = solve(_single_surface_model(power_w, 293.15, 6.0, 0.9))
    assert result.status == SolverStatus.CONVERGED
    assert result.total_heat_generation_w == pytest.approx(power_w, rel=1e-9)
    assert result.energy_balance_error_percent < 0.5


def test_temperature_rise_is_monotone_in_power() -> None:
    """A box cannot run cooler when you put more heat into it."""
    rises = [
        (solve(_single_surface_model(p, 293.15, 6.0, 0.9)).max_air_temperature_k() or 0.0)
        - 293.15
        for p in (25.0, 100.0, 400.0, 1200.0)
    ]
    assert all(
        later > earlier for earlier, later in itertools.pairwise(rises)
    )


# ---------------------------------------------------------------------------
# Correlations against published reference values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rayleigh", "expected_nu"),
    [
        # Churchill & Chu (1975) Eq. 8 at Pr = 0.71,
        #   Nu = {0.825 + 0.387·Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)}²
        # evaluated by hand across six decades of Rayleigh number. This
        # catches a mistyped exponent or a dropped Prandtl term — the
        # errors that leave a correlation looking entirely plausible.
        (1.0e4, 5.433),
        (1.0e6, 16.56),
        (1.0e8, 61.07),
        (1.0e10, 252.3),
    ],
)
def test_churchill_chu_reproduces_the_published_correlation(
    rayleigh: float, expected_nu: float
) -> None:
    assert nusselt_vertical_plate(rayleigh, 0.71) == pytest.approx(
        expected_nu, rel=0.02
    )


@pytest.mark.parametrize("t_surface_c", [25.0, 60.0, 120.0, 250.0])
def test_linearised_radiation_tracks_the_fourth_power_law(t_surface_c: float) -> None:
    """
    h_rad·(T_s − T_∞) must equal εσ(T_s⁴ − T_∞⁴) exactly, not approximately.

    The linearisation is an algebraic identity, so any discrepancy is a
    coding error rather than a modelling choice — and CR-ENG-003 means it
    only holds in kelvin, which is precisely what this checks.
    """
    t_s = t_surface_c + 273.15
    t_inf = 293.15
    emissivity = 0.85

    h_rad = linearised_radiation_coefficient(
        emissivity=emissivity, t_surface_k=t_s, t_surroundings_k=t_inf
    )
    linearised = h_rad * (t_s - t_inf)
    exact = emissivity * STEFAN_BOLTZMANN * (t_s**4 - t_inf**4)
    assert linearised == pytest.approx(exact, rel=1e-12)


# ---------------------------------------------------------------------------
# BM-007 — not yet implemented
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "BM-007 (De Vahl Davis square cavity, Nu_avg = 8.80 +/- 2 % at "
        "Ra = 1e6) is a discretised-cavity benchmark. The zonal network "
        "carries one air node per compartment and cannot resolve a cavity "
        "boundary layer, so it cannot reproduce this result and must not "
        "pretend to. Verifying it needs the MODE 4 CFD path, which is an "
        "adapter to an external solver rather than a solver here. "
        "Outstanding against FR-THERM-017 / M0-05 BM-007."
    )
)
def test_bm007_de_vahl_davis_cavity() -> None:  # pragma: no cover
    raise NotImplementedError

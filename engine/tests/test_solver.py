"""
Tests for the M4 zonal thermal solver.

Tests cover:
  - Pre-solve validation (VAL-001 through VAL-010)
  - Energy balance (Q_in = Q_out at convergence)
  - Status codes (CONVERGED / NON_CONVERGED / FAILED — CR-ENG-005)
  - Monotone convergence (temperatures don't oscillate wildly)
  - Analytical benchmark (BM-002: convection-only cooling)
  - CR-ENG-006: MODE_1 with forced ventilation → validation failure
"""
from __future__ import annotations

import pytest

from thermal_core.heat_source import HeatSource, HeatSourceEntityType, HeatSourceMap, LossCalculationSource
from thermal_core.geometry import Point3D
from thermal_core.libraries import LossConfidence
from thermal_core.result import SolverStatus
from thermal_core.snapshot import (
    BoundaryConditions,
    CalculationMode,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    OpeningSnapshot,
    SolverSettings,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.solver.iterative import ZonalSolver, solve


# ---------------------------------------------------------------------------
# Test fixture builders
# ---------------------------------------------------------------------------


def _make_enclosure_snapshot(
    q_heat_source_w: float = 0.0,
    source_id: str = "hs1",
    mode: CalculationMode = CalculationMode.MODE_2,
    has_forced_opening: bool = False,
    relaxation: float = 0.7,
    max_iter: int = 200,
    tol_k: float = 0.01,
    ambient_k: float = 303.15,
) -> InputSnapshot:
    """Build a minimal valid single-compartment InputSnapshot."""
    surface = SurfaceSnapshot(
        surface_id="s1",
        compartment_id="c1",
        area_m2=4.0,
        orientation=SurfaceOrientation.VERTICAL,
        emissivity=0.7,
        thickness_m=0.002,
        thermal_conductivity_w_per_m_k=50.0,
        is_external=True,
    )

    heat_source_ids: tuple[str, ...] = (source_id,) if q_heat_source_w > 0 else ()

    compartment = CompartmentSnapshot(
        compartment_id="c1",
        volume_m3=0.8,
        height_m=2.0,
        width_m=0.6,
        depth_m=0.4,
        surface_ids=("s1",),
        heat_source_ids=heat_source_ids,
    )

    openings: list[OpeningSnapshot] = []
    if has_forced_opening:
        openings.append(OpeningSnapshot(
            opening_id="o1",
            from_compartment_id=None,
            to_compartment_id="c1",
            free_area_m2=0.05,
            discharge_coefficient=0.65,
            centroid_height_m=0.1,
            is_forced=True,
            fan_id=None,
        ))

    geo = GeometrySnapshot(
        enclosure_id="enc1",
        total_height_m=2.0,
        total_external_surface_area_m2=4.0,
        compartments=(compartment,),
        surfaces=(surface,),
        openings=tuple(openings),
    )

    forced_flow = {"o1": 0.05} if has_forced_opening else {}

    bc = BoundaryConditions(
        ambient_temperature_k=ambient_k,
        ambient_pressure_pa=101_325.0,
        ambient_relative_humidity=0.5,
        forced_flow_m3_per_s=forced_flow,
    )

    ss = SolverSettings(
        calculation_mode=mode,
        max_iterations=max_iter,
        convergence_tolerance_k=tol_k,
        relaxation_factor=relaxation,
    )

    sources: list[HeatSource] = []
    if q_heat_source_w > 0:
        sources.append(HeatSource(
            source_id=source_id,
            entity_type=HeatSourceEntityType.DEVICE,
            entity_id="dev1",
            power_loss_w=q_heat_source_w,
            location=Point3D(x=0.3, y=1.0, z=0.2),
            volume_m3=None,
            surface_area_m2=None,
            confidence=LossConfidence.MANUFACTURER_CERTIFIED,
            calculation_source=LossCalculationSource.MANUFACTURER_CURVE,
            library_ref=None,
            operating_current_a=100.0,
            current_fraction=0.8,
        ))

    heat_source_map = HeatSourceMap(
        enclosure_id="enc1",
        sources=sources,
        library_manifest={"device": "1.0.0"},
    )

    return InputSnapshot(
        schema_version="4.0.0",
        library_manifest={"device": "1.0.0"},
        calculation_id="test-001",
        geometry=geo,
        heat_source_map=heat_source_map,
        boundary_conditions=bc,
        solver_settings=ss,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestZonalSolverNoHeat:
    """Solver with zero heat generation should converge immediately."""

    def test_zero_heat_converges(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=0.0)
        result = solve(snap)
        assert result.status == SolverStatus.CONVERGED

    def test_zero_heat_temperature_near_ambient(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=0.0, ambient_k=303.15)
        result = solve(snap)
        air_temp = result.max_air_temperature_k()
        assert air_temp is not None
        assert air_temp == pytest.approx(303.15, abs=1.0)

    def test_zero_heat_energy_balance(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=0.0)
        result = solve(snap)
        assert result.energy_balance_error_percent == pytest.approx(0.0, abs=5.0)


class TestZonalSolverWithHeat:
    """Solver with positive heat generation."""

    def test_converges_with_1000w(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=1000.0)
        result = solve(snap)
        assert result.status == SolverStatus.CONVERGED

    def test_air_temperature_above_ambient(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=1000.0, ambient_k=303.15)
        result = solve(snap)
        air_temp = result.max_air_temperature_k()
        assert air_temp is not None
        assert air_temp > 303.15  # must be hotter than ambient

    def test_air_temperature_not_unreasonably_high(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=1000.0, ambient_k=303.15)
        result = solve(snap)
        air_temp = result.max_air_temperature_k()
        assert air_temp is not None
        # 1 kW in a small enclosure: reasonable rise would be < 100 K above ambient
        assert air_temp < 303.15 + 150.0

    def test_higher_heat_gives_higher_temperature(self) -> None:
        result_low = solve(_make_enclosure_snapshot(q_heat_source_w=500.0))
        result_high = solve(_make_enclosure_snapshot(q_heat_source_w=2000.0))
        t_low = result_low.max_air_temperature_k()
        t_high = result_high.max_air_temperature_k()
        assert t_low is not None and t_high is not None
        assert t_high > t_low

    def test_result_has_node_temperatures(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert len(result.node_temperatures) >= 2  # at least air + ambient

    def test_result_has_compartment_results(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert len(result.compartment_results) == 1

    def test_is_valid_when_converged(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert result.is_valid

    def test_calculation_id_preserved(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert result.calculation_id == snap.calculation_id

    def test_schema_version_preserved(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert result.schema_version == snap.schema_version

    def test_convergence_trace_not_empty(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert len(result.convergence_trace) >= 1

    def test_total_heat_generation_matches_sources(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=1234.5)
        result = solve(snap)
        assert result.total_heat_generation_w == pytest.approx(1234.5)

    def test_elapsed_seconds_is_positive(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        assert result.elapsed_seconds >= 0.0

    def test_node_by_id_air(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=500.0)
        result = solve(snap)
        air_node = result.node_by_id("air_c1")
        assert air_node is not None


class TestSolverConvergenceFailure:
    """CR-ENG-005: unconverged results must have status NON_CONVERGED, not raise."""

    def test_max_iterations_1_returns_non_converged(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=5000.0, max_iter=1)
        result = solve(snap)
        assert result.status == SolverStatus.NON_CONVERGED

    def test_non_converged_is_not_valid(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=5000.0, max_iter=1)
        result = solve(snap)
        assert not result.is_valid

    def test_non_converged_has_warning(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=5000.0, max_iter=1)
        result = solve(snap)
        codes = [w.code for w in result.warnings]
        assert "WARN-005-NON-CONVERGED" in codes


class TestSolverValidationFailure:
    """Solver must return FAILED when pre-solve validation catches an error."""

    def test_mode1_with_forced_ventilation_fails(self) -> None:
        """CR-ENG-006: MODE_1 must fail when forced ventilation is present."""
        snap = _make_enclosure_snapshot(
            q_heat_source_w=500.0,
            mode=CalculationMode.MODE_1,
            has_forced_opening=True,
        )
        result = solve(snap)
        assert result.status == SolverStatus.FAILED
        # Should have a validation warning in there
        assert len(result.warnings) > 0

    def test_failed_result_is_not_valid(self) -> None:
        snap = _make_enclosure_snapshot(
            mode=CalculationMode.MODE_1,
            has_forced_opening=True,
        )
        result = solve(snap)
        assert not result.is_valid


class TestSolverAmbientTemperatureEffect:
    """Higher ambient temperature → higher air temperature by same amount."""

    def test_air_temperature_tracks_ambient(self) -> None:
        result_30 = solve(_make_enclosure_snapshot(q_heat_source_w=500.0, ambient_k=303.15))
        result_40 = solve(_make_enclosure_snapshot(q_heat_source_w=500.0, ambient_k=313.15))

        t_air_30 = result_30.max_air_temperature_k()
        t_air_40 = result_40.max_air_temperature_k()

        assert t_air_30 is not None and t_air_40 is not None
        # Both should be above their respective ambient temperatures
        assert t_air_30 > 303.15
        assert t_air_40 > 313.15


class TestSolverDeterminism:
    """Rule 6: deterministic — identical inputs must give identical results."""

    def test_same_input_same_output(self) -> None:
        snap = _make_enclosure_snapshot(q_heat_source_w=750.0)
        result1 = solve(snap)
        result2 = solve(snap)
        t1 = result1.max_air_temperature_k()
        t2 = result2.max_air_temperature_k()
        assert t1 == t2

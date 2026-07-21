"""Tests for M4 InputSnapshot, GeometrySnapshot, BoundaryConditions, SolverSettings."""
from __future__ import annotations

import pytest

from thermal_core.heat_source import HeatSourceMap
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


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_surface(
    surface_id: str = "s1",
    compartment_id: str = "c1",
    area_m2: float = 1.0,
    orientation: SurfaceOrientation = SurfaceOrientation.VERTICAL,
    emissivity: float = 0.7,
    thickness_m: float = 0.002,
    k: float = 50.0,
    is_external: bool = True,
) -> SurfaceSnapshot:
    return SurfaceSnapshot(
        surface_id=surface_id,
        compartment_id=compartment_id,
        area_m2=area_m2,
        orientation=orientation,
        emissivity=emissivity,
        thickness_m=thickness_m,
        thermal_conductivity_w_per_m_k=k,
        is_external=is_external,
    )


def _make_compartment(
    compartment_id: str = "c1",
    surface_ids: tuple[str, ...] = ("s1",),
    heat_source_ids: tuple[str, ...] = (),
) -> CompartmentSnapshot:
    return CompartmentSnapshot(
        compartment_id=compartment_id,
        volume_m3=0.8,
        height_m=2.0,
        width_m=0.6,
        depth_m=0.4,
        surface_ids=surface_ids,
        heat_source_ids=heat_source_ids,
    )


def _make_geo() -> GeometrySnapshot:
    return GeometrySnapshot(
        enclosure_id="enc1",
        total_height_m=2.0,
        total_external_surface_area_m2=4.0,
        compartments=(_make_compartment(),),
        surfaces=(_make_surface(),),
        openings=(),
    )


def _make_bc(
    ambient_temperature_k: float = 303.15,
    pressure_pa: float = 101_325.0,
) -> BoundaryConditions:
    return BoundaryConditions(
        ambient_temperature_k=ambient_temperature_k,
        ambient_pressure_pa=pressure_pa,
        ambient_relative_humidity=0.5,
    )


def _make_ss(mode: CalculationMode = CalculationMode.MODE_2) -> SolverSettings:
    return SolverSettings(calculation_mode=mode)


def _make_snapshot(
    schema_version: str = "4.0.0",
    calculation_id: str = "test-calc-001",
) -> InputSnapshot:
    return InputSnapshot(
        schema_version=schema_version,
        library_manifest={"device": "1.0.0"},
        calculation_id=calculation_id,
        geometry=_make_geo(),
        heat_source_map=HeatSourceMap(enclosure_id="enc1"),
        boundary_conditions=_make_bc(),
        solver_settings=_make_ss(),
    )


# ---------------------------------------------------------------------------
# SurfaceSnapshot
# ---------------------------------------------------------------------------


class TestSurfaceSnapshot:
    def test_valid_surface(self) -> None:
        s = _make_surface()
        assert s.area_m2 == 1.0
        assert s.is_external is True

    def test_zero_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="area_m2"):
            _make_surface(area_m2=0.0)

    def test_negative_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="area_m2"):
            _make_surface(area_m2=-1.0)

    def test_emissivity_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="emissivity"):
            _make_surface(emissivity=1.1)

    def test_emissivity_zero_accepted(self) -> None:
        s = _make_surface(emissivity=0.0)
        assert s.emissivity == 0.0

    def test_negative_thickness_rejected(self) -> None:
        with pytest.raises(ValueError, match="thickness_m"):
            _make_surface(thickness_m=-0.001)

    def test_zero_conductivity_rejected(self) -> None:
        with pytest.raises(ValueError, match="thermal_conductivity"):
            _make_surface(k=0.0)

    def test_orientations(self) -> None:
        for orient in SurfaceOrientation:
            s = _make_surface(orientation=orient)
            assert s.orientation == orient


# ---------------------------------------------------------------------------
# CompartmentSnapshot
# ---------------------------------------------------------------------------


class TestCompartmentSnapshot:
    def test_valid_compartment(self) -> None:
        c = _make_compartment()
        assert c.volume_m3 == 0.8
        assert c.height_m == 2.0

    def test_zero_volume_rejected(self) -> None:
        with pytest.raises(ValueError, match="volume_m3"):
            CompartmentSnapshot(
                compartment_id="c1",
                volume_m3=0.0,
                height_m=2.0,
                width_m=0.6,
                depth_m=0.4,
                surface_ids=(),
                heat_source_ids=(),
            )

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValueError, match="height_m"):
            CompartmentSnapshot(
                compartment_id="c1",
                volume_m3=0.5,
                height_m=0.0,
                width_m=0.6,
                depth_m=0.4,
                surface_ids=(),
                heat_source_ids=(),
            )


# ---------------------------------------------------------------------------
# GeometrySnapshot
# ---------------------------------------------------------------------------


class TestGeometrySnapshot:
    def test_valid_geo(self) -> None:
        geo = _make_geo()
        assert len(geo.compartments) == 1

    def test_no_compartments_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one compartment"):
            GeometrySnapshot(
                enclosure_id="e1",
                total_height_m=2.0,
                total_external_surface_area_m2=4.0,
                compartments=(),
                surfaces=(),
                openings=(),
            )

    def test_surface_by_id(self) -> None:
        geo = _make_geo()
        s = geo.surface_by_id("s1")
        assert s is not None
        assert s.surface_id == "s1"

    def test_surface_by_id_missing(self) -> None:
        geo = _make_geo()
        assert geo.surface_by_id("nonexistent") is None

    def test_compartment_by_id(self) -> None:
        geo = _make_geo()
        c = geo.compartment_by_id("c1")
        assert c is not None

    def test_openings_for_compartment(self) -> None:
        opening = OpeningSnapshot(
            opening_id="o1",
            from_compartment_id=None,
            to_compartment_id="c1",
            free_area_m2=0.05,
            discharge_coefficient=0.65,
            centroid_height_m=0.1,
            is_forced=False,
            fan_id=None,
        )
        geo = GeometrySnapshot(
            enclosure_id="e1",
            total_height_m=2.0,
            total_external_surface_area_m2=4.0,
            compartments=(_make_compartment(),),
            surfaces=(_make_surface(),),
            openings=(opening,),
        )
        result = geo.openings_for_compartment("c1")
        assert len(result) == 1
        assert result[0].opening_id == "o1"


# ---------------------------------------------------------------------------
# BoundaryConditions
# ---------------------------------------------------------------------------


class TestBoundaryConditions:
    def test_valid_bc(self) -> None:
        bc = _make_bc()
        assert bc.ambient_temperature_k == pytest.approx(303.15)

    def test_zero_temperature_rejected(self) -> None:
        with pytest.raises(ValueError, match="ambient_temperature_k"):
            _make_bc(ambient_temperature_k=0.0)

    def test_negative_pressure_rejected(self) -> None:
        with pytest.raises(ValueError, match="ambient_pressure_pa"):
            _make_bc(pressure_pa=-1.0)

    def test_humidity_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="ambient_relative_humidity"):
            BoundaryConditions(
                ambient_temperature_k=303.15,
                ambient_pressure_pa=101325.0,
                ambient_relative_humidity=1.1,
            )

    def test_forced_flow_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="forced_flow"):
            BoundaryConditions(
                ambient_temperature_k=303.15,
                ambient_pressure_pa=101325.0,
                ambient_relative_humidity=0.5,
                forced_flow_m3_per_s={"o1": -0.1},
            )


# ---------------------------------------------------------------------------
# SolverSettings
# ---------------------------------------------------------------------------


class TestSolverSettings:
    def test_defaults(self) -> None:
        ss = _make_ss()
        assert ss.max_iterations == 200
        assert ss.convergence_tolerance_k == pytest.approx(0.01)
        assert ss.relaxation_factor == pytest.approx(0.7)

    def test_zero_iterations_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_iterations"):
            SolverSettings(calculation_mode=CalculationMode.MODE_2, max_iterations=0)

    def test_zero_tolerance_rejected(self) -> None:
        with pytest.raises(ValueError, match="convergence_tolerance_k"):
            SolverSettings(
                calculation_mode=CalculationMode.MODE_2,
                convergence_tolerance_k=0.0,
            )

    def test_relaxation_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="relaxation_factor"):
            SolverSettings(
                calculation_mode=CalculationMode.MODE_2,
                relaxation_factor=1.1,
            )


# ---------------------------------------------------------------------------
# InputSnapshot
# ---------------------------------------------------------------------------


class TestInputSnapshot:
    def test_valid_snapshot(self) -> None:
        snap = _make_snapshot()
        assert snap.schema_version == "4.0.0"
        assert snap.calculation_id == "test-calc-001"

    def test_empty_schema_version_rejected(self) -> None:
        with pytest.raises(ValueError, match="schema_version"):
            _make_snapshot(schema_version="")

    def test_empty_calculation_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="calculation_id"):
            _make_snapshot(calculation_id="")

    def test_forced_flow_references_unknown_opening_rejected(self) -> None:
        bc = BoundaryConditions(
            ambient_temperature_k=303.15,
            ambient_pressure_pa=101325.0,
            ambient_relative_humidity=0.5,
            forced_flow_m3_per_s={"nonexistent_opening": 0.1},
        )
        with pytest.raises(ValueError, match="forced_flow opening"):
            InputSnapshot(
                schema_version="4.0.0",
                library_manifest={"x": "1"},
                calculation_id="c1",
                geometry=_make_geo(),
                heat_source_map=HeatSourceMap(enclosure_id="enc1"),
                boundary_conditions=bc,
                solver_settings=_make_ss(),
            )

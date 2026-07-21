"""Tests for M3 HeatSource domain objects."""
import pytest

from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    HeatSourceMap,
    LossBreakdown,
    LossCalculationSource,
)
from thermal_core.libraries import LossConfidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _loc() -> Point3D:
    return Point3D(x=0.1, y=0.5, z=1.2)


def _make_heat_source(
    power_loss_w: float = 100.0,
    volume_m3: float | None = 0.008,
    surface_area_m2: float | None = 0.4,
    entity_type: HeatSourceEntityType = HeatSourceEntityType.DEVICE,
) -> HeatSource:
    return HeatSource(
        source_id="hs-001",
        entity_type=entity_type,
        entity_id="entity-001",
        power_loss_w=power_loss_w,
        location=_loc(),
        volume_m3=volume_m3,
        surface_area_m2=surface_area_m2,
        confidence=LossConfidence.MANUFACTURER_CERTIFIED,
        calculation_source=LossCalculationSource.MANUFACTURER_CURVE,
        library_ref="dev-3wl-001@1.0.0",
        operating_current_a=2000.0,
        current_fraction=0.8,
        breakdown=LossBreakdown(joule_loss_w=100.0),
    )


# ---------------------------------------------------------------------------
# LossBreakdown
# ---------------------------------------------------------------------------


class TestLossBreakdown:
    def test_all_none(self) -> None:
        bd = LossBreakdown()
        assert bd.joule_loss_w is None
        assert bd.switching_loss_w is None
        assert bd.iron_loss_w is None
        assert bd.contact_loss_w is None
        assert bd.other_w is None

    def test_partial_breakdown(self) -> None:
        bd = LossBreakdown(joule_loss_w=80.0, iron_loss_w=20.0)
        assert bd.joule_loss_w == pytest.approx(80.0)
        assert bd.iron_loss_w == pytest.approx(20.0)
        assert bd.switching_loss_w is None

    def test_frozen(self) -> None:
        bd = LossBreakdown(joule_loss_w=10.0)
        with pytest.raises((AttributeError, TypeError)):
            bd.joule_loss_w = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HeatSource construction and validation
# ---------------------------------------------------------------------------


class TestHeatSource:
    def test_basic_creation(self) -> None:
        hs = _make_heat_source()
        assert hs.power_loss_w == pytest.approx(100.0)
        assert hs.entity_type == HeatSourceEntityType.DEVICE
        assert hs.confidence == LossConfidence.MANUFACTURER_CERTIFIED
        assert hs.library_ref == "dev-3wl-001@1.0.0"

    def test_zero_power_loss_allowed(self) -> None:
        hs = _make_heat_source(power_loss_w=0.0)
        assert hs.power_loss_w == pytest.approx(0.0)

    def test_negative_power_loss_rejected(self) -> None:
        with pytest.raises(ValueError, match="power_loss_w must be >= 0"):
            _make_heat_source(power_loss_w=-1.0)

    def test_zero_volume_rejected(self) -> None:
        with pytest.raises(ValueError, match="volume_m3 must be > 0"):
            _make_heat_source(volume_m3=0.0)

    def test_negative_volume_rejected(self) -> None:
        with pytest.raises(ValueError, match="volume_m3 must be > 0"):
            _make_heat_source(volume_m3=-0.01)

    def test_zero_surface_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="surface_area_m2 must be > 0"):
            _make_heat_source(surface_area_m2=0.0)

    def test_none_volume_allowed(self) -> None:
        hs = _make_heat_source(volume_m3=None)
        assert hs.volume_m3 is None

    def test_none_surface_area_allowed(self) -> None:
        hs = _make_heat_source(surface_area_m2=None)
        assert hs.surface_area_m2 is None

    def test_frozen(self) -> None:
        hs = _make_heat_source()
        with pytest.raises((AttributeError, TypeError)):
            hs.power_loss_w = 999.0  # type: ignore[misc]

    def test_entity_types(self) -> None:
        for etype in HeatSourceEntityType:
            hs = _make_heat_source(entity_type=etype)
            assert hs.entity_type == etype


# ---------------------------------------------------------------------------
# HeatSource derived properties
# ---------------------------------------------------------------------------


class TestHeatSourceDerivedProperties:
    def test_volumetric_density(self) -> None:
        hs = _make_heat_source(power_loss_w=100.0, volume_m3=0.01)
        density = hs.volumetric_power_density_w_per_m3()
        assert density == pytest.approx(10_000.0)

    def test_volumetric_density_none_when_no_volume(self) -> None:
        hs = _make_heat_source(volume_m3=None)
        assert hs.volumetric_power_density_w_per_m3() is None

    def test_surface_heat_flux(self) -> None:
        hs = _make_heat_source(power_loss_w=200.0, surface_area_m2=0.5)
        flux = hs.surface_heat_flux_w_per_m2()
        assert flux == pytest.approx(400.0)

    def test_surface_heat_flux_none_when_no_area(self) -> None:
        hs = _make_heat_source(surface_area_m2=None)
        assert hs.surface_heat_flux_w_per_m2() is None

    def test_zero_power_loss_density(self) -> None:
        hs = _make_heat_source(power_loss_w=0.0, volume_m3=0.01)
        assert hs.volumetric_power_density_w_per_m3() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# HeatSourceMap
# ---------------------------------------------------------------------------


def _make_map() -> HeatSourceMap:
    sources = [
        _make_heat_source(power_loss_w=100.0, entity_type=HeatSourceEntityType.DEVICE),
        HeatSource(
            source_id="hs-002",
            entity_type=HeatSourceEntityType.BUSBAR,
            entity_id="entity-002",
            power_loss_w=30.0,
            location=Point3D(0.2, 0.3, 0.4),
            volume_m3=None,
            surface_area_m2=None,
            confidence=LossConfidence.CORRELATED,
            calculation_source=LossCalculationSource.DC_RESISTANCE_CALC,
            library_ref="bp-cu-50x5-001@1.0.0",
            operating_current_a=500.0,
            current_fraction=0.5,
        ),
        HeatSource(
            source_id="hs-003",
            entity_type=HeatSourceEntityType.JOINT,
            entity_id="entity-003",
            power_loss_w=2.5,
            location=Point3D(0.3, 0.3, 0.4),
            volume_m3=None,
            surface_area_m2=None,
            confidence=LossConfidence.MANUFACTURER_TYPICAL,
            calculation_source=LossCalculationSource.JOINT_RESISTANCE,
            library_ref="conn-m10-ag-001@1.0.0",
            operating_current_a=500.0,
            current_fraction=None,
            breakdown=LossBreakdown(contact_loss_w=2.5),
        ),
        HeatSource(
            source_id="hs-004",
            entity_type=HeatSourceEntityType.DEVICE,
            entity_id="entity-004",
            power_loss_w=80.0,
            location=Point3D(0.5, 0.5, 1.0),
            volume_m3=0.005,
            surface_area_m2=None,
            confidence=LossConfidence.ESTIMATED,
            calculation_source=LossCalculationSource.ESTIMATED_FRACTION,
            library_ref=None,
            operating_current_a=None,
            current_fraction=None,
        ),
    ]
    return HeatSourceMap(
        enclosure_id="enc-001",
        sources=sources,
        library_manifest={"device": "1.0.0", "busbar": "1.0.0"},
    )


class TestHeatSourceMap:
    def test_total_power_loss(self) -> None:
        hsmap = _make_map()
        assert hsmap.total_power_loss_w() == pytest.approx(212.5)

    def test_empty_map_total(self) -> None:
        hsmap = HeatSourceMap(enclosure_id="enc-empty")
        assert hsmap.total_power_loss_w() == pytest.approx(0.0)

    def test_by_entity_type_device(self) -> None:
        hsmap = _make_map()
        devices = hsmap.by_entity_type(HeatSourceEntityType.DEVICE)
        assert len(devices) == 2
        ids = {s.entity_id for s in devices}
        assert ids == {"entity-001", "entity-004"}

    def test_by_entity_type_joint(self) -> None:
        hsmap = _make_map()
        joints = hsmap.by_entity_type(HeatSourceEntityType.JOINT)
        assert len(joints) == 1
        assert joints[0].entity_id == "entity-003"

    def test_by_entity_type_cable_empty(self) -> None:
        hsmap = _make_map()
        cables = hsmap.by_entity_type(HeatSourceEntityType.CABLE)
        assert cables == []

    def test_by_entity_id_found(self) -> None:
        hsmap = _make_map()
        hs = hsmap.by_entity_id("entity-002")
        assert hs is not None
        assert hs.entity_type == HeatSourceEntityType.BUSBAR

    def test_by_entity_id_not_found(self) -> None:
        hsmap = _make_map()
        assert hsmap.by_entity_id("nonexistent") is None

    def test_confidence_summary(self) -> None:
        hsmap = _make_map()
        summary = hsmap.confidence_summary()
        assert summary[LossConfidence.MANUFACTURER_CERTIFIED.value] == 1
        assert summary[LossConfidence.CORRELATED.value] == 1
        assert summary[LossConfidence.MANUFACTURER_TYPICAL.value] == 1
        assert summary[LossConfidence.ESTIMATED.value] == 1
        assert summary[LossConfidence.ASSUMED_DEFAULT.value] == 0

    def test_has_low_confidence_sources_true(self) -> None:
        hsmap = _make_map()
        assert hsmap.has_low_confidence_sources() is True

    def test_has_low_confidence_sources_false(self) -> None:
        hs = _make_heat_source()  # MANUFACTURER_CERTIFIED
        hsmap = HeatSourceMap(enclosure_id="enc-clean", sources=[hs])
        assert hsmap.has_low_confidence_sources() is False


# ---------------------------------------------------------------------------
# LossCalculationSource enum coverage
# ---------------------------------------------------------------------------


class TestEnumCoverage:
    def test_all_loss_calc_sources_accessible(self) -> None:
        expected = {
            "MANUFACTURER_CURVE",
            "MANUFACTURER_RATED",
            "IEC_60890_TABLE",
            "DC_RESISTANCE_CALC",
            "AC_RESISTANCE_CALC",
            "JOINT_RESISTANCE",
            "USER_OVERRIDE",
            "ESTIMATED_FRACTION",
            "UNKNOWN",
        }
        actual = {e.value for e in LossCalculationSource}
        assert actual == expected

    def test_all_entity_types_accessible(self) -> None:
        expected = {"DEVICE", "BUSBAR", "JOINT", "CABLE", "TRANSFORMER", "RESISTOR", "OTHER"}
        actual = {e.value for e in HeatSourceEntityType}
        assert actual == expected

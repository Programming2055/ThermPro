"""Tests for M3 power-loss calculation models."""
import warnings

import pytest

from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    LossCalculationSource,
)
from thermal_core.libraries import (
    BusbarCoating,
    BusbarProfile,
    BusbarProfileLibraryEntry,
    CableConductor,
    CableInsulation,
    CableLibraryEntry,
    ConnectionLibraryEntry,
    ContactQuality,
    DeviceLibraryEntry,
    LossConfidence,
    LossCurvePoint,
    MountingType,
    VentilationRequirement,
)
from thermal_core.loss_models import (
    T_REF_K,
    _interpolate_loss_curve,
    busbar_heat_source,
    busbar_heat_source_resolved,
    cable_heat_source,
    device_heat_source,
    joint_heat_source,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _loc() -> Point3D:
    return Point3D(x=0.2, y=0.4, z=1.1)


def _make_device(curve: tuple[LossCurvePoint, ...] | None = None) -> DeviceLibraryEntry:
    if curve is None:
        curve = (
            LossCurvePoint(0.0, 0.0),
            LossCurvePoint(0.5, 30.0),
            LossCurvePoint(1.0, 120.0),
            LossCurvePoint(1.25, 187.5),
        )
    return DeviceLibraryEntry(
        entry_id="dev-3wl-001",
        library_version="1.0.0",
        manufacturer="Siemens",
        family="3WL",
        model="3WL1225",
        rated_current_a=2500.0,
        poles=3,
        width_m=0.4,
        height_m=0.7,
        depth_m=0.35,
        mounting_type=MountingType.DRAW_OUT,
        ventilation_requirement=VentilationRequirement.CLEARANCE_TOP,
        max_ambient_temp_k=313.15,
        power_loss_curve=curve,
        loss_confidence=LossConfidence.MANUFACTURER_CERTIFIED,
    )


def _make_busbar_profile(cross_section_area_m2: float = 250e-6) -> BusbarProfileLibraryEntry:
    return BusbarProfileLibraryEntry(
        entry_id="bp-cu-50x5-001",
        library_version="1.0.0",
        name="Cu 50×5 Flat Bare",
        material_ref="mat-cu-001",
        profile=BusbarProfile.FLAT,
        coating=BusbarCoating.BARE,
        thickness_m=0.005,
        width_m=0.050,
        cross_section_area_m2=cross_section_area_m2,
        max_continuous_current_a=630.0,
        emissivity_override=None,
    )


def _make_connection() -> ConnectionLibraryEntry:
    return ConnectionLibraryEntry(
        entry_id="conn-m10-ag-001",
        library_version="1.0.0",
        name="M10 silver-plated Cu-Cu bolted joint",
        contact_quality=ContactQuality.SILVER_PLATED,
        plating="silver",
        bolt_size_m=0.010,
        bolt_torque_n_m=25.0,
        contact_pressure_pa=None,
        joint_resistance_ohm=5e-6,
        resistance_source="JOINT_LIBRARY",
        age_factor=1.0,
    )


def _make_cable() -> CableLibraryEntry:
    return CableLibraryEntry(
        entry_id="cbl-cu-185-001",
        library_version="1.0.0",
        manufacturer=None,
        designation="YJY 3×185 mm² CU XLPE",
        conductor=CableConductor.COPPER,
        insulation=CableInsulation.XLPE,
        conductor_cross_section_m2=185e-6,
        outer_diameter_m=0.040,
        rated_current_a=385.0,
        resistance_ohm_per_m=9.95e-5,
        temp_coeff_resistance_per_k=3.93e-3,
        max_conductor_temp_k=363.15,
    )


# ---------------------------------------------------------------------------
# Reference temperature
# ---------------------------------------------------------------------------


def test_t_ref_k_is_20c() -> None:
    assert T_REF_K == pytest.approx(293.15)


# ---------------------------------------------------------------------------
# _interpolate_loss_curve
# ---------------------------------------------------------------------------


class TestInterpolateLossCurve:
    def _curve(self) -> tuple[LossCurvePoint, ...]:
        return (
            LossCurvePoint(0.0, 0.0),
            LossCurvePoint(0.5, 30.0),
            LossCurvePoint(1.0, 120.0),
            LossCurvePoint(1.25, 187.5),
        )

    def test_at_zero(self) -> None:
        assert _interpolate_loss_curve(self._curve(), 0.0) == pytest.approx(0.0)

    def test_at_rated(self) -> None:
        assert _interpolate_loss_curve(self._curve(), 1.0) == pytest.approx(120.0)

    def test_midpoint_interpolation(self) -> None:
        # midpoint between 0.5 and 1.0 → midpoint between 30 and 120 = 75
        assert _interpolate_loss_curve(self._curve(), 0.75) == pytest.approx(75.0)

    def test_below_range_clamps_to_first(self) -> None:
        assert _interpolate_loss_curve(self._curve(), -0.5) == pytest.approx(0.0)

    def test_above_range_clamps_to_last(self) -> None:
        result = _interpolate_loss_curve(self._curve(), 2.0)
        assert result == pytest.approx(187.5)

    def test_empty_curve_raises(self) -> None:
        with pytest.raises(ValueError, match="Loss curve is empty"):
            _interpolate_loss_curve((), 1.0)

    def test_unsorted_input_still_works(self) -> None:
        curve = (
            LossCurvePoint(1.0, 120.0),
            LossCurvePoint(0.0, 0.0),
            LossCurvePoint(0.5, 30.0),
        )
        assert _interpolate_loss_curve(curve, 0.75) == pytest.approx(75.0)


# ---------------------------------------------------------------------------
# device_heat_source
# ---------------------------------------------------------------------------


class TestDeviceHeatSource:
    def test_rated_current(self) -> None:
        dev = _make_device()
        hs = device_heat_source(
            device=dev,
            entity_id="ent-001",
            location=_loc(),
            operating_current_a=2500.0,
        )
        assert isinstance(hs, HeatSource)
        assert hs.power_loss_w == pytest.approx(120.0)
        assert hs.entity_type == HeatSourceEntityType.DEVICE
        assert hs.calculation_source == LossCalculationSource.MANUFACTURER_CURVE
        assert hs.current_fraction == pytest.approx(1.0)
        assert hs.library_ref == "dev-3wl-001@1.0.0"

    def test_half_rated_current(self) -> None:
        dev = _make_device()
        hs = device_heat_source(
            device=dev,
            entity_id="ent-001",
            location=_loc(),
            operating_current_a=1250.0,
        )
        assert hs.power_loss_w == pytest.approx(30.0)
        assert hs.current_fraction == pytest.approx(0.5)

    def test_zero_current(self) -> None:
        dev = _make_device()
        hs = device_heat_source(
            device=dev,
            entity_id="ent-001",
            location=_loc(),
            operating_current_a=0.0,
        )
        assert hs.power_loss_w == pytest.approx(0.0)

    def test_negative_current_rejected(self) -> None:
        dev = _make_device()
        with pytest.raises(ValueError, match="operating_current_a must be >= 0"):
            device_heat_source(
                device=dev,
                entity_id="ent-001",
                location=_loc(),
                operating_current_a=-100.0,
            )

    def test_confidence_matches_device(self) -> None:
        dev = _make_device()
        hs = device_heat_source(
            device=dev, entity_id="ent-001", location=_loc(), operating_current_a=2500.0
        )
        assert hs.confidence == LossConfidence.MANUFACTURER_CERTIFIED

    def test_optional_volume_and_surface(self) -> None:
        dev = _make_device()
        hs = device_heat_source(
            device=dev,
            entity_id="ent-001",
            location=_loc(),
            operating_current_a=2500.0,
            volume_m3=0.098,
            surface_area_m2=1.6,
        )
        assert hs.volume_m3 == pytest.approx(0.098)
        assert hs.surface_area_m2 == pytest.approx(1.6)

    def test_source_id_is_unique(self) -> None:
        dev = _make_device()
        hs1 = device_heat_source(device=dev, entity_id="e", location=_loc(), operating_current_a=0.0)
        hs2 = device_heat_source(device=dev, entity_id="e", location=_loc(), operating_current_a=0.0)
        assert hs1.source_id != hs2.source_id


# ---------------------------------------------------------------------------
# busbar_heat_source (stub)
# ---------------------------------------------------------------------------


class TestBusbarHeatSourceStub:
    def test_raises_not_implemented(self) -> None:
        profile = _make_busbar_profile()
        with pytest.raises(NotImplementedError):
            busbar_heat_source(
                profile=profile,
                entity_id="ent-bb",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
            )


# ---------------------------------------------------------------------------
# busbar_heat_source_resolved
# ---------------------------------------------------------------------------

# Copper resistivity at 20 °C: 1.72e-8 Ω·m
CU_RESISTIVITY = 1.72e-8


class TestBusbarHeatSourceResolved:
    def test_basic_dc_loss(self) -> None:
        profile = _make_busbar_profile(cross_section_area_m2=250e-6)
        # R = ρ·L/A = 1.72e-8 × 1.0 / 250e-6 = 6.88e-5 Ω
        # P = I² × R = 500² × 6.88e-5 = 17.2 W
        hs = busbar_heat_source_resolved(
            profile=profile,
            material_resistivity_ohm_m=CU_RESISTIVITY,
            entity_id="ent-bb",
            location=_loc(),
            length_m=1.0,
            operating_current_a=500.0,
        )
        expected_r = CU_RESISTIVITY * 1.0 / 250e-6
        expected_p = 500.0 ** 2 * expected_r
        assert hs.power_loss_w == pytest.approx(expected_p, rel=1e-5)
        assert hs.calculation_source == LossCalculationSource.DC_RESISTANCE_CALC
        assert hs.entity_type == HeatSourceEntityType.BUSBAR

    def test_ac_correction_applied(self) -> None:
        profile = _make_busbar_profile()
        hs = busbar_heat_source_resolved(
            profile=profile,
            material_resistivity_ohm_m=CU_RESISTIVITY,
            entity_id="ent-bb",
            location=_loc(),
            length_m=1.0,
            operating_current_a=500.0,
            k_ac=1.1,
            k_ac_source="SKIN_EFFECT",
        )
        hs_dc = busbar_heat_source_resolved(
            profile=profile,
            material_resistivity_ohm_m=CU_RESISTIVITY,
            entity_id="ent-bb",
            location=_loc(),
            length_m=1.0,
            operating_current_a=500.0,
        )
        assert hs.power_loss_w == pytest.approx(hs_dc.power_loss_w * 1.1, rel=1e-5)
        assert hs.calculation_source == LossCalculationSource.AC_RESISTANCE_CALC

    def test_current_fraction_computed(self) -> None:
        profile = _make_busbar_profile()
        hs = busbar_heat_source_resolved(
            profile=profile,
            material_resistivity_ohm_m=CU_RESISTIVITY,
            entity_id="ent-bb",
            location=_loc(),
            length_m=1.0,
            operating_current_a=315.0,  # half of 630 A
        )
        assert hs.current_fraction == pytest.approx(0.5, rel=1e-5)

    def test_zero_length_rejected(self) -> None:
        profile = _make_busbar_profile()
        with pytest.raises(ValueError, match="length_m must be > 0"):
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=0.0,
                operating_current_a=500.0,
            )

    def test_negative_current_rejected(self) -> None:
        profile = _make_busbar_profile()
        with pytest.raises(ValueError, match="operating_current_a must be >= 0"):
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=-1.0,
            )

    def test_k_ac_below_one_rejected(self) -> None:
        profile = _make_busbar_profile()
        with pytest.raises(ValueError, match="k_ac must be >= 1.0"):
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
                k_ac=0.9,
            )

    def test_zero_resistivity_rejected(self) -> None:
        profile = _make_busbar_profile()
        with pytest.raises(ValueError, match="material_resistivity_ohm_m must be > 0"):
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=0.0,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
            )

    def test_cr_eng_011_warning_large_cross_section(self) -> None:
        """CR-ENG-011: K_AC=1.0 must warn when cross-section > 400 mm²."""
        profile = _make_busbar_profile(cross_section_area_m2=500e-6)  # 500 mm²
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
                k_ac=1.0,
            )
        assert any("CR-ENG-011" in str(w.message) for w in caught)

    def test_no_warning_small_cross_section(self) -> None:
        profile = _make_busbar_profile(cross_section_area_m2=250e-6)  # 250 mm²
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
                k_ac=1.0,
            )
        assert not any("CR-ENG-011" in str(w.message) for w in caught)

    def test_no_warning_large_cross_section_with_k_ac(self) -> None:
        """No warning when k_ac > 1.0 even for large cross-section."""
        profile = _make_busbar_profile(cross_section_area_m2=500e-6)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            busbar_heat_source_resolved(
                profile=profile,
                material_resistivity_ohm_m=CU_RESISTIVITY,
                entity_id="e",
                location=_loc(),
                length_m=1.0,
                operating_current_a=500.0,
                k_ac=1.05,
            )
        assert not any("CR-ENG-011" in str(w.message) for w in caught)


# ---------------------------------------------------------------------------
# joint_heat_source — CR-ENG-008
# ---------------------------------------------------------------------------


class TestJointHeatSource:
    def test_basic_joint_loss(self) -> None:
        conn = _make_connection()
        # P = I² × R × age_factor = 500² × 5e-6 × 1.0 = 1.25 W
        hs = joint_heat_source(
            connection=conn,
            entity_id="jnt-001",
            location=_loc(),
            operating_current_a=500.0,
        )
        assert hs.power_loss_w == pytest.approx(1.25)
        assert hs.entity_type == HeatSourceEntityType.JOINT
        assert hs.calculation_source == LossCalculationSource.JOINT_RESISTANCE
        assert hs.breakdown is not None
        assert hs.breakdown.contact_loss_w == pytest.approx(1.25)

    def test_aged_joint_higher_loss(self) -> None:
        conn_fresh = ConnectionLibraryEntry(
            entry_id="conn-aged",
            library_version="1.0.0",
            name="Aged bare Cu-Cu",
            contact_quality=ContactQuality.BARE_AGED,
            plating=None,
            bolt_size_m=0.012,
            bolt_torque_n_m=None,
            contact_pressure_pa=None,
            joint_resistance_ohm=5e-6,
            resistance_source="JOINT_LIBRARY",
            age_factor=2.5,
        )
        hs = joint_heat_source(
            connection=conn_fresh,
            entity_id="jnt-002",
            location=_loc(),
            operating_current_a=500.0,
        )
        # P = 500² × 5e-6 × 2.5 = 3.125 W
        assert hs.power_loss_w == pytest.approx(3.125)

    def test_negative_current_rejected(self) -> None:
        conn = _make_connection()
        with pytest.raises(ValueError, match="operating_current_a must be >= 0"):
            joint_heat_source(
                connection=conn,
                entity_id="jnt-001",
                location=_loc(),
                operating_current_a=-1.0,
            )

    def test_no_volume_or_surface(self) -> None:
        """Joint is always a point source — no volume or surface."""
        conn = _make_connection()
        hs = joint_heat_source(
            connection=conn,
            entity_id="jnt-001",
            location=_loc(),
            operating_current_a=500.0,
        )
        assert hs.volume_m3 is None
        assert hs.surface_area_m2 is None

    def test_current_fraction_is_none(self) -> None:
        conn = _make_connection()
        hs = joint_heat_source(
            connection=conn,
            entity_id="jnt-001",
            location=_loc(),
            operating_current_a=500.0,
        )
        assert hs.current_fraction is None


# ---------------------------------------------------------------------------
# cable_heat_source
# ---------------------------------------------------------------------------


class TestCableHeatSource:
    def test_basic_cable_loss(self) -> None:
        cable = _make_cable()
        # R_total = 9.95e-5 Ω/m × 10 m = 9.95e-4 Ω
        # P = 300² × 9.95e-4 = 89.55 W
        hs = cable_heat_source(
            cable=cable,
            entity_id="cbl-001",
            location=_loc(),
            length_m=10.0,
            operating_current_a=300.0,
        )
        expected_p = 300.0 ** 2 * 9.95e-5 * 10.0
        assert hs.power_loss_w == pytest.approx(expected_p, rel=1e-4)
        assert hs.entity_type == HeatSourceEntityType.CABLE
        assert hs.calculation_source == LossCalculationSource.DC_RESISTANCE_CALC

    def test_current_fraction_computed(self) -> None:
        cable = _make_cable()
        hs = cable_heat_source(
            cable=cable,
            entity_id="cbl-001",
            location=_loc(),
            length_m=5.0,
            operating_current_a=192.5,  # half rated (385 / 2)
        )
        assert hs.current_fraction == pytest.approx(0.5, rel=1e-4)

    def test_zero_length_rejected(self) -> None:
        cable = _make_cable()
        with pytest.raises(ValueError, match="length_m must be > 0"):
            cable_heat_source(
                cable=cable,
                entity_id="cbl-001",
                location=_loc(),
                length_m=0.0,
                operating_current_a=300.0,
            )

    def test_negative_current_rejected(self) -> None:
        cable = _make_cable()
        with pytest.raises(ValueError, match="operating_current_a must be >= 0"):
            cable_heat_source(
                cable=cable,
                entity_id="cbl-001",
                location=_loc(),
                length_m=5.0,
                operating_current_a=-1.0,
            )

    def test_library_ref_format(self) -> None:
        cable = _make_cable()
        hs = cable_heat_source(
            cable=cable,
            entity_id="cbl-001",
            location=_loc(),
            length_m=5.0,
            operating_current_a=300.0,
        )
        assert hs.library_ref == "cbl-cu-185-001@1.0.0"

    def test_optional_volume_and_surface(self) -> None:
        cable = _make_cable()
        hs = cable_heat_source(
            cable=cable,
            entity_id="cbl-001",
            location=_loc(),
            length_m=5.0,
            operating_current_a=300.0,
            volume_m3=0.025,
            surface_area_m2=0.63,
        )
        assert hs.volume_m3 == pytest.approx(0.025)
        assert hs.surface_area_m2 == pytest.approx(0.63)

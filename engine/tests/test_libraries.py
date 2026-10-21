"""Tests for M3 engineering library domain types."""
import pytest

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
    FanCurvePoint,
    FanDirection,
    FanLibraryEntry,
    FilterLibraryEntry,
    LossConfidence,
    LossCurvePoint,
    MaterialCategory,
    MaterialLibraryEntry,
    MountingType,
    SurfaceLibraryEntry,
    VentilationRequirement,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_material() -> MaterialLibraryEntry:
    return MaterialLibraryEntry(
        entry_id="mat-cu-001",
        library_version="1.0.0",
        name="Copper (ETP)",
        category=MaterialCategory.CONDUCTOR,
        thermal_conductivity_w_per_m_k=385.0,
        density_kg_per_m3=8960.0,
        specific_heat_j_per_kg_k=385.0,
        electrical_resistivity_ohm_m=1.72e-8,
        temp_coeff_resistance_per_k=3.93e-3,
        emissivity=0.03,
        max_operating_temp_k=473.15,  # 200 °C
        references=("IEC 60228",),
    )


def _make_busbar_profile() -> BusbarProfileLibraryEntry:
    return BusbarProfileLibraryEntry(
        entry_id="bp-cu-50x5-001",
        library_version="1.0.0",
        name="Cu 50×5 Flat Bare",
        material_ref="mat-cu-001",
        profile=BusbarProfile.FLAT,
        coating=BusbarCoating.BARE,
        thickness_m=0.005,
        width_m=0.050,
        cross_section_area_m2=0.000250,
        max_continuous_current_a=630.0,
        emissivity_override=None,
    )


def _make_loss_curve() -> tuple[LossCurvePoint, ...]:
    return (
        LossCurvePoint(current_fraction=0.0, power_loss_w=0.0),
        LossCurvePoint(current_fraction=0.5, power_loss_w=30.0),
        LossCurvePoint(current_fraction=1.0, power_loss_w=120.0),
        LossCurvePoint(current_fraction=1.25, power_loss_w=187.5),
    )


def _make_device() -> DeviceLibraryEntry:
    return DeviceLibraryEntry(
        entry_id="dev-3wl-001",
        library_version="1.0.0",
        manufacturer="Siemens",
        family="3WL",
        model="3WL1225-3BB37-1AA2",
        rated_current_a=2500.0,
        poles=3,
        width_m=0.400,
        height_m=0.700,
        depth_m=0.350,
        mounting_type=MountingType.DRAW_OUT,
        ventilation_requirement=VentilationRequirement.CLEARANCE_TOP,
        max_ambient_temp_k=313.15,  # 40 °C
        power_loss_curve=_make_loss_curve(),
        loss_confidence=LossConfidence.MANUFACTURER_CERTIFIED,
        references=("Siemens 3WL datasheet rev 2023",),
    )


# ---------------------------------------------------------------------------
# MaterialLibraryEntry
# ---------------------------------------------------------------------------


class TestMaterialLibraryEntry:
    def test_copper_creation(self) -> None:
        mat = _make_material()
        assert mat.name == "Copper (ETP)"
        assert mat.category == MaterialCategory.CONDUCTOR
        assert mat.electrical_resistivity_ohm_m == pytest.approx(1.72e-8, rel=1e-6)

    def test_frozen(self) -> None:
        mat = _make_material()
        with pytest.raises((AttributeError, TypeError)):
            mat.name = "Steel"  # type: ignore[misc]

    def test_non_conductor_missing_electrical(self) -> None:
        mat = MaterialLibraryEntry(
            entry_id="mat-steel-001",
            library_version="1.0.0",
            name="Mild Steel",
            category=MaterialCategory.ENCLOSURE,
            thermal_conductivity_w_per_m_k=50.0,
            density_kg_per_m3=7850.0,
            specific_heat_j_per_kg_k=490.0,
            electrical_resistivity_ohm_m=None,
            temp_coeff_resistance_per_k=None,
            emissivity=0.9,
            max_operating_temp_k=None,
        )
        assert mat.electrical_resistivity_ohm_m is None


# ---------------------------------------------------------------------------
# SurfaceLibraryEntry
# ---------------------------------------------------------------------------


class TestSurfaceLibraryEntry:
    def test_ral7035_paint(self) -> None:
        surface = SurfaceLibraryEntry(
            entry_id="surf-ral7035-001",
            library_version="1.0.0",
            name="RAL 7035 Light Grey Powder Coat",
            emissivity=0.90,
            absorptivity=0.88,
            roughness_um=5.0,
            coating="Polyester powder coat",
            material_ref=None,
        )
        assert surface.emissivity == pytest.approx(0.90)
        assert surface.absorptivity == pytest.approx(0.88)


# ---------------------------------------------------------------------------
# BusbarProfileLibraryEntry
# ---------------------------------------------------------------------------


class TestBusbarProfileLibraryEntry:
    def test_dimensions(self) -> None:
        bp = _make_busbar_profile()
        assert bp.thickness_m == pytest.approx(0.005)
        assert bp.width_m == pytest.approx(0.050)
        assert bp.cross_section_area_m2 == pytest.approx(250e-6, rel=1e-6)

    def test_frozen(self) -> None:
        bp = _make_busbar_profile()
        with pytest.raises((AttributeError, TypeError)):
            bp.width_m = 0.1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeviceLibraryEntry
# ---------------------------------------------------------------------------


class TestDeviceLibraryEntry:
    def test_creation(self) -> None:
        dev = _make_device()
        assert dev.manufacturer == "Siemens"
        assert dev.rated_current_a == pytest.approx(2500.0)
        assert dev.max_ambient_temp_k == pytest.approx(313.15)

    def test_power_loss_at_rated(self) -> None:
        dev = _make_device()
        loss = dev.power_loss_at_rated_w()
        assert loss == pytest.approx(120.0)

    def test_power_loss_at_rated_missing(self) -> None:
        curve = (LossCurvePoint(0.0, 0.0), LossCurvePoint(0.5, 30.0))
        dev = DeviceLibraryEntry(
            entry_id="dev-no-rated",
            library_version="1.0.0",
            manufacturer="Test",
            family="X",
            model="X100",
            rated_current_a=100.0,
            poles=3,
            width_m=0.1,
            height_m=0.2,
            depth_m=0.1,
            mounting_type=MountingType.DIN_RAIL,
            ventilation_requirement=VentilationRequirement.NONE,
            max_ambient_temp_k=313.15,
            power_loss_curve=curve,
            loss_confidence=LossConfidence.ESTIMATED,
        )
        assert dev.power_loss_at_rated_w() is None

    def test_frozen(self) -> None:
        dev = _make_device()
        with pytest.raises((AttributeError, TypeError)):
            dev.manufacturer = "ABB"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FanLibraryEntry
# ---------------------------------------------------------------------------


class TestFanLibraryEntry:
    def test_fan_curve_creation(self) -> None:
        fan = FanLibraryEntry(
            entry_id="fan-ebm-001",
            library_version="1.0.0",
            manufacturer="ebm-papst",
            model="W2S130-AA25-01",
            direction=FanDirection.AXIAL_EXHAUST,
            rated_speed_rpm=2750.0,
            rated_flow_m3_per_s=0.05,
            rated_pressure_pa=35.0,
            rated_power_w=28.0,
            voltage_v=230.0,
            frequency_hz=50.0,
            fan_curve=(
                FanCurvePoint(0.0, 65.0, 15.0, None),
                FanCurvePoint(0.025, 50.0, 22.0, None),
                FanCurvePoint(0.05, 35.0, 28.0, None),
                FanCurvePoint(0.07, 0.0, 30.0, None),
            ),
        )
        assert fan.rated_flow_m3_per_s == pytest.approx(0.05)
        assert len(fan.fan_curve) == 4


# ---------------------------------------------------------------------------
# FilterLibraryEntry
# ---------------------------------------------------------------------------


class TestFilterLibraryEntry:
    def test_filter_creation(self) -> None:
        f = FilterLibraryEntry(
            entry_id="filt-001",
            library_version="1.0.0",
            manufacturer="Rittal",
            model="SK 3173.100",
            dust_class="G4",
            rated_flow_m3_per_s=0.1,
            pressure_drop_pa=12.0,
            loss_coefficient=2.4,
            porosity=0.55,
            initial_efficiency=0.60,
        )
        assert f.pressure_drop_pa == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# ConnectionLibraryEntry
# ---------------------------------------------------------------------------


class TestConnectionLibraryEntry:
    def test_joint_resistance(self) -> None:
        conn = ConnectionLibraryEntry(
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
        assert conn.joint_resistance_ohm == pytest.approx(5e-6)
        assert conn.age_factor == pytest.approx(1.0)

    def test_aged_joint_factor(self) -> None:
        conn = ConnectionLibraryEntry(
            entry_id="conn-aged-001",
            library_version="1.0.0",
            name="Aged bare Cu-Cu joint",
            contact_quality=ContactQuality.BARE_AGED,
            plating=None,
            bolt_size_m=0.012,
            bolt_torque_n_m=None,
            contact_pressure_pa=None,
            joint_resistance_ohm=20e-6,
            resistance_source="USER_ASSUMPTION",
            age_factor=2.5,
        )
        effective = conn.joint_resistance_ohm * conn.age_factor
        assert effective == pytest.approx(50e-6)


# ---------------------------------------------------------------------------
# CableLibraryEntry
# ---------------------------------------------------------------------------


class TestCableLibraryEntry:
    def test_cable_creation(self) -> None:
        cable = CableLibraryEntry(
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
            max_conductor_temp_k=363.15,  # 90 °C
        )
        assert cable.resistance_ohm_per_m == pytest.approx(9.95e-5, rel=1e-4)

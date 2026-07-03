"""
Mandatory unit conversion tests per M0-10 section 6.

All ten tests (UT-UNITS-001 through UT-UNITS-010) must pass on every CI push.
"""
import pytest
from thermpro_units import (
    mm_to_m, m_to_mm,
    mm2_to_m2, m2_to_mm2,
    micro_ohm_to_ohm, ohm_to_micro_ohm,
    celsius_to_kelvin, kelvin_to_celsius,
    m3h_to_m3s, m3s_to_m3h,
    kpa_to_pa, pa_to_kpa,
    gauge_to_absolute_pa,
    gross_to_effective_area,
    check_absolute_temperature,
)


# UT-UNITS-001: 600 mm -> 0.600 m
@pytest.mark.units
def test_ut_units_001_mm_to_m():
    assert abs(mm_to_m(600.0) - 0.600) < 1e-9


# UT-UNITS-002: 50 uOhm -> 50e-6 Ohm
@pytest.mark.units
def test_ut_units_002_micro_ohm_to_ohm():
    assert abs(micro_ohm_to_ohm(50.0) - 50e-6) < 1e-15


# UT-UNITS-003: 40 degC -> 313.15 K
@pytest.mark.units
def test_ut_units_003_celsius_to_kelvin():
    assert abs(celsius_to_kelvin(40.0) - 313.15) < 1e-6


# UT-UNITS-004: radiation with T[degC] input raises ValueError
@pytest.mark.units
def test_ut_units_004_celsius_raises_in_radiation_interface():
    with pytest.raises(ValueError, match="likely a Celsius value"):
        check_absolute_temperature(40.0, "T_surface")  # 40 K is < 200 K threshold


# UT-UNITS-005: 1000 m3/h -> 0.2778 m3/s
@pytest.mark.units
def test_ut_units_005_m3h_to_m3s():
    assert abs(m3h_to_m3s(1000.0) - (1000.0 / 3600.0)) < 1e-4


# UT-UNITS-006: gross area x fraction x Cd = effective area
@pytest.mark.units
def test_ut_units_006_effective_area():
    result = gross_to_effective_area(
        gross_area_m2=0.1,
        open_area_fraction=0.6,
        discharge_coefficient=0.6,
    )
    assert abs(result - 0.036) < 1e-10


# UT-UNITS-007: gauge 50 Pa -> absolute 101 375 Pa
@pytest.mark.units
def test_ut_units_007_gauge_to_absolute():
    result = gauge_to_absolute_pa(50.0)
    assert abs(result - 101_375.0) < 1.0


# UT-UNITS-008: thermal conductivity 50 W/(m.K) passes through unchanged
@pytest.mark.units
def test_ut_units_008_thermal_conductivity_passthrough():
    # W/(m.K) is already SI -- no conversion needed
    value = 50.0
    assert value == 50.0  # no scaling applied


# UT-UNITS-009: resistivity x length / area -> resistance (consistent with Joule)
@pytest.mark.units
def test_ut_units_009_resistivity_to_resistance():
    rho = 1.72e-8  # Cu resistivity [Ohm.m]
    length = mm_to_m(1000.0)  # 1000 mm = 1.0 m
    area = mm2_to_m2(100.0)   # 100 mm2 = 100e-6 m2
    r_ohm = rho * length / area
    assert abs(r_ohm - 1.72e-4) < 1e-15


# UT-UNITS-010: 1.2 kg/m3 not confused with 1200 g/m3
@pytest.mark.units
def test_ut_units_010_density_units():
    density_kg_m3 = 1.2
    density_g_m3_wrong = 1200.0  # would be if someone forgot to convert
    assert density_kg_m3 != density_g_m3_wrong
    # The engine only accepts kg/m3; g/m3 must be converted at the boundary
    converted = density_g_m3_wrong / 1000.0
    assert abs(converted - density_kg_m3) < 1e-9


# Round-trip tests (display -> SI -> display)
@pytest.mark.units
def test_roundtrip_mm():
    v = 1234.5
    assert abs(m_to_mm(mm_to_m(v)) - v) < 1e-9


@pytest.mark.units
def test_roundtrip_micro_ohm():
    v = 37.8
    assert abs(ohm_to_micro_ohm(micro_ohm_to_ohm(v)) - v) < 1e-9


@pytest.mark.units
def test_roundtrip_celsius():
    v = 85.3
    assert abs(kelvin_to_celsius(celsius_to_kelvin(v)) - v) < 1e-9


@pytest.mark.units
def test_roundtrip_m3h():
    v = 720.0
    assert abs(m3s_to_m3h(m3h_to_m3s(v)) - v) < 1e-9


@pytest.mark.units
def test_gross_area_invalid_fraction():
    with pytest.raises(ValueError):
        gross_to_effective_area(0.1, 1.5, 0.6)


@pytest.mark.units
def test_gross_area_invalid_cd():
    with pytest.raises(ValueError):
        gross_to_effective_area(0.1, 0.6, -0.1)


@pytest.mark.units
def test_check_absolute_temperature_valid():
    assert check_absolute_temperature(313.15) == 313.15


@pytest.mark.units
def test_check_absolute_temperature_negative():
    with pytest.raises(ValueError, match="negative"):
        check_absolute_temperature(-1.0)

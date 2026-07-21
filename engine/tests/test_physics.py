"""
Tests for M4 physics modules:
  - conduction (Fourier)
  - natural convection (Churchill-Chu)
  - radiation (gray body — CR-ENG-003 kelvin enforcement)
  - airflow (stack effect, orifice flow)
"""
from __future__ import annotations

import math

import pytest

from thermal_core.conduction.fourier import (
    composite_wall_resistance_k_per_w,
    contact_resistance_k_per_w,
    wall_conductance_w_per_k,
    wall_resistance_k_per_w,
)
from thermal_core.natural_convection.churchill_chu import (
    convection_coefficient,
    convection_coefficient_vertical,
    nusselt_horizontal_plate_down,
    nusselt_horizontal_plate_up,
    nusselt_vertical_plate,
    rayleigh_number,
)
from thermal_core.materials.air_properties import air_at
from thermal_core.radiation.gray_body import (
    STEFAN_BOLTZMANN,
    effective_emissivity_two_surfaces,
    gray_body_heat_flux,
    linearised_radiation_coefficient,
    radiation_conductance_w_per_k,
)
from thermal_core.airflow.network import (
    natural_ventilation_flow,
    orifice_flow_m3_per_s,
    stack_pressure_pa,
)
from thermal_core.snapshot import SurfaceOrientation


# ---------------------------------------------------------------------------
# Conduction
# ---------------------------------------------------------------------------


class TestWallResistance:
    def test_basic_resistance(self) -> None:
        # 2 mm steel plate: L=0.002, k=50, A=1
        R = wall_resistance_k_per_w(0.002, 50.0, 1.0)
        expected = 0.002 / (50.0 * 1.0)
        assert R == pytest.approx(expected)

    def test_zero_thickness_returns_zero(self) -> None:
        R = wall_resistance_k_per_w(0.0, 50.0, 1.0)
        assert R == 0.0

    def test_conductance_is_reciprocal(self) -> None:
        R = wall_resistance_k_per_w(0.01, 1.0, 1.0)
        G = wall_conductance_w_per_k(0.01, 1.0, 1.0)
        assert G == pytest.approx(1.0 / R, rel=1e-9)

    def test_zero_thickness_conductance_is_large(self) -> None:
        G = wall_conductance_w_per_k(0.0, 50.0, 1.0)
        assert G == pytest.approx(1e12)

    def test_negative_thickness_rejected(self) -> None:
        with pytest.raises(ValueError):
            wall_resistance_k_per_w(-0.001, 50.0, 1.0)

    def test_zero_conductivity_rejected(self) -> None:
        with pytest.raises(ValueError):
            wall_resistance_k_per_w(0.01, 0.0, 1.0)

    def test_zero_area_rejected(self) -> None:
        with pytest.raises(ValueError):
            wall_resistance_k_per_w(0.01, 1.0, 0.0)

    def test_composite_wall(self) -> None:
        # Two equal layers in series
        layers = [(0.01, 1.0), (0.01, 1.0)]
        R = composite_wall_resistance_k_per_w(layers, area_m2=1.0)
        expected = 0.01 / 1.0 + 0.01 / 1.0
        assert R == pytest.approx(expected)

    def test_empty_layers_rejected(self) -> None:
        with pytest.raises(ValueError):
            composite_wall_resistance_k_per_w([], area_m2=1.0)

    def test_contact_resistance(self) -> None:
        # r'' = 1e-4 m²·K/W, A = 1 m²
        R = contact_resistance_k_per_w(1e-4, 1.0)
        assert R == pytest.approx(1e-4)


# ---------------------------------------------------------------------------
# Natural Convection
# ---------------------------------------------------------------------------


class TestRayleighNumber:
    def test_zero_delta_t(self) -> None:
        props = air_at(300.0)
        ra = rayleigh_number(props, 0.0, 1.0)
        assert ra == 0.0

    def test_positive_ra_for_positive_delta_t(self) -> None:
        props = air_at(300.0)
        ra = rayleigh_number(props, 10.0, 1.0)
        assert ra > 0

    def test_ra_scales_as_length_cubed(self) -> None:
        props = air_at(300.0)
        ra1 = rayleigh_number(props, 10.0, 1.0)
        ra2 = rayleigh_number(props, 10.0, 2.0)
        assert ra2 == pytest.approx(ra1 * 8.0, rel=1e-6)

    def test_negative_delta_t_treated_as_absolute(self) -> None:
        props = air_at(300.0)
        ra_pos = rayleigh_number(props, 10.0, 1.0)
        ra_neg = rayleigh_number(props, -10.0, 1.0)
        assert ra_pos == pytest.approx(ra_neg)

    def test_zero_length_rejected(self) -> None:
        props = air_at(300.0)
        with pytest.raises(ValueError, match="length_m"):
            rayleigh_number(props, 10.0, 0.0)


class TestNusseltVerticalPlate:
    def test_zero_ra_returns_minimum(self) -> None:
        nu = nusselt_vertical_plate(0.0, 0.71)
        assert nu >= 1.0

    def test_typical_switchboard_ra(self) -> None:
        # Ra ~ 1e8 (typical enclosure) → Nu should be in range [40, 200]
        nu = nusselt_vertical_plate(1e8, 0.71)
        assert 40 < nu < 200

    def test_larger_ra_gives_larger_nu(self) -> None:
        nu_low = nusselt_vertical_plate(1e6, 0.71)
        nu_high = nusselt_vertical_plate(1e10, 0.71)
        assert nu_high > nu_low


class TestNusseltHorizontal:
    def test_heated_up_below_min_ra(self) -> None:
        nu = nusselt_horizontal_plate_up(1e3)
        assert nu == 1.0

    def test_heated_up_regime1(self) -> None:
        nu = nusselt_horizontal_plate_up(1e5)
        expected = 0.54 * (1e5) ** 0.25
        assert nu == pytest.approx(expected)

    def test_heated_up_regime2(self) -> None:
        nu = nusselt_horizontal_plate_up(1e9)
        expected = 0.15 * (1e9) ** (1.0 / 3.0)
        assert nu == pytest.approx(expected)

    def test_heated_down_below_min_ra(self) -> None:
        nu = nusselt_horizontal_plate_down(1e4)
        assert nu == 1.0

    def test_heated_down_formula(self) -> None:
        nu = nusselt_horizontal_plate_down(1e7)
        expected = 0.27 * (1e7) ** 0.25
        assert nu == pytest.approx(expected)


class TestConvectionCoefficient:
    def test_vertical_positive_h(self) -> None:
        h = convection_coefficient_vertical(320.0, 300.0, 2.0)
        assert h > 0

    def test_hot_surface_produces_convection(self) -> None:
        h = convection_coefficient_vertical(350.0, 300.0, 2.0)
        assert h > 2.0  # typical natural convection 2-10 W/(m²·K)

    def test_no_delta_t_gives_nonzero_h(self) -> None:
        # Even with zero ΔT, Nu=1 gives minimum h
        h = convection_coefficient_vertical(300.0, 300.0, 2.0)
        assert h > 0

    def test_orientation_dispatch(self) -> None:
        # All orientations should return positive h
        for orient in SurfaceOrientation:
            h = convection_coefficient(320.0, 300.0, 1.0, orient)
            assert h > 0, f"h=0 for orientation {orient}"


# ---------------------------------------------------------------------------
# Radiation — CR-ENG-003: kelvin enforcement
# ---------------------------------------------------------------------------


class TestRadiation:
    def test_stefan_boltzmann_constant(self) -> None:
        # CODATA 2018 exact value
        assert STEFAN_BOLTZMANN == pytest.approx(5.670374419e-8, rel=1e-9)

    def test_zero_flux_at_equal_temperatures(self) -> None:
        q = gray_body_heat_flux(300.0, 300.0, 0.9)
        assert q == pytest.approx(0.0, abs=1e-6)

    def test_positive_flux_when_surface_hotter(self) -> None:
        q = gray_body_heat_flux(350.0, 300.0, 0.9)
        assert q > 0

    def test_negative_flux_when_surface_cooler(self) -> None:
        q = gray_body_heat_flux(300.0, 350.0, 0.9)
        assert q < 0

    def test_flux_with_blackbody_emissivity(self) -> None:
        # Black body: q = σ(T_s⁴ - T_surr⁴)
        q = gray_body_heat_flux(350.0, 300.0, 1.0)
        expected = STEFAN_BOLTZMANN * (350.0 ** 4 - 300.0 ** 4)
        assert q == pytest.approx(expected, rel=1e-9)

    def test_zero_emissivity_gives_zero_flux(self) -> None:
        q = gray_body_heat_flux(400.0, 300.0, 0.0)
        assert q == pytest.approx(0.0, abs=1e-12)

    def test_cr_eng_003_celsius_raises(self) -> None:
        # CR-ENG-003 guard: T=40 K is unreasonably cold → catches accidental °C usage
        with pytest.raises(ValueError, match="CR-ENG-003"):
            gray_body_heat_flux(40.0, 20.0, 0.9)  # 40°C passed as 40 K

    def test_linearised_h_rad_is_positive(self) -> None:
        h = linearised_radiation_coefficient(350.0, 300.0, 0.9)
        assert h > 0

    def test_linearised_exactly_factored(self) -> None:
        # h_rad × ΔT = q (exact algebraic identity)
        T_s, T_surr, eps = 350.0, 300.0, 0.7
        h_rad = linearised_radiation_coefficient(T_s, T_surr, eps)
        q_linearised = h_rad * (T_s - T_surr)
        q_exact = gray_body_heat_flux(T_s, T_surr, eps)
        assert q_linearised == pytest.approx(q_exact, rel=1e-9)

    def test_conductance_equals_h_times_area(self) -> None:
        G = radiation_conductance_w_per_k(350.0, 300.0, 0.7, 2.0)
        h = linearised_radiation_coefficient(350.0, 300.0, 0.7)
        assert G == pytest.approx(h * 2.0, rel=1e-9)

    def test_effective_emissivity_two_black_surfaces(self) -> None:
        eps_eff = effective_emissivity_two_surfaces(1.0, 1.0)
        assert eps_eff == pytest.approx(1.0)

    def test_effective_emissivity_two_surfaces(self) -> None:
        # 1/eps_eff = 1/0.9 + 1/0.9 - 1
        eps_eff = effective_emissivity_two_surfaces(0.9, 0.9)
        expected = 1.0 / (1.0 / 0.9 + 1.0 / 0.9 - 1.0)
        assert eps_eff == pytest.approx(expected)

    def test_one_zero_emissivity_gives_zero(self) -> None:
        eps_eff = effective_emissivity_two_surfaces(0.0, 0.9)
        assert eps_eff == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Airflow
# ---------------------------------------------------------------------------


class TestStackPressure:
    def test_zero_when_equal_temperatures(self) -> None:
        dp = stack_pressure_pa(300.0, 300.0, 1.0)
        assert dp == pytest.approx(0.0, abs=1e-6)

    def test_positive_when_air_hotter_than_ambient(self) -> None:
        dp = stack_pressure_pa(330.0, 300.0, 1.0)
        assert dp > 0

    def test_negative_when_air_cooler_than_ambient(self) -> None:
        dp = stack_pressure_pa(290.0, 300.0, 1.0)
        assert dp < 0

    def test_scales_with_height(self) -> None:
        dp1 = stack_pressure_pa(320.0, 300.0, 1.0)
        dp2 = stack_pressure_pa(320.0, 300.0, 2.0)
        assert dp2 == pytest.approx(dp1 * 2.0, rel=0.01)

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValueError, match="height_difference_m"):
            stack_pressure_pa(320.0, 300.0, 0.0)

    def test_typical_switchboard_stack_pressure(self) -> None:
        # H=1.5m, ΔT=20K, T_amb=303K → should be ~1-5 Pa
        dp = stack_pressure_pa(323.0, 303.0, 1.5)
        assert 0.5 < dp < 20.0


class TestOrificeFlow:
    def test_zero_pressure_gives_zero_flow(self) -> None:
        q = orifice_flow_m3_per_s(0.0, 0.65, 0.05, 1.2)
        assert q == pytest.approx(0.0)

    def test_positive_flow_for_positive_pressure(self) -> None:
        q = orifice_flow_m3_per_s(5.0, 0.65, 0.05, 1.2)
        assert q > 0

    def test_negative_pressure_same_magnitude(self) -> None:
        q_pos = orifice_flow_m3_per_s(5.0, 0.65, 0.05, 1.2)
        q_neg = orifice_flow_m3_per_s(-5.0, 0.65, 0.05, 1.2)
        assert q_pos == pytest.approx(q_neg)

    def test_orifice_formula_correctness(self) -> None:
        # Q = Cd × A × sqrt(2 × ΔP / ρ)
        Cd, A, dp, rho = 0.65, 0.05, 10.0, 1.2
        expected = Cd * A * math.sqrt(2.0 * dp / rho)
        result = orifice_flow_m3_per_s(dp, Cd, A, rho)
        assert result == pytest.approx(expected, rel=1e-9)

    def test_zero_cd_rejected(self) -> None:
        with pytest.raises(ValueError, match="discharge_coefficient"):
            orifice_flow_m3_per_s(5.0, 0.0, 0.05, 1.2)

    def test_zero_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="free_area_m2"):
            orifice_flow_m3_per_s(5.0, 0.65, 0.0, 1.2)

    def test_zero_density_rejected(self) -> None:
        with pytest.raises(ValueError, match="air_density"):
            orifice_flow_m3_per_s(5.0, 0.65, 0.05, 0.0)


class TestNaturalVentilationFlow:
    def test_hot_air_produces_positive_flow(self) -> None:
        result = natural_ventilation_flow(
            t_air_k=330.0,
            t_ambient_k=303.0,
            inlet_height_m=0.1,
            outlet_height_m=1.9,
            inlet_area_m2=0.05,
            outlet_area_m2=0.05,
            inlet_cd=0.65,
            outlet_cd=0.65,
            compartment_volume_m3=0.5,
        )
        assert result.volumetric_flow_m3_per_s > 0
        assert result.is_buoyancy_driven is True
        assert result.air_changes_per_hour > 0

    def test_equal_temperatures_gives_zero_flow(self) -> None:
        result = natural_ventilation_flow(
            t_air_k=303.0,
            t_ambient_k=303.0,
            inlet_height_m=0.1,
            outlet_height_m=1.9,
            inlet_area_m2=0.05,
            outlet_area_m2=0.05,
            inlet_cd=0.65,
            outlet_cd=0.65,
            compartment_volume_m3=0.5,
        )
        assert result.volumetric_flow_m3_per_s == pytest.approx(0.0, abs=1e-6)
        assert result.is_buoyancy_driven is False

    def test_mass_flow_equals_q_times_rho(self) -> None:
        result = natural_ventilation_flow(
            t_air_k=330.0,
            t_ambient_k=303.0,
            inlet_height_m=0.1,
            outlet_height_m=1.9,
            inlet_area_m2=0.05,
            outlet_area_m2=0.05,
            inlet_cd=0.65,
            outlet_cd=0.65,
            compartment_volume_m3=0.5,
        )
        # Mass flow ≈ Q × ρ_amb
        from thermal_core.materials.air_properties import air_at
        rho = air_at(303.0).density_kg_per_m3
        expected_mdot = result.volumetric_flow_m3_per_s * rho
        assert result.mass_flow_kg_per_s == pytest.approx(expected_mdot, rel=0.05)

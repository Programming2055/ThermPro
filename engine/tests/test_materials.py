"""Tests for M4 air properties and ThermalMaterial."""
from __future__ import annotations

import pytest

from thermal_core.materials.air_properties import air_at, film_temperature_k
from thermal_core.materials.thermal_material import ThermalMaterial

# Standard temperature references
T_0C_K = 273.15
T_20C_K = 293.15
T_40C_K = 313.15
T_60C_K = 333.15


class TestAirAt:
    """Tests for temperature-dependent air properties."""

    def test_returns_air_properties_at_20c(self) -> None:
        props = air_at(T_20C_K)
        assert props.temperature_k == T_20C_K
        assert props.pressure_pa == pytest.approx(101_325.0)

    def test_density_ideal_gas(self) -> None:
        # ρ = P / (R_air × T) = 101325 / (287.058 × 293.15) ≈ 1.204 kg/m³
        props = air_at(T_20C_K)
        assert props.density_kg_per_m3 == pytest.approx(1.204, rel=0.02)

    def test_density_decreases_with_temperature(self) -> None:
        rho_20 = air_at(T_20C_K).density_kg_per_m3
        rho_60 = air_at(T_60C_K).density_kg_per_m3
        assert rho_60 < rho_20

    def test_viscosity_increases_with_temperature(self) -> None:
        mu_20 = air_at(T_20C_K).dynamic_viscosity_pa_s
        mu_60 = air_at(T_60C_K).dynamic_viscosity_pa_s
        assert mu_60 > mu_20

    def test_thermal_conductivity_increases_with_temperature(self) -> None:
        k_20 = air_at(T_20C_K).thermal_conductivity_w_per_m_k
        k_60 = air_at(T_60C_K).thermal_conductivity_w_per_m_k
        assert k_60 > k_20

    def test_prandtl_number_near_0_7_at_20c(self) -> None:
        props = air_at(T_20C_K)
        assert 0.6 <= props.prandtl_number <= 0.8

    def test_thermal_expansion_is_1_over_T(self) -> None:
        props = air_at(T_20C_K)
        expected = 1.0 / T_20C_K
        assert props.thermal_expansion_per_k == pytest.approx(expected, rel=1e-6)

    def test_kinematic_viscosity_equals_mu_over_rho(self) -> None:
        props = air_at(T_20C_K)
        expected = props.dynamic_viscosity_pa_s / props.density_kg_per_m3
        assert props.kinematic_viscosity_m2_per_s == pytest.approx(expected, rel=1e-6)

    def test_thermal_diffusivity_equals_k_over_rho_cp(self) -> None:
        props = air_at(T_20C_K)
        expected = (
            props.thermal_conductivity_w_per_m_k
            / (props.density_kg_per_m3 * props.specific_heat_j_per_kg_k)
        )
        assert props.thermal_diffusivity_m2_per_s == pytest.approx(expected, rel=1e-6)

    def test_custom_pressure(self) -> None:
        rho_std = air_at(T_20C_K, 101_325.0).density_kg_per_m3
        rho_high = air_at(T_20C_K, 200_000.0).density_kg_per_m3
        assert rho_high > rho_std

    def test_zero_temperature_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            air_at(0.0)

    def test_negative_temperature_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            air_at(-10.0)

    def test_very_low_temperature_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside the supported range"):
            air_at(50.0)

    def test_very_high_temperature_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside the supported range"):
            air_at(5000.0)

    def test_zero_pressure_rejected(self) -> None:
        with pytest.raises(ValueError, match="pressure_pa"):
            air_at(T_20C_K, 0.0)

    def test_kinematic_viscosity_at_60c_reference(self) -> None:
        # At 60°C, ν ≈ 18.9×10⁻⁶ m²/s (engineering reference value)
        props = air_at(T_60C_K)
        assert 15e-6 <= props.kinematic_viscosity_m2_per_s <= 22e-6


class TestFilmTemperature:
    def test_midpoint(self) -> None:
        t_film = film_temperature_k(350.0, 300.0)
        assert t_film == pytest.approx(325.0)

    def test_equal_temperatures(self) -> None:
        t_film = film_temperature_k(300.0, 300.0)
        assert t_film == pytest.approx(300.0)


class TestThermalMaterial:
    def _make_steel(self) -> ThermalMaterial:
        return ThermalMaterial(
            material_id="steel-304",
            name="Stainless Steel 304",
            thermal_conductivity_w_per_m_k=16.2,
            density_kg_per_m3=8000.0,
            specific_heat_j_per_kg_k=500.0,
            electrical_resistivity_ohm_m=7.2e-7,
            temp_coeff_resistance_per_k=1.05e-3,
            emissivity=0.6,
            max_operating_temp_k=1673.0,
        )

    def test_valid_material(self) -> None:
        m = self._make_steel()
        assert m.material_id == "steel-304"
        assert m.thermal_conductivity_w_per_m_k == pytest.approx(16.2)

    def test_k_method_constant(self) -> None:
        m = self._make_steel()
        assert m.k(300.0) == pytest.approx(16.2)
        assert m.k(500.0) == pytest.approx(16.2)  # constant in MVP

    def test_rho_method_constant(self) -> None:
        m = self._make_steel()
        assert m.rho(300.0) == pytest.approx(8000.0)

    def test_cp_method_constant(self) -> None:
        m = self._make_steel()
        assert m.cp(300.0) == pytest.approx(500.0)

    def test_rho_e_at_reference_temperature(self) -> None:
        m = self._make_steel()
        # At T_ref (293.15 K), rho_e = rho_e_ref × [1 + α × 0] = rho_e_ref
        rho_e = m.rho_e(293.15)
        assert rho_e == pytest.approx(7.2e-7)

    def test_rho_e_increases_with_temperature(self) -> None:
        m = self._make_steel()
        rho_low = m.rho_e(293.15)
        rho_high = m.rho_e(500.0)
        assert rho_low is not None and rho_high is not None
        assert rho_high > rho_low

    def test_rho_e_none_when_not_specified(self) -> None:
        m = ThermalMaterial(
            material_id="x",
            name="x",
            thermal_conductivity_w_per_m_k=1.0,
            density_kg_per_m3=1000.0,
            specific_heat_j_per_kg_k=1000.0,
        )
        assert m.rho_e(300.0) is None

    def test_emissivity_method(self) -> None:
        m = self._make_steel()
        assert m.eps(300.0) == pytest.approx(0.6)

    def test_emissivity_none_when_not_specified(self) -> None:
        m = ThermalMaterial(
            material_id="x",
            name="x",
            thermal_conductivity_w_per_m_k=1.0,
            density_kg_per_m3=1000.0,
            specific_heat_j_per_kg_k=1000.0,
        )
        assert m.eps(300.0) is None

    def test_zero_conductivity_rejected(self) -> None:
        with pytest.raises(ValueError, match="thermal_conductivity"):
            ThermalMaterial(
                material_id="x",
                name="x",
                thermal_conductivity_w_per_m_k=0.0,
                density_kg_per_m3=1000.0,
                specific_heat_j_per_kg_k=1000.0,
            )

    def test_zero_density_rejected(self) -> None:
        with pytest.raises(ValueError, match="density"):
            ThermalMaterial(
                material_id="x",
                name="x",
                thermal_conductivity_w_per_m_k=1.0,
                density_kg_per_m3=0.0,
                specific_heat_j_per_kg_k=1000.0,
            )

    def test_emissivity_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="emissivity"):
            ThermalMaterial(
                material_id="x",
                name="x",
                thermal_conductivity_w_per_m_k=1.0,
                density_kg_per_m3=1000.0,
                specific_heat_j_per_kg_k=1000.0,
                emissivity=1.1,
            )

    def test_copper_resistivity_temperature_correction(self) -> None:
        # Copper: ρ_e_ref ≈ 1.72e-8 Ω·m at 20°C, α ≈ 3.93e-3 K⁻¹
        copper = ThermalMaterial(
            material_id="cu",
            name="Copper",
            thermal_conductivity_w_per_m_k=400.0,
            density_kg_per_m3=8960.0,
            specific_heat_j_per_kg_k=385.0,
            electrical_resistivity_ohm_m=1.72e-8,
            temp_coeff_resistance_per_k=3.93e-3,
        )
        # At 70°C (343.15 K): ρ_e = 1.72e-8 × [1 + 3.93e-3 × (343.15 - 293.15)]
        #                           = 1.72e-8 × [1 + 3.93e-3 × 50]
        #                           = 1.72e-8 × 1.1965 ≈ 2.058e-8
        expected = 1.72e-8 * (1.0 + 3.93e-3 * 50.0)
        result = copper.rho_e(343.15)
        assert result == pytest.approx(expected, rel=1e-6)

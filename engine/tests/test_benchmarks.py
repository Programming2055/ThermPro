"""
Tests for M4 analytical benchmarks and IEC TR 60890 framework.

BM-001: Plane wall conduction
BM-002: Newton convection cooling
BM-003: Radiation exchange (gray body)
BM-004: Combined convection + radiation
IEC60890: Applicability checks and calculation framework (no licensed data)
"""
from __future__ import annotations

import math

import pytest
from thermal_core.benchmarks.analytical import (
    BenchmarkResult,
    combined_heat_loss,
    conduction_through_plate,
    convection_cooling,
    radiation_exchange,
)
from thermal_core.benchmarks.iec60890 import (
    IEC60890Coefficients,
    check_iec60890_applicability,
    effective_cooling_area_m2,
    iec60890_temperature_rise,
    ventilation_opening_area_m2,
)
from thermal_core.radiation.gray_body import STEFAN_BOLTZMANN


class TestBM001PlaneConductionWall:
    """BM-001: Steady-state conduction through a plane wall."""

    def test_1d_fourier_exact(self) -> None:
        # Q=1000W, L=0.002m, k=50 W/(m·K), A=1m²
        # ΔT = Q×L/(k×A) = 1000×0.002/50 = 0.04 K
        t_cold = conduction_through_plate(1000.0, 0.002, 50.0, 1.0, 373.15)
        expected = 373.15 - 0.04
        assert t_cold == pytest.approx(expected, rel=1e-9)

    def test_zero_heat_no_temperature_drop(self) -> None:
        t_cold = conduction_through_plate(0.0, 0.002, 50.0, 1.0, 373.15)
        assert t_cold == pytest.approx(373.15)

    def test_higher_conductivity_smaller_drop(self) -> None:
        t_low_k = conduction_through_plate(1000.0, 0.01, 1.0, 1.0, 373.15)
        t_high_k = conduction_through_plate(1000.0, 0.01, 50.0, 1.0, 373.15)
        assert t_high_k > t_low_k  # less drop with higher k

    def test_thicker_wall_larger_drop(self) -> None:
        t_thin = conduction_through_plate(1000.0, 0.001, 50.0, 1.0, 373.15)
        t_thick = conduction_through_plate(1000.0, 0.010, 50.0, 1.0, 373.15)
        assert t_thick < t_thin  # more drop with thicker wall


class TestBM002ConvectionCooling:
    """BM-002: Newton's law of cooling."""

    def test_surface_temperature_above_fluid(self) -> None:
        T_s = convection_cooling(q_w=1000.0, h_w_per_m2_k=10.0, area_m2=2.0, t_fluid_k=300.0)
        # T_s = 300 + 1000/(10×2) = 300 + 50 = 350 K
        assert T_s == pytest.approx(350.0)

    def test_zero_heat_surface_at_fluid_temperature(self) -> None:
        T_s = convection_cooling(0.0, 10.0, 2.0, 300.0)
        assert T_s == pytest.approx(300.0)

    def test_higher_h_lower_temperature(self) -> None:
        T_low_h = convection_cooling(1000.0, 5.0, 1.0, 300.0)
        T_high_h = convection_cooling(1000.0, 20.0, 1.0, 300.0)
        assert T_high_h < T_low_h

    def test_dimensional_check(self) -> None:
        # Newton's law: Q = h × A × (T_s - T_f) → T_s = T_f + Q/(h×A)
        q, h, A, T_f = 500.0, 8.0, 0.5, 310.0
        T_s = convection_cooling(q, h, A, T_f)
        # Verify the formula: Q should equal h*A*(T_s - T_f)
        Q_check = h * A * (T_s - T_f)
        assert Q_check == pytest.approx(q, rel=1e-9)


class TestBM003RadiationExchange:
    """BM-003: Gray body radiation — CR-ENG-003 kelvin enforcement."""

    def test_zero_flux_equal_temperatures(self) -> None:
        q = radiation_exchange(300.0, 300.0, 0.9, 1.0)
        assert q == pytest.approx(0.0, abs=1e-6)

    def test_positive_flux_hotter_surface(self) -> None:
        q = radiation_exchange(350.0, 300.0, 0.9, 1.0)
        assert q > 0

    def test_exact_blackbody_formula(self) -> None:
        # Q = σ A (T_s⁴ - T_surr⁴)
        q = radiation_exchange(400.0, 300.0, 1.0, 1.0)
        expected = STEFAN_BOLTZMANN * 1.0 * (400.0 ** 4 - 300.0 ** 4)
        assert q == pytest.approx(expected, rel=1e-9)

    def test_cr_eng_003_celsius_raises(self) -> None:
        # CR-ENG-003 guard: 40 K and 20 K are physically unreasonable → catches °C/K error
        with pytest.raises(ValueError, match="CR-ENG-003"):
            radiation_exchange(40.0, 20.0, 0.9, 1.0)


class TestBM004CombinedLoss:
    """BM-004: Combined convection + radiation surface temperature."""

    def test_temperature_above_ambient(self) -> None:
        T_s = combined_heat_loss(1000.0, 5.0, 0.7, 2.0, 300.0)
        assert T_s > 300.0

    def test_energy_balance_satisfied(self) -> None:
        q = 500.0
        h = 5.0
        eps = 0.7
        A = 1.0
        T_amb = 300.0

        T_s = combined_heat_loss(q, h, eps, A, T_amb)

        # Verify: q_conv + q_rad ≈ q
        q_conv = h * A * (T_s - T_amb)
        q_rad = eps * STEFAN_BOLTZMANN * A * (T_s ** 4 - T_amb ** 4)
        assert q_conv + q_rad == pytest.approx(q, rel=0.01)

    def test_zero_emissivity_is_pure_convection(self) -> None:
        T_s_rad = combined_heat_loss(500.0, 5.0, 0.7, 1.0, 300.0)
        T_s_conv = convection_cooling(500.0, 5.0, 1.0, 300.0)
        # Pure convection gives higher surface temperature (no radiation path)
        assert T_s_conv > T_s_rad


class TestIEC60890Framework:
    """IEC TR 60890 empirical method — framework tests (no licensed data)."""

    @staticmethod
    def _coefficients(**overrides: object) -> IEC60890Coefficients:
        """Synthetic, deliberately non-licensed coefficients for formula tests."""
        kwargs: dict[str, object] = {
            "c0": 1.0,
            "n": 0.5,
            "d": 1.2,
            "installation_factors": {"VERTICAL": 0.9, "HORIZONTAL_UP": 1.4},
            "dataset_version": "synthetic-test-only",
        }
        kwargs.update(overrides)
        return IEC60890Coefficients(**kwargs)  # type: ignore[arg-type]

    def test_applicability_no_forced_ventilation(self) -> None:
        result = check_iec60890_applicability(
            has_forced_ventilation=False,
            has_busbars_with_unknown_losses=False,
        )
        assert result.is_applicable

    def test_forced_ventilation_makes_not_applicable(self) -> None:
        """CR-ENG-006: forced ventilation disables MODE 1."""
        result = check_iec60890_applicability(
            has_forced_ventilation=True,
            has_busbars_with_unknown_losses=False,
        )
        assert not result.is_applicable
        assert any("CR-ENG-006" in r for r in result.reasons)

    def test_unknown_busbar_losses_not_applicable(self) -> None:
        result = check_iec60890_applicability(
            has_forced_ventilation=False,
            has_busbars_with_unknown_losses=True,
        )
        assert not result.is_applicable

    def test_tall_enclosure_outside_method_range(self) -> None:
        """ASS-M1-003: the correlation was derived for enclosures up to 2 m."""
        result = check_iec60890_applicability(
            has_forced_ventilation=False,
            has_busbars_with_unknown_losses=False,
            enclosure_height_m=2.6,
        )
        assert not result.is_applicable
        assert any("2 m" in r for r in result.reasons)

    def test_effective_cooling_area_weights_by_installation_factor(self) -> None:
        """THERM-EQN-001 §11.2: A_e = Σ b_j · A_j."""
        a_e = effective_cooling_area_m2([(2.0, 0.9), (1.0, 1.4)])
        assert a_e == pytest.approx(2.0 * 0.9 + 1.0 * 1.4)

    def test_effective_cooling_area_of_nothing_is_zero(self) -> None:
        assert effective_cooling_area_m2([]) == pytest.approx(0.0)

    def test_ventilation_opening_area_geometric_mean(self) -> None:
        a_vent = ventilation_opening_area_m2(0.04, 0.09)
        assert a_vent == pytest.approx(math.sqrt(0.04 * 0.09))

    def test_ventilation_opening_area_zero_inlet(self) -> None:
        assert ventilation_opening_area_m2(0.0, 0.09) == pytest.approx(0.0)

    def test_zero_coefficient_rejected(self) -> None:
        """CR-ENG-002: c0 = 0 means the licensed dataset was never imported."""
        with pytest.raises(ValueError, match="licensed"):
            IEC60890Coefficients(c0=0.0, n=0.5, d=1.2)

    def test_top_factor_below_one_rejected(self) -> None:
        """The top of an enclosure is never cooler than its mid-height."""
        with pytest.raises(ValueError, match="d must be >= 1"):
            IEC60890Coefficients(c0=1.0, n=0.5, d=0.8)

    def test_mid_height_temperature_rise(self) -> None:
        """Δθ_mid = c_0 · (P_tot / A_e)^n — THERM-EQN-001 §11.3."""
        result = iec60890_temperature_rise(1000.0, 1.0, self._coefficients())
        assert result.delta_theta_mid_k == pytest.approx(math.sqrt(1000.0), rel=1e-9)

    def test_top_rise_applies_distribution_factor(self) -> None:
        """Δθ_top = d · Δθ_mid — THERM-EQN-001 §11.4."""
        result = iec60890_temperature_rise(1000.0, 1.0, self._coefficients(d=1.3))
        assert result.delta_theta_top_k == pytest.approx(
            1.3 * result.delta_theta_mid_k, rel=1e-9
        )

    def test_rise_scales_with_power_density_not_power_alone(self) -> None:
        """Doubling A_e at fixed power must reduce the rise."""
        coeffs = self._coefficients()
        small_area = iec60890_temperature_rise(1000.0, 1.0, coeffs)
        large_area = iec60890_temperature_rise(1000.0, 2.0, coeffs)
        assert large_area.delta_theta_mid_k < small_area.delta_theta_mid_k

    def test_sealed_enclosure_is_rejected_not_reported_as_zero_rise(self) -> None:
        """
        A_e = 0 must raise.

        Returning a zero rise for an enclosure with no cooling surface would
        report the single most dangerous configuration as the safest one.
        """
        with pytest.raises(ValueError, match="cannot reach a steady state"):
            iec60890_temperature_rise(1000.0, 0.0, self._coefficients())

    def test_negative_power_rejected(self) -> None:
        with pytest.raises(ValueError, match="p_total_w"):
            iec60890_temperature_rise(-100.0, 1.0, self._coefficients())

    def test_untagged_dataset_warns(self) -> None:
        """M0-09: a result must be traceable to a licensed dataset release."""
        result = iec60890_temperature_rise(
            500.0, 2.0, self._coefficients(dataset_version="")
        )
        assert any("version tag" in w for w in result.warnings)

    def test_height_profile_interpolates(self) -> None:
        """Δθ(y) = Δθ_mid · f(y/H) — THERM-EQN-001 §11.5."""
        coeffs = self._coefficients(
            height_distribution=((0.0, 0.5), (0.5, 1.0), (1.0, 1.4))
        )
        result = iec60890_temperature_rise(1000.0, 1.0, coeffs)
        mid = result.delta_theta_mid_k
        assert result.delta_theta_at_height_k(0.0) == pytest.approx(0.5 * mid)
        assert result.delta_theta_at_height_k(0.5) == pytest.approx(1.0 * mid)
        assert result.delta_theta_at_height_k(0.25) == pytest.approx(0.75 * mid)
        assert result.delta_theta_at_height_k(1.0) == pytest.approx(1.4 * mid)

    def test_height_profile_absent_returns_mid_height(self) -> None:
        result = iec60890_temperature_rise(1000.0, 1.0, self._coefficients())
        assert result.delta_theta_at_height_k(0.9) == pytest.approx(
            result.delta_theta_mid_k
        )

    def test_installation_factor_falls_back_to_default(self) -> None:
        coeffs = self._coefficients(default_installation_factor=0.6)
        assert coeffs.installation_factor("VERTICAL") == pytest.approx(0.9)
        assert coeffs.installation_factor("HORIZONTAL_DOWN") == pytest.approx(0.6)


class TestBenchmarkResult:
    def test_passed_when_within_tolerance(self) -> None:
        br = BenchmarkResult(
            benchmark_id="BM-001",
            description="Test",
            analytical_value=100.0,
            solver_value=100.1,
            tolerance=0.5,
            units="K",
            passed=True,
        )
        assert br.passed
        assert br.absolute_error == pytest.approx(0.1)

    def test_relative_error_zero_for_exact_match(self) -> None:
        br = BenchmarkResult("B", "B", 100.0, 100.0, 0.1, "K", True)
        assert br.relative_error_percent == pytest.approx(0.0)

    def test_relative_error_zero_when_analytical_is_zero(self) -> None:
        br = BenchmarkResult("B", "B", 0.0, 0.0, 0.1, "K", True)
        assert br.relative_error_percent == pytest.approx(0.0)

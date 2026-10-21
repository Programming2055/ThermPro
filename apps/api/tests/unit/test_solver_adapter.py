"""Unit tests for the M0-03 JSON -> M4 solver adapter."""
import pytest

from thermpro_api.services.solver_adapter import device_power_w


def _dev(**kw):
    base = {"id": "d", "load_current_A": 300.0, "rated_current_A": 600.0,
            "thermal_model": "QUADRATIC", "power_at_rated_W": 100.0}
    return {**base, **kw}


def test_quadratic_scales_with_current_squared():
    assert device_power_w(_dev()) == pytest.approx(25.0)


def test_linear_scales_with_current():
    assert device_power_w(_dev(thermal_model="LINEAR")) == pytest.approx(50.0)


def test_fixed_power_ignores_current():
    assert device_power_w(_dev(thermal_model="FIXED_POWER")) == pytest.approx(100.0)


def test_explicit_coefficients_take_precedence():
    d = _dev(power_coefficient_a=1e-3, power_coefficient_b=0.0, power_coefficient_c=5.0)
    assert device_power_w(d) == pytest.approx(1e-3 * 300**2 + 5.0)

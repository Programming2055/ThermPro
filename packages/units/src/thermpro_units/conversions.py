"""
Unit conversions for thermpro_engine boundary layer.

All engine internals use SI base units (M0-10). Conversions happen
only at input/output boundaries. Do not apply these inside physics modules.
"""

_P_ATM_PA: float = 101_325.0  # Standard atmospheric pressure [Pa]


def mm_to_m(value_mm: float) -> float:
    """Convert millimetres to metres. [mm] -> [m]"""
    return value_mm / 1_000.0


def m_to_mm(value_m: float) -> float:
    """Convert metres to millimetres. [m] -> [mm]"""
    return value_m * 1_000.0


def mm2_to_m2(value_mm2: float) -> float:
    """Convert square millimetres to square metres. [mm2] -> [m2]"""
    return value_mm2 / 1_000_000.0


def m2_to_mm2(value_m2: float) -> float:
    """Convert square metres to square millimetres. [m2] -> [mm2]"""
    return value_m2 * 1_000_000.0


def micro_ohm_to_ohm(value_uohm: float) -> float:
    """Convert micro-ohms to ohms. [uOhm] -> [Ohm]"""
    return value_uohm / 1_000_000.0


def ohm_to_micro_ohm(value_ohm: float) -> float:
    """Convert ohms to micro-ohms. [Ohm] -> [uOhm]"""
    return value_ohm * 1_000_000.0


def celsius_to_kelvin(value_c: float) -> float:
    """Convert Celsius to kelvin. [degC] -> [K]"""
    return value_c + 273.15


def kelvin_to_celsius(value_k: float) -> float:
    """Convert kelvin to Celsius. [K] -> [degC]"""
    return value_k - 273.15


def m3h_to_m3s(value_m3h: float) -> float:
    """Convert cubic metres per hour to cubic metres per second. [m3/h] -> [m3/s]"""
    return value_m3h / 3_600.0


def m3s_to_m3h(value_m3s: float) -> float:
    """Convert cubic metres per second to cubic metres per hour. [m3/s] -> [m3/h]"""
    return value_m3s * 3_600.0


def kpa_to_pa(value_kpa: float) -> float:
    """Convert kilopascals to pascals. [kPa] -> [Pa]"""
    return value_kpa * 1_000.0


def pa_to_kpa(value_pa: float) -> float:
    """Convert pascals to kilopascals. [Pa] -> [kPa]"""
    return value_pa / 1_000.0


def gauge_to_absolute_pa(value_gauge_pa: float, p_atm_pa: float = _P_ATM_PA) -> float:
    """
    Convert gauge pressure to absolute pressure.

    [Pa gauge] -> [Pa absolute]
    P_absolute = P_gauge + P_atm
    """
    return value_gauge_pa + p_atm_pa


def gross_to_effective_area(
    gross_area_m2: float,
    open_area_fraction: float,
    discharge_coefficient: float,
) -> float:
    """
    Compute effective flow area from gross area.

    effective_area_m2 = gross_area_m2 x open_area_fraction x discharge_coefficient

    Args:
        gross_area_m2: Total face area including frame [m2]
        open_area_fraction: Fraction of gross area that is open (0-1) [dimensionless]
        discharge_coefficient: Cd, accounts for vena contracta (0-1) [dimensionless]

    Returns:
        Effective area for orifice flow equation [m2]
    """
    if not 0.0 <= open_area_fraction <= 1.0:
        raise ValueError(f"open_area_fraction must be in [0, 1]; got {open_area_fraction}")
    if not 0.0 <= discharge_coefficient <= 1.0:
        raise ValueError(f"discharge_coefficient must be in [0, 1]; got {discharge_coefficient}")
    return gross_area_m2 * open_area_fraction * discharge_coefficient


def check_absolute_temperature(value: float, name: str = "temperature") -> float:
    """
    Validate that a temperature is in kelvin (absolute).

    Raises ValueError if the value looks like it might be in Celsius (< 0 K is
    physically impossible; < 200 K is below the range of any LV switchboard).

    Args:
        value: Temperature value to validate [K]
        name: Field name for error messages

    Returns:
        The validated value [K]

    Raises:
        ValueError: If value is negative (impossible) or suspiciously low (likely degC)
    """
    if value < 0.0:
        raise ValueError(
            f"{name}={value} K is negative and therefore not a valid absolute temperature. "
            "Did you pass a value in Celsius? Convert with celsius_to_kelvin() first."
        )
    if value < 200.0:
        raise ValueError(
            f"{name}={value} K is below 200 K and likely a Celsius value mistakenly "
            "passed as kelvin. Convert with celsius_to_kelvin() first. "
            "(200 K = -73 degC, below any realistic switchboard temperature.)"
        )
    return value

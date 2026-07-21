"""M4 forced convection — fan curve interpolation and operating point."""
from thermal_core.forced_convection.fan_model import (
    FanOperatingPoint,
    interpolate_fan_curve,
    fan_operating_point,
    fan_mass_flow_kg_per_s,
)

__all__ = [
    "FanOperatingPoint",
    "interpolate_fan_curve",
    "fan_operating_point",
    "fan_mass_flow_kg_per_s",
]

"""M4 forced convection — fan curve interpolation and operating point."""
from thermal_core.forced_convection.fan_model import (
    FanOperatingPoint,
    fan_mass_flow_kg_per_s,
    fan_operating_point,
    interpolate_fan_curve,
)

__all__ = [
    "FanOperatingPoint",
    "fan_mass_flow_kg_per_s",
    "fan_operating_point",
    "interpolate_fan_curve",
]

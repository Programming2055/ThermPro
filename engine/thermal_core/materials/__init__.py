"""M4 materials — temperature-dependent thermophysical properties."""
from thermal_core.materials.air_properties import AirProperties, air_at
from thermal_core.materials.thermal_material import ThermalMaterial

__all__ = ["AirProperties", "air_at", "ThermalMaterial"]

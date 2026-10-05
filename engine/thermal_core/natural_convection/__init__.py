"""M4 natural convection — Churchill-Chu and related correlations."""
from thermal_core.natural_convection.churchill_chu import (
    convection_coefficient,
    convection_coefficient_horizontal,
    convection_coefficient_vertical,
    nusselt_horizontal_plate_down,
    nusselt_horizontal_plate_up,
    nusselt_vertical_plate,
    rayleigh_number,
)

__all__ = [
    "convection_coefficient",
    "convection_coefficient_horizontal",
    "convection_coefficient_vertical",
    "nusselt_horizontal_plate_down",
    "nusselt_horizontal_plate_up",
    "nusselt_vertical_plate",
    "rayleigh_number",
]

"""M4 natural convection — Churchill-Chu and related correlations."""
from thermal_core.natural_convection.churchill_chu import (
    rayleigh_number,
    nusselt_vertical_plate,
    nusselt_horizontal_plate_up,
    nusselt_horizontal_plate_down,
    convection_coefficient_vertical,
    convection_coefficient_horizontal,
    convection_coefficient,
)

__all__ = [
    "rayleigh_number",
    "nusselt_vertical_plate",
    "nusselt_horizontal_plate_up",
    "nusselt_horizontal_plate_down",
    "convection_coefficient_vertical",
    "convection_coefficient_horizontal",
    "convection_coefficient",
]

"""M4 conduction — Fourier wall and component thermal resistances."""
from thermal_core.conduction.fourier import (
    wall_resistance_k_per_w,
    wall_conductance_w_per_k,
    composite_wall_resistance_k_per_w,
    contact_resistance_k_per_w,
)

__all__ = [
    "wall_resistance_k_per_w",
    "wall_conductance_w_per_k",
    "composite_wall_resistance_k_per_w",
    "contact_resistance_k_per_w",
]

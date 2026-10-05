"""M4 conduction — Fourier wall and component thermal resistances."""
from thermal_core.conduction.fourier import (
    composite_wall_resistance_k_per_w,
    contact_resistance_k_per_w,
    wall_conductance_w_per_k,
    wall_resistance_k_per_w,
)

__all__ = [
    "composite_wall_resistance_k_per_w",
    "contact_resistance_k_per_w",
    "wall_conductance_w_per_k",
    "wall_resistance_k_per_w",
]

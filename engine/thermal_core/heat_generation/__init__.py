"""M4 heat generation — compartment-level power aggregation from HeatSourceMap."""
from thermal_core.heat_generation.generation import (
    compartment_heat_generation_w,
    total_heat_generation_w,
    heat_sources_in_compartment,
)

__all__ = [
    "compartment_heat_generation_w",
    "total_heat_generation_w",
    "heat_sources_in_compartment",
]

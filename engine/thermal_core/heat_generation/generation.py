"""
Compartment-level heat generation aggregation.

The M4 zonal solver needs the total power injected into each compartment.
These helper functions extract the relevant heat sources from a HeatSourceMap
and sum them by compartment.

All values in SI base units (CR-ENG-013).
No temperatures computed here — this is pure power aggregation.
"""
from __future__ import annotations

from thermal_core.heat_source import HeatSource, HeatSourceMap
from thermal_core.snapshot import CompartmentSnapshot


def heat_sources_in_compartment(
    heat_source_map: HeatSourceMap,
    compartment: CompartmentSnapshot,
) -> list[HeatSource]:
    """
    Filter HeatSource objects that belong to the given compartment.

    A source that names its compartment directly wins; otherwise the
    compartment's own `heat_source_ids` list is consulted. The back-reference
    is preferred because `HeatSource.source_id` is generated inside the loss
    models, so a caller assembling a CompartmentSnapshot cannot know it in
    advance.
    """
    ids = set(compartment.heat_source_ids)
    return [
        s
        for s in heat_source_map.sources
        if s.compartment_id == compartment.compartment_id
        or (s.compartment_id is None and s.source_id in ids)
    ]


def compartment_heat_generation_w(
    heat_source_map: HeatSourceMap,
    compartment: CompartmentSnapshot,
) -> float:
    """
    Total power loss [W] from all heat sources in a compartment.

    This is the Q term in the compartment energy balance:
        Q = UA_total × (T_air - T_amb)
    """
    sources = heat_sources_in_compartment(heat_source_map, compartment)
    return sum(s.power_loss_w for s in sources)


def total_heat_generation_w(heat_source_map: HeatSourceMap) -> float:
    """Sum of all heat source power in the enclosure [W]."""
    return heat_source_map.total_power_loss_w()

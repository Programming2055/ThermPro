"""
Thermal network nodes for the M4 zonal solver.

Each node represents one thermally-lumped entity:
  - AIR node: one mean air temperature per compartment
  - SURFACE node: one mean temperature per enclosure wall/surface
  - AMBIENT node: fixed boundary (T = T_amb)

The solver builds a conductance matrix G [W/K] and a source vector Q [W]
and solves G × T = Q iteratively, updating nonlinear conductances each iteration.

All temperatures in kelvin (CR-ENG-003).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(str, Enum):
    """Type of thermal network node."""
    AIR = "AIR"          # compartment mean air — unknown temperature
    SURFACE = "SURFACE"  # enclosure surface — unknown temperature
    AMBIENT = "AMBIENT"  # external environment — fixed temperature (boundary)


@dataclass
class ThermalNode:
    """
    One node in the M4 thermal network.

    Mutable during solver iteration (temperature is updated each step).
    The final node temperatures are frozen into NodeTemperature objects.
    """
    node_id: str
    node_type: NodeType
    temperature_k: float       # current temperature estimate [K]
    is_fixed: bool             # True → temperature never updated (boundary condition)
    heat_generation_w: float   # Q injected at this node [W]
    area_m2: Optional[float]   # surface area (for flux calculation) [m²]

    def __post_init__(self) -> None:
        if self.temperature_k <= 0:
            raise ValueError(
                f"ThermalNode.temperature_k must be > 0 K (CR-ENG-003); "
                f"got {self.temperature_k}"
            )
        if self.heat_generation_w < 0:
            raise ValueError(
                f"ThermalNode.heat_generation_w must be >= 0 W; "
                f"got {self.heat_generation_w}"
            )

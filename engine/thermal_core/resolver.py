"""
LibraryResolver — the mandatory abstraction between the library layer and the solver.

M4 non-negotiable rules 2 and 3:
  - The solver NEVER queries the library (rule 2).
  - The resolver layer is MANDATORY (rule 3).

The resolver converts library entry objects (from M3 SQLAlchemy models, or from
any other source) into immutable, solver-ready types.  The solver only receives
resolved types — it never sees UUIDs, SQLAlchemy objects, or raw library data.

Usage (at the API/service layer, NOT in the solver):
    resolver = LibraryResolver()
    thermal_material = resolver.resolve_material(orm_entry)

The resolver itself has no database connection.  Database lookups happen in the
service layer before calling the resolver.  The resolver is a pure transformation.

All values converted to SI base units (CR-ENG-013).
Temperatures converted to kelvin (CR-ENG-003).

This module must NOT import FastAPI, SQLAlchemy, or any HTTP framework (CR-TECH-001).
Instead, it accepts plain Python dicts or dataclass instances from the library layer.
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from thermal_core.libraries import (
    BusbarProfileLibraryEntry,
    CableLibraryEntry,
    ConnectionLibraryEntry,
    DeviceLibraryEntry,
    FanLibraryEntry,
    FilterLibraryEntry,
    MaterialLibraryEntry,
    SurfaceLibraryEntry,
    VentilationOpeningLibraryEntry,
)
from thermal_core.materials.thermal_material import ThermalMaterial


# ---------------------------------------------------------------------------
# Protocol: what the resolver expects from the library layer
# ---------------------------------------------------------------------------


@runtime_checkable
class HasMaterialAttributes(Protocol):
    """Protocol for objects that can be resolved into a ThermalMaterial."""
    domain_entry_id: str
    name: str
    thermal_conductivity_w_per_m_k: float
    density_kg_per_m3: float
    specific_heat_j_per_kg_k: float
    electrical_resistivity_ohm_m: Optional[float]
    temp_coeff_resistance_per_k: Optional[float]
    emissivity: Optional[float]
    max_operating_temp_k: Optional[float]


# ---------------------------------------------------------------------------
# LibraryResolver
# ---------------------------------------------------------------------------


class LibraryResolver:
    """
    Converts library entry objects to immutable solver-ready types.

    This class is intentionally simple: it is a collection of pure transformation
    methods.  No state, no caching, no database connections.

    The service layer (thermpro_api.services) is responsible for fetching the
    correct library entries from the database and passing them here.
    """

    def resolve_material(self, entry: MaterialLibraryEntry) -> ThermalMaterial:
        """
        Convert a MaterialLibraryEntry to an immutable ThermalMaterial.

        The ThermalMaterial is what the solver sees — never the raw library entry.
        """
        return ThermalMaterial(
            material_id=entry.domain_entry_id,
            name=entry.name,
            thermal_conductivity_w_per_m_k=entry.thermal_conductivity_w_per_m_k,
            density_kg_per_m3=entry.density_kg_per_m3,
            specific_heat_j_per_kg_k=entry.specific_heat_j_per_kg_k,
            electrical_resistivity_ohm_m=entry.electrical_resistivity_ohm_m,
            temp_coeff_resistance_per_k=entry.temp_coeff_resistance_per_k,
            emissivity=entry.emissivity,
            max_operating_temp_k=entry.max_operating_temp_k,
        )

    def resolve_material_from_dict(self, data: dict[str, Any]) -> ThermalMaterial:
        """
        Convert a plain dict (e.g. from JSON deserialization) to a ThermalMaterial.

        This allows the resolver to be used without importing M3 library classes,
        keeping the solver package independent of the ORM layer.
        """
        return ThermalMaterial(
            material_id=data["domain_entry_id"],
            name=data["name"],
            thermal_conductivity_w_per_m_k=float(data["thermal_conductivity_w_per_m_k"]),
            density_kg_per_m3=float(data["density_kg_per_m3"]),
            specific_heat_j_per_kg_k=float(data["specific_heat_j_per_kg_k"]),
            electrical_resistivity_ohm_m=data.get("electrical_resistivity_ohm_m"),
            temp_coeff_resistance_per_k=data.get("temp_coeff_resistance_per_k"),
            emissivity=data.get("emissivity"),
            max_operating_temp_k=data.get("max_operating_temp_k"),
        )

    def resolve_surface_emissivity(self, entry: SurfaceLibraryEntry) -> float:
        """Return the emissivity of a surface entry [-]."""
        return entry.emissivity

    def resolve_fan_curve(
        self, entry: FanLibraryEntry
    ) -> list[dict[str, float]]:
        """
        Return the fan curve as a list of plain dicts for the forced-convection model.

        The fan_curve JSONB field is stored as:
          [{flow_m3_per_s, static_pressure_pa, power_w, efficiency}, ...]
        """
        return list(entry.fan_curve)  # type: ignore[arg-type]

    def resolve_device_loss_curve(
        self, entry: DeviceLibraryEntry
    ) -> list[dict[str, float]]:
        """
        Return the power-loss curve as a list of plain dicts.

        Stored as: [{current_fraction, power_loss_w}, ...]
        """
        return list(entry.power_loss_curve)  # type: ignore[arg-type]

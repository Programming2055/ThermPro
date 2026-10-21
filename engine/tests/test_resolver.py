"""LibraryResolver: pure conversion of library entries to solver types (M4 rule 3)."""
from __future__ import annotations

from thermal_core.libraries import MaterialCategory, MaterialLibraryEntry
from thermal_core.resolver import LibraryResolver


def _copper() -> MaterialLibraryEntry:
    return MaterialLibraryEntry(
        entry_id="mat-cu-001",
        library_version="1.0.0",
        name="Copper",
        category=next(iter(MaterialCategory)),
        thermal_conductivity_w_per_m_k=390.0,
        density_kg_per_m3=8960.0,
        specific_heat_j_per_kg_k=385.0,
        electrical_resistivity_ohm_m=1.72e-8,
        temp_coeff_resistance_per_k=0.00393,
        emissivity=0.05,
        max_operating_temp_k=373.15,
    )


def test_resolve_material_copies_every_property_in_si():
    material = LibraryResolver().resolve_material(_copper())
    assert material.material_id == "mat-cu-001"
    assert material.name == "Copper"
    assert material.k(293.15) == 390.0
    assert material.emissivity == 0.05
    assert material.max_operating_temp_k == 373.15


def test_resolution_is_deterministic_and_stateless():
    resolver = LibraryResolver()
    assert resolver.resolve_material(_copper()) == resolver.resolve_material(_copper())

"""
MODE 4 — CFD export/import adapter.

MODE 4 is not a solver. A CFD run happens in an external package, so this
module brackets it:

  * `build_cfd_export_package` turns an InputSnapshot, plus the zonal result
    that seeds it, into a neutral JSON description of the domain, the heat
    sources and the boundary conditions a CFD engineer needs;
  * `import_cfd_field` takes the temperatures that come back and rebuilds a
    ResultSnapshot, so a CFD answer flows through the same compliance,
    reporting and audit path as a MODE 2 or MODE 3 answer.

Running MODE 4 therefore means: solve MODE 2 or MODE 3 for the initial and
boundary conditions, export, run the external solver, import.

The export carries no vendor-specific mesh or solver settings. It states the
geometry, the loads and the boundary conditions in SI units and leaves meshing
and discretisation to the CFD engineer, whose judgement this platform does not
attempt to replace.

All values in SI base units (CR-ENG-013); all temperatures in kelvin
(CR-ENG-003).
"""
from __future__ import annotations

import time
from typing import Any

from thermal_core.heat_generation.generation import heat_sources_in_compartment
from thermal_core.result import (
    CompartmentResult,
    NodeTemperature,
    NodeType,
    ResultSnapshot,
    SolverStatus,
    SolverWarning,
)
from thermal_core.snapshot import InputSnapshot

CFD_EXPORT_FORMAT_VERSION = "1.0"


class CfdImportError(ValueError):
    """Raised when an imported CFD field cannot be reconciled with the model."""


def build_cfd_export_package(
    snapshot: InputSnapshot,
    seed_result: ResultSnapshot | None = None,
) -> dict[str, Any]:
    """
    Build the neutral CFD export package for an enclosure.

    Parameters
    ----------
    snapshot:
        The model to export.
    seed_result:
        A converged MODE 2 or MODE 3 result, used to supply initial conditions.
        Optional: without it the CFD run simply starts from ambient, which
        converges more slowly but gives the same answer.

    Returns
    -------
    dict
        A JSON-serialisable package. Lengths in m, areas in m², power in W,
        temperatures in K.
    """
    geo = snapshot.geometry
    bc = snapshot.boundary_conditions

    seeds: dict[str, float] = {}
    if seed_result is not None:
        for node in seed_result.node_temperatures:
            if node.node_type == NodeType.AIR and node.compartment_id is not None:
                seeds[node.compartment_id] = node.temperature_k

    return {
        "format": "thermpro-cfd-export",
        "format_version": CFD_EXPORT_FORMAT_VERSION,
        "units": "SI base units; lengths m, areas m^2, power W, temperature K",
        "calculation_id": snapshot.calculation_id,
        "schema_version": snapshot.schema_version,
        "library_manifest": dict(snapshot.library_manifest),
        "enclosure": {
            "enclosure_id": geo.enclosure_id,
            "total_height_m": geo.total_height_m,
            "total_external_surface_area_m2": geo.total_external_surface_area_m2,
        },
        "ambient": {
            "temperature_k": bc.ambient_temperature_k,
            "pressure_pa": bc.ambient_pressure_pa,
            "relative_humidity": bc.ambient_relative_humidity,
        },
        "compartments": [
            {
                "compartment_id": c.compartment_id,
                "volume_m3": c.volume_m3,
                "width_m": c.width_m,
                "height_m": c.height_m,
                "depth_m": c.depth_m,
                "initial_air_temperature_k": seeds.get(
                    c.compartment_id, bc.ambient_temperature_k
                ),
                "total_power_w": sum(
                    s.power_loss_w
                    for s in heat_sources_in_compartment(snapshot.heat_source_map, c)
                ),
            }
            for c in geo.compartments
        ],
        "surfaces": [
            {
                "surface_id": s.surface_id,
                "compartment_id": s.compartment_id,
                "area_m2": s.area_m2,
                "orientation": s.orientation.value,
                "emissivity": s.emissivity,
                "internal_emissivity": s.internal_emissivity,
                "thickness_m": s.thickness_m,
                "thermal_conductivity_w_per_m_k": s.thermal_conductivity_w_per_m_k,
                "is_external": s.is_external,
                "is_restricted": s.is_restricted,
                "adjacent_compartment_id": s.adjacent_compartment_id,
                # A restricted surface is adiabatic; everything else exchanges
                # heat with the surroundings by convection and radiation.
                "boundary_condition": "ADIABATIC" if s.is_restricted else "MIXED",
            }
            for s in geo.surfaces
        ],
        "openings": [
            {
                "opening_id": o.opening_id,
                "from_compartment_id": o.from_compartment_id,
                "to_compartment_id": o.to_compartment_id,
                "free_area_m2": o.free_area_m2,
                "discharge_coefficient": o.discharge_coefficient,
                "centroid_height_m": o.centroid_height_m,
                "is_forced": o.is_forced,
                "fan_id": o.fan_id,
                "prescribed_flow_m3_per_s": bc.forced_flow_m3_per_s.get(o.opening_id),
            }
            for o in geo.openings
        ],
        "heat_sources": [
            {
                "source_id": s.source_id,
                "entity_id": s.entity_id,
                "entity_type": s.entity_type.value,
                "name": s.name,
                "compartment_id": s.compartment_id,
                "power_w": s.power_loss_w,
                "location_m": [s.location.x, s.location.y, s.location.z],
                "volume_m3": s.volume_m3,
                "surface_area_m2": s.surface_area_m2,
                "emissivity": s.emissivity,
                "generation_type": s.generation_type.value,
            }
            for s in snapshot.heat_source_map.sources
        ],
    }


def import_cfd_field(
    snapshot: InputSnapshot,
    compartment_air_temperatures_k: dict[str, float],
    entity_temperatures_k: dict[str, float] | None = None,
    *,
    source_label: str,
    converged: bool = True,
) -> ResultSnapshot:
    """
    Rebuild a ResultSnapshot from an external CFD solution.

    Parameters
    ----------
    snapshot:
        The model that was exported.
    compartment_air_temperatures_k:
        Mean air temperature per compartment id [K]. Every compartment in the
        model must be present: a partial field would silently report ambient
        for the compartments the CFD run did not cover.
    entity_temperatures_k:
        Optional entity_id → temperature [K] for device and conductor bodies.
    source_label:
        Identifies the external solver and case, for the audit trail.
    converged:
        Whether the external run converged. False yields NON_CONVERGED, which
        carries the CR-ENG-005 "RESULT INVALID" treatment downstream.

    Raises
    ------
    CfdImportError
        If a compartment is missing from the field, or a temperature is not a
        plausible absolute temperature.
    """
    geo = snapshot.geometry
    t_amb = snapshot.boundary_conditions.ambient_temperature_k
    entity_temperatures_k = entity_temperatures_k or {}

    missing = [
        c.compartment_id
        for c in geo.compartments
        if c.compartment_id not in compartment_air_temperatures_k
    ]
    if missing:
        raise CfdImportError(
            f"The imported CFD field is missing air temperatures for compartments "
            f"{missing}. A partial field cannot be reconciled with the model."
        )

    for label, value in (
        *compartment_air_temperatures_k.items(),
        *entity_temperatures_k.items(),
    ):
        if value <= 0:
            raise CfdImportError(
                f"Imported temperature for {label!r} is {value}; temperatures must be "
                f"absolute, in kelvin (CR-ENG-003)."
            )

    known_entities = {s.entity_id for s in snapshot.heat_source_map.sources}
    unknown = sorted(set(entity_temperatures_k) - known_entities)
    if unknown:
        raise CfdImportError(
            f"The imported CFD field names entities that are not in the model: "
            f"{unknown}."
        )

    nodes: list[NodeTemperature] = []
    comp_results: list[CompartmentResult] = []

    for comp in geo.compartments:
        t_air = compartment_air_temperatures_k[comp.compartment_id]
        sources = heat_sources_in_compartment(snapshot.heat_source_map, comp)
        comp_entity_temps = [
            entity_temperatures_k[s.entity_id]
            for s in sources
            if s.entity_id in entity_temperatures_k
        ]
        nodes.append(
            NodeTemperature(
                node_id=f"air:{comp.compartment_id}",
                node_type=NodeType.AIR,
                temperature_k=t_air,
                heat_generation_w=sum(s.power_loss_w for s in sources),
                net_heat_flux_w_per_m2=None,
                compartment_id=comp.compartment_id,
            )
        )
        comp_results.append(
            CompartmentResult(
                compartment_id=comp.compartment_id,
                mean_air_temperature_k=t_air,
                max_device_temperature_k=max(comp_entity_temps, default=None),
                max_surface_temperature_k=None,
                total_heat_generation_w=sum(s.power_loss_w for s in sources),
                heat_to_ambient_w=sum(s.power_loss_w for s in sources),
            )
        )

    for source in snapshot.heat_source_map.sources:
        if source.entity_id not in entity_temperatures_k:
            continue
        nodes.append(
            NodeTemperature(
                node_id=f"ent:{source.source_id}",
                node_type=NodeType.ENTITY,
                temperature_k=entity_temperatures_k[source.entity_id],
                heat_generation_w=source.power_loss_w,
                net_heat_flux_w_per_m2=None,
                entity_id=source.entity_id,
                name=source.name,
                compartment_id=source.compartment_id,
            )
        )

    nodes.append(
        NodeTemperature(
            node_id="ambient",
            node_type=NodeType.AMBIENT,
            temperature_k=t_amb,
            heat_generation_w=0.0,
            net_heat_flux_w_per_m2=None,
        )
    )

    p_total = snapshot.heat_source_map.total_power_loss_w()
    warnings = [
        SolverWarning(
            code="WARN-MODE4-IMPORTED",
            message=(
                f"Temperatures were imported from the external CFD run {source_label!r}; "
                f"they were not computed by thermpro_engine. The accuracy of this "
                f"result rests on the external model, whose mesh, turbulence model and "
                f"convergence are outside this platform's audit trail."
            ),
        )
    ]
    if not converged:
        warnings.append(
            SolverWarning(
                code="WARN-005-NON-CONVERGED",
                message=(
                    "The external CFD run was reported as not converged. CR-ENG-005: "
                    "the result is marked NON_CONVERGED and must not be used for "
                    "compliance."
                ),
            )
        )

    return ResultSnapshot(
        schema_version=snapshot.schema_version,
        calculation_id=snapshot.calculation_id,
        status=SolverStatus.CONVERGED if converged else SolverStatus.NON_CONVERGED,
        node_temperatures=tuple(nodes),
        compartment_results=tuple(comp_results),
        convergence_trace=(),
        total_heat_generation_w=p_total,
        # The external solver's own energy balance is not visible here, so the
        # dissipation is reported as the imposed load rather than invented.
        total_heat_dissipation_w=p_total,
        energy_balance_error_percent=0.0,
        elapsed_seconds=0.0,
        warnings=tuple(warnings),
    )


def cfd_export_filename(snapshot: InputSnapshot) -> str:
    """Stable filename for an export package, including a UTC timestamp."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"thermpro-cfd-export-{snapshot.calculation_id}-{stamp}.json"

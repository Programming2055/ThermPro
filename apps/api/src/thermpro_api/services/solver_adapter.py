"""
Adapter from the M0-03 JSON InputSnapshot to the M4 solver input.

This is the service-layer boundary: it reads the validated JSON snapshot and
builds the immutable ``thermal_core`` types. The solver itself never sees JSON,
the database, or the library (M4 rules 1-3).

Modelling choices are surfaced in ``Adaptation.assumptions`` so that none is
hidden (M4 rule 8).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thermal_core import (
    BoundaryConditions,
    CalculationMode,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    SolverSettings,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.geometry import Point3D
from thermal_core.heat_source import (
    HeatSource,
    HeatSourceEntityType,
    HeatSourceMap,
    LossCalculationSource,
)
from thermal_core.libraries import LossConfidence

_KELVIN = 273.15
_FACES = ("FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM")
_CONFIDENCE = {
    "HIGH": LossConfidence.MANUFACTURER_CERTIFIED,
    "MEDIUM": LossConfidence.MANUFACTURER_TYPICAL,
    "LOW": LossConfidence.ESTIMATED,
    "UNKNOWN": LossConfidence.ASSUMED_DEFAULT,
}


class AdaptationError(ValueError):
    """The snapshot cannot be solved by the M4 zonal solver as submitted."""


@dataclass(frozen=True)
class Adaptation:
    solver_input: InputSnapshot
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[dict[str, str], ...] = field(default_factory=tuple)


def device_power_w(device: dict[str, Any]) -> float:
    """Device loss at its load current, per the declared thermal model."""
    current = float(device["load_current_A"])
    rated = float(device["rated_current_A"])
    model = device["thermal_model"]
    if model == "FIXED_POWER":
        return float(device["power_at_rated_W"])
    a = device.get("power_coefficient_a")
    b = device.get("power_coefficient_b")
    c = device.get("power_coefficient_c")
    if any(x is not None for x in (a, b, c)):
        return float((a or 0.0) * current**2 + (b or 0.0) * current + (c or 0.0))
    if rated <= 0:
        raise AdaptationError(f"Device {device['id']}: rated_current_A must be > 0.")
    exponent = 1.0 if model == "LINEAR" else 2.0
    return float(device["power_at_rated_W"]) * (current / rated) ** exponent


def build_solver_input(snapshot: dict[str, Any], calculation_id: str) -> Adaptation:
    """Build the M4 InputSnapshot for a MODE_2 submission."""
    enc = snapshot["enclosure"]
    if enc.get("fans") or enc.get("external_openings"):
        raise AdaptationError(
            "Fans and external openings require forced/natural ventilation modelling "
            "(MODE_3), which is not available for MODE_2 submissions."
        )

    h, w, d = (float(enc[k]) for k in ("external_height_m", "external_width_m", "external_depth_m"))
    restricted = set(enc.get("restricted_surfaces", []))
    face_area = {
        "FRONT": (h * w, SurfaceOrientation.VERTICAL),
        "REAR": (h * w, SurfaceOrientation.VERTICAL),
        "LEFT": (h * d, SurfaceOrientation.VERTICAL),
        "RIGHT": (h * d, SurfaceOrientation.VERTICAL),
        "TOP": (w * d, SurfaceOrientation.HORIZONTAL_UP),
        "BOTTOM": (w * d, SurfaceOrientation.HORIZONTAL_DOWN),
    }
    surfaces = tuple(
        SurfaceSnapshot(
            surface_id=f"surf_{face}",
            compartment_id="c_enclosure",
            area_m2=face_area[face][0],
            orientation=face_area[face][1],
            emissivity=float(enc["paint_emissivity"]),
            thickness_m=float(enc["wall_thickness_m"]),
            thermal_conductivity_w_per_m_k=float(enc["wall_thermal_conductivity_W_mK"]),
            is_external=face not in restricted,
        )
        for face in _FACES
    )
    if all(not s.is_external for s in surfaces):
        raise AdaptationError(
            "All six enclosure faces are restricted; there is no heat path to ambient."
        )

    sources: list[HeatSource] = []
    warnings: list[dict[str, str]] = []
    for dev in enc.get("devices", []):
        power = device_power_w(dev)
        if power < 0:
            raise AdaptationError(f"Device {dev['id']}: computed loss is negative ({power} W).")
        confidence = dev["data_confidence"]
        if confidence in ("LOW", "UNKNOWN"):
            warnings.append({
                "code": "DATA_CONFIDENCE_LOW",
                "message": f"Device '{dev.get('name', dev['id'])}' loss data confidence is "
                           f"{confidence}. No margin has been applied (DR-009).",
                "entity_id": dev["id"],
            })
        sources.append(HeatSource(
            source_id=f"hs_{dev['id']}",
            entity_type=HeatSourceEntityType.DEVICE,
            entity_id=dev["id"],
            power_loss_w=power,
            location=Point3D(
                x=float(dev["position_x_m"]), y=float(dev["position_y_m"]),
                z=float(dev["position_z_m"]),
            ),
            volume_m3=None,
            surface_area_m2=None,
            confidence=_CONFIDENCE[confidence],
            calculation_source=(
                LossCalculationSource.MANUFACTURER_RATED
                if dev["thermal_model"] == "FIXED_POWER"
                else LossCalculationSource.MANUFACTURER_CURVE
            ),
            library_ref=dev.get("device_library_id"),
            operating_current_a=float(dev["load_current_A"]),
            current_fraction=float(dev["load_current_A"]) / float(dev["rated_current_A"]),
        ))

    if enc.get("busbar_runs"):
        warnings.append({
            "code": "BUSBAR_LOSSES_NOT_MODELLED",
            "message": "Busbar runs were submitted but busbar losses are not part of this "
                       "calculation; the result under-estimates total dissipation.",
            "entity_id": enc["id"],
        })

    compartment = CompartmentSnapshot(
        compartment_id="c_enclosure",
        volume_m3=h * w * d,
        height_m=h,
        width_m=w,
        depth_m=d,
        surface_ids=tuple(s.surface_id for s in surfaces),
        heat_source_ids=tuple(s.source_id for s in sources),
    )
    geometry = GeometrySnapshot(
        enclosure_id=enc["id"],
        total_height_m=h,
        total_external_surface_area_m2=sum(s.area_m2 for s in surfaces if s.is_external),
        compartments=(compartment,),
        surfaces=surfaces,
        openings=(),
    )

    sc = snapshot["service_conditions"]
    ss = snapshot["solver_settings"]
    # Worst case: the maximum ambient is used, not the 24 h average.
    boundary = BoundaryConditions(
        ambient_temperature_k=float(sc["ambient_temperature_max_C"]) + _KELVIN,
        ambient_pressure_pa=101_325.0,
        ambient_relative_humidity=float(sc["relative_humidity_max_percent"]) / 100.0,
        forced_flow_m3_per_s={},
    )
    settings = SolverSettings(
        calculation_mode=CalculationMode(snapshot["mode"]),
        max_iterations=int(ss["max_inner_iterations"]),
        convergence_tolerance_k=float(ss["convergence_T_K"]),
        relaxation_factor=float(ss["relaxation_factor"]),
    )

    manifest = {k: str(v.get("version", "")) for k, v in snapshot["library_manifest"].items()}
    inline_only = not manifest
    if inline_only:
        # CR-TECH-002 needs a manifest; with no pins the inputs are user-supplied inline.
        manifest = {"inline_inputs": "no-library-pinned"}
    solver_input = InputSnapshot(
        schema_version=snapshot["schema_version"],
        library_manifest=manifest,
        calculation_id=calculation_id,
        geometry=geometry,
        heat_source_map=HeatSourceMap(
            enclosure_id=enc["id"], sources=sources, library_manifest=manifest
        ),
        boundary_conditions=boundary,
        solver_settings=settings,
    )
    assumptions = (
        "Single well-mixed air zone for the whole enclosure (zonal model, one mean air temp.).",
        "Ambient is the maximum service ambient temperature (worst case), not the 24 h average.",
        "Internal volume is taken equal to the external envelope volume.",
        "Ambient pressure is 101325 Pa; altitude is not applied.",
        f"{len(restricted)} restricted face(s) are treated as adiabatic.",
    ) + (
        ("No library release is pinned: device losses are user-supplied inline values.",)
        if inline_only else ()
    )
    return Adaptation(solver_input, assumptions, tuple(warnings))

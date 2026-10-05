"""
A worked reference model, as an M0-03 InputSnapshot document.

A 2 m cubicle with a device chamber over a cable chamber, a copper main
busbar with one bolted joint, an outgoing cable, and louvres low at the front
and high on the roof: the smallest model that still exercises every part of
the contract. Every value is one a panel builder would actually supply.

It exists in the shipped package, not in a test directory, because the API
layer, the contract tests and the demo fixtures all need the *same* model. Two
copies of a reference model drift, and a drifted reference proves nothing.

The licensed IEC TR 60890 coefficients are deliberately absent (CR-ENG-002):
a MODE_1 run on this model fails until an administrator imports them.
"""
from __future__ import annotations

import uuid
from typing import Any

CABLE_CHAMBER_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.cable-chamber"))
DEVICE_CHAMBER_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.device-chamber"))
ENCLOSURE_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.enclosure"))
ACB_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.acb"))
MCCB_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.mccb"))
BUSBAR_RUN_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.busbar-run"))
BUSBAR_SEGMENT_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.busbar-segment"))
BUSBAR_JOINT_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.busbar-joint"))
CONDUCTOR_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.conductor"))
FAN_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.fan"))
PARTITION_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.partition"))

ENCLOSURE_WIDTH_M = 0.8
ENCLOSURE_DEPTH_M = 0.6
ENCLOSURE_HEIGHT_M = 2.0
WALL_THICKNESS_M = 0.002

AMBIENT_C = 35.0
AMBIENT_K = AMBIENT_C + 273.15


def _pin(name: str) -> dict[str, Any]:
    return {"name": name, "version": "1.0.0", "content_hash_sha256": "a" * 64}


def compartments() -> list[dict[str, Any]]:
    """A cable chamber below a device chamber, split by a perforated plate."""
    t = WALL_THICKNESS_M
    return [
        {
            "id": CABLE_CHAMBER_ID,
            "name": "Cable chamber",
            "position_x_m": t,
            "position_y_m": t,
            "position_z_m": t,
            "width_m": ENCLOSURE_WIDTH_M - 2 * t,
            "depth_m": ENCLOSURE_DEPTH_M - 2 * t,
            "height_m": 1.0 - t,
            "partitions": [
                {
                    "id": PARTITION_ID,
                    "orientation": "HORIZONTAL",
                    "position_m": 1.0,
                    "thickness_m": 0.0015,
                    "thermal_conductivity_W_mK": 50.0,
                    "is_perforated": True,
                    "open_area_fraction": 0.1,
                }
            ],
        },
        {
            "id": DEVICE_CHAMBER_ID,
            "name": "Device chamber",
            "position_x_m": t,
            "position_y_m": t,
            "position_z_m": 1.0,
            "width_m": ENCLOSURE_WIDTH_M - 2 * t,
            "depth_m": ENCLOSURE_DEPTH_M - 2 * t,
            "height_m": ENCLOSURE_HEIGHT_M - 1.0 - t,
        },
    ]


def devices() -> list[dict[str, Any]]:
    return [
        {
            "id": ACB_ID,
            "name": "Incomer ACB",
            "device_library_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "lib.acb")),
            "compartment_id": DEVICE_CHAMBER_ID,
            "position_x_m": 0.4,
            "position_y_m": 0.3,
            "position_z_m": 1.5,
            "load_current_A": 1200.0,
            "rated_current_A": 1600.0,
            "thermal_model": "QUADRATIC",
            "power_at_rated_W": 250.0,
            "data_confidence": "HIGH",
            "max_operating_temp_C": 105.0,
            "surface_area_m2": 0.9,
            "volume_m3": 0.05,
            "emissivity": 0.85,
        },
        {
            "id": MCCB_ID,
            "name": "Outgoing MCCB",
            "device_library_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "lib.mccb")),
            "compartment_id": CABLE_CHAMBER_ID,
            "position_x_m": 0.4,
            "position_y_m": 0.3,
            "position_z_m": 0.4,
            "load_current_A": 300.0,
            "rated_current_A": 400.0,
            "thermal_model": "FIXED_POWER",
            "power_at_rated_W": 60.0,
            "data_confidence": "MEDIUM",
            "surface_area_m2": 0.25,
        },
    ]


def busbar_runs() -> list[dict[str, Any]]:
    return [
        {
            "id": BUSBAR_RUN_ID,
            "name": "Main busbar",
            "phase_label": "L1",
            "current_A": 1200.0,
            "cross_section_m2": 0.0012,
            "width_m": 0.1,
            "thickness_m": 0.012,
            "resistivity_ohm_m": 1.72e-8,
            "temp_coefficient_1_K": 0.00393,
            "temp_ref_C": 20.0,
            "emissivity": 0.7,
            "compartment_id": DEVICE_CHAMBER_ID,
            "segments": [
                {
                    "id": BUSBAR_SEGMENT_ID,
                    "start_x_m": 0.05,
                    "start_y_m": 0.5,
                    "start_z_m": 1.8,
                    "end_x_m": 0.75,
                    "end_y_m": 0.5,
                    "end_z_m": 1.8,
                    "length_m": 0.7,
                    "k_ac_factor": None,
                    "k_ac_source": None,
                }
            ],
            "joints": [
                {
                    "id": BUSBAR_JOINT_ID,
                    "segment_a_id": BUSBAR_SEGMENT_ID,
                    "segment_b_id": None,
                    "position_x_m": 0.75,
                    "position_y_m": 0.5,
                    "position_z_m": 1.8,
                    "joint_condition": "NEW_VALIDATED",
                    "contact_resistance_ref_ohm": 5.0e-6,
                    "contact_resistance_source": "MANUFACTURER",
                    "temp_coefficient_contact_1_K": 0.00393,
                    "temp_ref_C": 20.0,
                    "data_confidence": "HIGH",
                    "surface_area_m2": 0.02,
                }
            ],
        }
    ]


def conductors() -> list[dict[str, Any]]:
    return [
        {
            "id": CONDUCTOR_ID,
            "name": "Outgoing cable",
            "conductor_library_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "lib.cable")),
            "length_m": 2.5,
            "current_A": 300.0,
            "resistance_ohm_per_m": 1.21e-4,
            "temp_coefficient_1_K": 0.00393,
            "temp_ref_C": 20.0,
            "rated_current_A": 400.0,
            "surface_area_m2": 0.35,
            "emissivity": 0.9,
            "compartment_id": CABLE_CHAMBER_ID,
        }
    ]


def external_openings() -> list[dict[str, Any]]:
    """Low inlet at the front, high outlet on the roof — a stack by design."""
    return [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.inlet")),
            "opening_type": "LOUVRE",
            "mounting_surface": "FRONT",
            "gross_area_m2": 0.05,
            "open_area_fraction": 0.6,
            "discharge_coefficient": 0.6,
            "position_x_m": 0.4,
            "position_y_m": 0.0,
            "position_z_m": 0.15,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "thermpro.test.outlet")),
            "opening_type": "VENTILATION_SLOT",
            "mounting_surface": "TOP",
            "gross_area_m2": 0.06,
            "open_area_fraction": 0.6,
            "discharge_coefficient": 0.6,
            "position_x_m": 0.4,
            "position_y_m": 0.3,
            "position_z_m": ENCLOSURE_HEIGHT_M,
        },
    ]


def fan(operating_state: str = "RUNNING_FORWARD") -> dict[str, Any]:
    return {
        "id": FAN_ID,
        "ventilation_device_library_id": str(
            uuid.uuid5(uuid.NAMESPACE_DNS, "lib.fan")
        ),
        "position_x_m": 0.4,
        "position_y_m": 0.3,
        "position_z_m": 1.95,
        "orientation": "OUTLET",
        "mounting_surface": "TOP",
        "operating_state": operating_state,
        "free_area_m2": 0.02,
        "motor_power_loss_W": 18.0,
        "fan_curve": [
            {"flow_m3_s": 0.00, "static_pressure_Pa": 90.0, "power_W": 20.0},
            {"flow_m3_s": 0.05, "static_pressure_Pa": 70.0, "power_W": 24.0},
            {"flow_m3_s": 0.10, "static_pressure_Pa": 40.0, "power_W": 26.0},
            {"flow_m3_s": 0.15, "static_pressure_Pa": 0.0, "power_W": 22.0},
        ],
    }


def m003_document(
    mode: str = "MODE_2",
    *,
    with_fan: bool = False,
    fan_state: str = "RUNNING_FORWARD",
    with_compartments: bool = True,
) -> dict[str, Any]:
    """A complete, schema-valid M0-03 document."""
    enclosure: dict[str, Any] = {
        "id": ENCLOSURE_ID,
        "name": "Main LV board, section 1",
        "external_height_m": ENCLOSURE_HEIGHT_M,
        "external_width_m": ENCLOSURE_WIDTH_M,
        "external_depth_m": ENCLOSURE_DEPTH_M,
        "wall_thickness_m": WALL_THICKNESS_M,
        "wall_thermal_conductivity_W_mK": 50.0,
        "paint_emissivity": 0.9,
        "restricted_surfaces": ["REAR"],
        "devices": devices(),
        "busbar_runs": busbar_runs(),
        "conductors": conductors(),
        "external_openings": external_openings(),
    }
    if with_compartments:
        enclosure["compartments"] = compartments()
    else:
        for device in enclosure["devices"]:
            device["compartment_id"] = None
        enclosure["busbar_runs"][0]["compartment_id"] = None
        enclosure["conductors"][0]["compartment_id"] = None
    if with_fan:
        enclosure["fans"] = [fan(fan_state)]

    return {
        "schema_version": "1.0",
        "mode": mode,
        "standard_profile": ["IEC_61439_2"],
        "library_manifest": {
            "material_library": _pin("MaterialLibrary"),
            "device_library": _pin("DeviceLibrary"),
            "conductor_library": _pin("ConductorLibrary"),
        },
        "service_conditions": {
            "ambient_temperature_max_C": AMBIENT_C,
            "ambient_temperature_avg_24h_C": 30.0,
            "relative_humidity_max_percent": 50.0,
            "altitude_m": 0.0,
            "pollution_degree": 3,
        },
        "enclosure": enclosure,
        "solver_settings": {
            "max_outer_iterations": 50,
            "max_inner_iterations": 300,
            "convergence_T_K": 0.01,
            "convergence_flow_fraction": 0.005,
            "convergence_power_fraction": 0.005,
            "energy_imbalance_limit": 0.01,
            "mass_imbalance_limit": 0.005,
            "relaxation_factor": 0.6,
        },
    }

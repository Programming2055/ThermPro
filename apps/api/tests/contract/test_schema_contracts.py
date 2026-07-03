"""
Schema contract tests.

These tests verify that the bundled M0-03 and M0-04 JSON schemas correctly
accept valid payloads and reject out-of-scope content. They are marked
@pytest.mark.contract and always run in CI (no database required).
"""
import pytest
from thermpro_schemas import SchemaValidationError, validate_input_snapshot


@pytest.mark.contract
def test_m003_schema_rejects_arc_flash_mode():
    """ARC_FLASH mode must be absent from the mode enum (DR-008)."""
    data = {
        "schema_version": "1.0",
        "mode": "ARC_FLASH",
        "standard_profile": ["IEC_61439_2"],
        "library_manifest": {},
        "service_conditions": {
            "ambient_temperature_max_C": 40.0,
            "ambient_temperature_avg_24h_C": 35.0,
            "relative_humidity_max_percent": 95.0,
            "altitude_m": 0.0,
            "pollution_degree": 2,
        },
        "enclosure": {
            "id": "00000000-0000-0000-0000-000000000001",
            "external_height_m": 2.0,
            "external_width_m": 0.8,
            "external_depth_m": 0.6,
            "wall_thickness_m": 0.002,
            "wall_thermal_conductivity_W_mK": 50.0,
            "paint_emissivity": 0.9,
            "restricted_surfaces": [],
        },
        "solver_settings": {
            "max_outer_iterations": 50,
            "max_inner_iterations": 100,
            "convergence_T_K": 0.1,
            "convergence_flow_fraction": 0.005,
            "convergence_power_fraction": 0.005,
            "energy_imbalance_limit": 0.01,
            "mass_imbalance_limit": 0.005,
            "relaxation_factor": 0.7,
        },
    }
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


@pytest.mark.contract
def test_m003_schema_rejects_ul_standards():
    """UL_891 and UL_1558 must not appear in the standard_profile enum (DR-007)."""
    base = {
        "schema_version": "1.0",
        "mode": "MODE_1",
        "standard_profile": ["UL_891"],
        "library_manifest": {},
        "service_conditions": {
            "ambient_temperature_max_C": 40.0,
            "ambient_temperature_avg_24h_C": 35.0,
            "relative_humidity_max_percent": 95.0,
            "altitude_m": 0.0,
            "pollution_degree": 2,
        },
        "enclosure": {
            "id": "00000000-0000-0000-0000-000000000001",
            "external_height_m": 2.0,
            "external_width_m": 0.8,
            "external_depth_m": 0.6,
            "wall_thickness_m": 0.002,
            "wall_thermal_conductivity_W_mK": 50.0,
            "paint_emissivity": 0.9,
            "restricted_surfaces": [],
        },
        "solver_settings": {
            "max_outer_iterations": 50,
            "max_inner_iterations": 100,
            "convergence_T_K": 0.1,
            "convergence_flow_fraction": 0.005,
            "convergence_power_fraction": 0.005,
            "energy_imbalance_limit": 0.01,
            "mass_imbalance_limit": 0.005,
            "relaxation_factor": 0.7,
        },
    }
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(base)


@pytest.mark.contract
def test_m003_fan_operating_states_schema_contract():
    """The schema must accept all six canonical fan states and reject unknown ones."""
    from thermpro_schemas import validate_input_snapshot

    valid_states = [
        "RUNNING_FORWARD",
        "STOPPED_FREE_FLOW",
        "STOPPED_WITH_DAMPER",
        "FAILED_OPEN",
        "FAILED_BLOCKED",
        "REVERSE_FLOW_ESTIMATED",
    ]

    base = {
        "schema_version": "1.0",
        "mode": "MODE_3",
        "standard_profile": ["IEC_61439_2"],
        "library_manifest": {
            "material_library": {
                "name": "MaterialLibrary",
                "version": "1.0.0",
                "content_hash_sha256": "a" * 64,
            }
        },
        "service_conditions": {
            "ambient_temperature_max_C": 40.0,
            "ambient_temperature_avg_24h_C": 35.0,
            "relative_humidity_max_percent": 95.0,
            "altitude_m": 0.0,
            "pollution_degree": 2,
        },
        "enclosure": {
            "id": "00000000-0000-0000-0000-000000000001",
            "external_height_m": 2.0,
            "external_width_m": 0.8,
            "external_depth_m": 0.6,
            "wall_thickness_m": 0.002,
            "wall_thermal_conductivity_W_mK": 50.0,
            "paint_emissivity": 0.9,
            "restricted_surfaces": [],
            "fans": [],
        },
        "solver_settings": {
            "max_outer_iterations": 50,
            "max_inner_iterations": 100,
            "convergence_T_K": 0.1,
            "convergence_flow_fraction": 0.005,
            "convergence_power_fraction": 0.005,
            "energy_imbalance_limit": 0.01,
            "mass_imbalance_limit": 0.005,
            "relaxation_factor": 0.7,
        },
    }

    import copy

    for state in valid_states:
        data = copy.deepcopy(base)
        data["enclosure"]["fans"] = [
            {
                "id": "00000000-0000-0000-0000-000000000010",
                "ventilation_device_library_id": "00000000-0000-0000-0000-000000000020",
                "position_x_m": 0.1,
                "position_y_m": 0.1,
                "position_z_m": 0.1,
                "orientation": "INLET",
                "mounting_surface": "FRONT",
                "operating_state": state,
            }
        ]
        validate_input_snapshot(data)  # must not raise

    # Invalid state
    bad_data = copy.deepcopy(base)
    bad_data["enclosure"]["fans"] = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "ventilation_device_library_id": "00000000-0000-0000-0000-000000000020",
            "position_x_m": 0.1,
            "position_y_m": 0.1,
            "position_z_m": 0.1,
            "orientation": "INLET",
            "mounting_surface": "FRONT",
            "operating_state": "OPERATING",  # old boolean-era value — invalid
        }
    ]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(bad_data)

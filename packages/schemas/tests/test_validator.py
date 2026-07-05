"""
Schema contract tests for InputSnapshot and ResultSnapshot validation.

Tests verify that the validator correctly accepts valid payloads
and rejects malformed, incomplete, or out-of-scope inputs.
"""
import pytest
from thermpro_schemas import SchemaValidationError, validate_input_snapshot


# ---------------------------------------------------------------------------
# Minimal valid InputSnapshot fixture
# ---------------------------------------------------------------------------

_VALID_LIBRARY_PIN = {
    "name": "MaterialLibrary",
    "version": "1.0.0",
    "content_hash_sha256": "a" * 64,
}

_VALID_INPUT: dict = {
    "schema_version": "1.0",
    "mode": "MODE_1",
    "standard_profile": ["IEC_61439_2"],
    "library_manifest": {
        "material_library": _VALID_LIBRARY_PIN,
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
        "restricted_surfaces": ["BOTTOM"],
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


def _make_input(**overrides):
    """Return a deep copy of _VALID_INPUT with top-level key overrides."""
    import copy
    data = copy.deepcopy(_VALID_INPUT)
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_input_snapshot_passes():
    """A fully valid InputSnapshot should not raise."""
    validate_input_snapshot(_VALID_INPUT)


def test_missing_schema_version_rejected():
    """schema_version is mandatory; omitting it must raise SchemaValidationError."""
    data = _make_input()
    del data["schema_version"]
    with pytest.raises(SchemaValidationError, match="schema_version"):
        validate_input_snapshot(data)


def test_wrong_schema_version_rejected():
    """An unsupported schema_version must be rejected."""
    data = _make_input(schema_version="99.0")
    with pytest.raises(SchemaValidationError, match="Unsupported schema_version"):
        validate_input_snapshot(data)


def test_missing_library_manifest_rejected():
    """library_manifest is required per M0-03; omitting it must raise."""
    data = _make_input()
    del data["library_manifest"]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_invalid_mode_arc_flash_rejected():
    """ARC_FLASH is explicitly removed from scope (DR-008)."""
    data = _make_input(mode="ARC_FLASH")
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_invalid_fan_state_rejected():
    """A fan with an unknown operating_state must fail schema validation."""
    import copy
    data = copy.deepcopy(_VALID_INPUT)
    data["enclosure"]["fans"] = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "ventilation_device_library_id": "00000000-0000-0000-0000-000000000020",
            "position_x_m": 0.1,
            "position_y_m": 0.1,
            "position_z_m": 0.1,
            "orientation": "INLET",
            "mounting_surface": "FRONT",
            "operating_state": "BROKEN",  # invalid
        }
    ]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_valid_fan_states_accepted():
    """All six canonical fan operating states must be accepted by the schema."""
    import copy

    valid_states = [
        "RUNNING_FORWARD",
        "STOPPED_FREE_FLOW",
        "STOPPED_WITH_DAMPER",
        "FAILED_OPEN",
        "FAILED_BLOCKED",
        "REVERSE_FLOW_ESTIMATED",
    ]
    for state in valid_states:
        data = copy.deepcopy(_VALID_INPUT)
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


def test_invalid_joint_condition_rejected():
    """An unknown joint_condition must fail schema validation."""
    import copy
    data = copy.deepcopy(_VALID_INPUT)
    data["enclosure"]["busbar_runs"] = [
        {
            "id": "00000000-0000-0000-0000-000000000030",
            "phase_label": "L1",
            "current_A": 400.0,
            "cross_section_m2": 0.001,
            "width_m": 0.05,
            "thickness_m": 0.02,
            "resistivity_ohm_m": 1.72e-8,
            "temp_coefficient_1_K": 0.00393,
            "temp_ref_C": 20.0,
            "emissivity": 0.9,
            "segments": [
                {
                    "id": "00000000-0000-0000-0000-000000000031",
                    "start_x_m": 0.0,
                    "start_y_m": 0.0,
                    "start_z_m": 0.0,
                    "end_x_m": 0.0,
                    "end_y_m": 1.0,
                    "end_z_m": 0.0,
                    "length_m": 1.0,
                }
            ],
            "joints": [
                {
                    "id": "00000000-0000-0000-0000-000000000040",
                    "segment_a_id": "00000000-0000-0000-0000-000000000031",
                    "position_x_m": 0.0,
                    "position_y_m": 0.5,
                    "position_z_m": 0.0,
                    "joint_condition": "CORRODED",  # invalid
                    "temp_coefficient_contact_1_K": 0.00393,
                    "temp_ref_C": 20.0,
                    "data_confidence": "HIGH",
                }
            ],
        }
    ]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_k_ac_factor_below_one_rejected():
    """k_ac_factor must be >= 1.0 per schema (DR-003)."""
    import copy
    data = copy.deepcopy(_VALID_INPUT)
    data["enclosure"]["busbar_runs"] = [
        {
            "id": "00000000-0000-0000-0000-000000000030",
            "phase_label": "L1",
            "current_A": 400.0,
            "cross_section_m2": 0.001,
            "width_m": 0.05,
            "thickness_m": 0.02,
            "resistivity_ohm_m": 1.72e-8,
            "temp_coefficient_1_K": 0.00393,
            "temp_ref_C": 20.0,
            "emissivity": 0.9,
            "segments": [
                {
                    "id": "00000000-0000-0000-0000-000000000031",
                    "start_x_m": 0.0,
                    "start_y_m": 0.0,
                    "start_z_m": 0.0,
                    "end_x_m": 0.0,
                    "end_y_m": 1.0,
                    "end_z_m": 0.0,
                    "length_m": 1.0,
                    "k_ac_factor": 0.8,  # invalid: must be >= 1.0
                    "k_ac_source": "MANUFACTURER",
                }
            ],
        }
    ]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)

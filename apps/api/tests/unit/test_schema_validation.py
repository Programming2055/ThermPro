"""Unit tests for schema validation in thermpro_schemas."""
import pytest
from thermpro_schemas import SchemaValidationError, validate_input_snapshot


_BASE_INPUT = {
    "schema_version": "1.0",
    "mode": "MODE_1",
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


def test_valid_input_accepted():
    validate_input_snapshot(_BASE_INPUT)


def test_missing_schema_version():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    del data["schema_version"]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_unsupported_schema_version():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    data["schema_version"] = "2.0"
    with pytest.raises(SchemaValidationError, match="Unsupported"):
        validate_input_snapshot(data)


def test_missing_mode():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    del data["mode"]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_missing_library_manifest():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    del data["library_manifest"]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_invalid_mode_arc_flash():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    data["mode"] = "ARC_FLASH"
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_invalid_standard_profile_ul891():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    data["standard_profile"] = ["UL_891"]
    with pytest.raises(SchemaValidationError):
        validate_input_snapshot(data)


def test_schema_validation_error_has_errors_list():
    import copy
    data = copy.deepcopy(_BASE_INPUT)
    del data["mode"]
    exc = None
    try:
        validate_input_snapshot(data)
    except SchemaValidationError as e:
        exc = e
    assert exc is not None
    assert isinstance(exc.errors, list)

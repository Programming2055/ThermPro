"""Integration tests for the full calculation submission flow."""
import pytest

_VALID_INPUT = {
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schema_validation_rejects_arc_flash(client):
    """Submitting ARC_FLASH mode must be rejected at the schema validation step."""
    import copy

    # Create a project first
    proj_resp = await client.post("/api/v1/projects", json={"name": "Test"})
    project_id = proj_resp.json()["id"]

    bad_input = copy.deepcopy(_VALID_INPUT)
    bad_input["mode"] = "ARC_FLASH"

    resp = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": bad_input},
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schema_validation_rejects_missing_schema_version(client):
    """Submitting without schema_version is rejected before schema validation."""
    import copy

    proj_resp = await client.post("/api/v1/projects", json={"name": "Test2"})
    project_id = proj_resp.json()["id"]

    bad_input = copy.deepcopy(_VALID_INPUT)
    del bad_input["schema_version"]

    resp = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": bad_input},
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manifest_validation_rejects_unapproved_library(client):
    """
    If the library_manifest references a library that is not APPROVED,
    the submission must be rejected.

    In this test the MaterialLibrary 1.0.0 has not been created in the DB,
    so the manifest validation step will fail.
    """
    proj_resp = await client.post("/api/v1/projects", json={"name": "Test3"})
    project_id = proj_resp.json()["id"]

    resp = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": _VALID_INPUT},
    )
    # Manifest validation fails because no approved release exists
    assert resp.status_code == 422
    body = resp.json()
    assert "Library manifest validation" in body["detail"]["message"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health endpoint must return 200 in all conditions."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body

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


def _mode2(load_a: float = 400.0, **overrides):
    import copy

    snap = copy.deepcopy(_VALID_INPUT)
    snap["mode"] = "MODE_2"
    snap["library_manifest"] = {}
    snap["enclosure"]["devices"] = [{
        "id": "00000000-0000-0000-0000-0000000000d1",
        "name": "MCCB-1",
        "device_library_id": "manual",
        "position_x_m": 0.2, "position_y_m": 0.2, "position_z_m": 1.0,
        "load_current_A": load_a,
        "rated_current_A": 630.0,
        "thermal_model": "QUADRATIC",
        "power_at_rated_W": 200.0,
        "data_confidence": "HIGH",
    }]
    for k, v in overrides.items():
        snap["solver_settings" if k in snap["solver_settings"] else "enclosure"][k] = v
    return snap


async def _submit(client, snap):
    proj = await client.post("/api/v1/projects", json={"name": "Solver"})
    return await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": proj.json()["id"], "input_snapshot": snap},
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode2_runs_solver_and_stores_result(client):
    resp = await _submit(client, _mode2())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["engine_version"]
    res = body["result_snapshot"]
    assert res["status"] == "CONVERGED" and res["is_valid"] is True
    # 200 W * (400/630)^2 = 80.6 W of device loss, ambient 40 C -> air hotter than ambient
    assert res["total_heat_generation_w"] == pytest.approx(200.0 * (400 / 630) ** 2)
    air = res["compartment_results"][0]["mean_air_temperature_k"]
    assert air > 40.0 + 273.15
    assert res["assumptions"]
    fetched = await client.get(f"/api/v1/calculation-runs/{body['id']}")
    assert fetched.json()["result_snapshot"] == res


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode2_higher_load_gives_higher_temperature(client):
    lo = (await _submit(client, _mode2(200.0))).json()["result_snapshot"]
    hi = (await _submit(client, _mode2(600.0))).json()["result_snapshot"]
    t = lambda r: r["compartment_results"][0]["mean_air_temperature_k"]  # noqa: E731
    assert t(hi) > t(lo)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode2_non_converged_is_never_valid(client):
    """CR-ENG-005: iteration limit hit -> NON_CONVERGED, invalid, flagged."""
    resp = await _submit(client, _mode2(max_inner_iterations=1, convergence_T_K=1e-9))
    body = resp.json()
    assert body["status"] == "NON_CONVERGED"
    assert body["result_snapshot"]["is_valid"] is False
    assert body["rejection_reason"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode2_low_confidence_warning_is_surfaced(client):
    snap = _mode2()
    snap["enclosure"]["devices"][0]["data_confidence"] = "UNKNOWN"
    body = (await _submit(client, snap)).json()
    codes = [w["code"] for w in body["result_snapshot"]["warnings"]]
    assert "DATA_CONFIDENCE_LOW" in codes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode2_all_faces_restricted_is_rejected(client):
    snap = _mode2()
    snap["enclosure"]["restricted_surfaces"] = ["FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM"]
    resp = await _submit(client, snap)
    assert resp.status_code == 422
    assert "heat path" in resp.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mode1_still_not_implemented(client):
    import copy

    snap = copy.deepcopy(_VALID_INPUT)
    snap["library_manifest"] = {}
    resp = await _submit(client, snap)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "ENGINE_NOT_IMPLEMENTED"
    assert resp.json()["result_snapshot"] is None

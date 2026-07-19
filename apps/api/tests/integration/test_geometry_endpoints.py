"""M2 geometry endpoint integration tests.

Tests cover:
- Create / list enclosures
- Create compartment, partition, external opening, internal opening
- Create device placement, busbar placement
- Run geometry validation (enclosure.validated audit event)
- Audit event recorded on every write

Requires a running PostgreSQL instance (provided by CI service container).
Run with: pytest apps/api/tests/integration/ -m integration
"""
from __future__ import annotations

import pytest  # noqa: F401 — used via @pytest.mark decorators

# ─── Shared fixtures ──────────────────────────────────────────────────────────


async def _create_project(client, name: str = "Geo Test Project") -> str:
    resp = await client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


_ENCLOSURE_BODY = {
    "name": "MCC Panel A",
    "external_width_m": 0.6,
    "external_height_m": 2.0,
    "external_depth_m": 0.4,
    "internal_width_m": 0.556,
    "internal_height_m": 1.95,
    "internal_depth_m": 0.356,
    "wall_thickness_m": 0.002,
    "installation_type": "FLOOR_STANDING",
    "ip_rating": "IP54",
}


async def _create_enclosure(client, project_id: str, name: str = "MCC Panel A") -> str:
    body = {**_ENCLOSURE_BODY, "name": name}
    resp = await client.post(f"/api/v1/projects/{project_id}/enclosures", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ─── Enclosure ────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_enclosure_returns_201(client):
    project_id = await _create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/enclosures", json=_ENCLOSURE_BODY
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "MCC Panel A"
    assert body["external_width_m"] == 0.6
    assert body["internal_width_m"] == 0.556
    assert body["coordinate_system_version"] == "1.0"
    assert body["project_id"] == project_id
    assert "id" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_enclosures_returns_created(client):
    project_id = await _create_project(client, "ListEncTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.get(f"/api/v1/projects/{project_id}/enclosures")
    assert resp.status_code == 200
    ids = [e["id"] for e in resp.json()]
    assert enc_id in ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_enclosure_by_id(client):
    project_id = await _create_project(client, "GetEncTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.get(f"/api/v1/enclosures/{enc_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == enc_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_nonexistent_enclosure_returns_404(client):
    resp = await client.get("/api/v1/enclosures/00000000-0000-0000-0000-000000009999")
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_enclosure_rejects_zero_dimension(client):
    project_id = await _create_project(client, "BadDimTest")
    bad_body = {**_ENCLOSURE_BODY, "external_width_m": 0.0}
    resp = await client.post(
        f"/api/v1/projects/{project_id}/enclosures", json=bad_body
    )
    assert resp.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_enclosure_returns_204(client):
    project_id = await _create_project(client, "DelEncTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.delete(f"/api/v1/enclosures/{enc_id}")
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/enclosures/{enc_id}")
    assert resp2.status_code == 404


# ─── Compartment ──────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_compartment_returns_201(client):
    project_id = await _create_project(client, "CompTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/compartments",
        json={
            "name": "Device Bay 1",
            "compartment_type": "DEVICE_CHAMBER",
            "position_x_m": 0.0,
            "position_y_m": 0.0,
            "position_z_m": 0.0,
            "width_m": 0.5,
            "height_m": 0.9,
            "depth_m": 0.35,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Device Bay 1"
    assert body["compartment_type"] == "DEVICE_CHAMBER"
    assert body["enclosure_id"] == enc_id
    assert body["width_m"] == 0.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_compartments(client):
    project_id = await _create_project(client, "ListCompTest")
    enc_id = await _create_enclosure(client, project_id)
    await client.post(
        f"/api/v1/enclosures/{enc_id}/compartments",
        json={"name": "Bay A", "width_m": 0.5, "height_m": 0.9, "depth_m": 0.35},
    )
    resp = await client.get(f"/api/v1/enclosures/{enc_id}/compartments")
    assert resp.status_code == 200
    assert any(c["name"] == "Bay A" for c in resp.json())


# ─── Partition ────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_partition_returns_201(client):
    project_id = await _create_project(client, "PartTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/partitions",
        json={
            "orientation": "VERTICAL_YZ",
            "position_x_m": 0.278,
            "position_y_m": 0.0,
            "position_z_m": 0.0,
            "width_m": 0.356,
            "height_m": 1.95,
            "thickness_m": 0.002,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["orientation"] == "VERTICAL_YZ"
    assert body["enclosure_id"] == enc_id
    assert body["width_m"] == 0.356


# ─── ExternalOpening ─────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_external_opening_returns_201(client):
    project_id = await _create_project(client, "ExtOpenTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/external-openings",
        json={
            "name": "Bottom inlet louvre",
            "position_x_m": 0.1,
            "position_y_m": 0.05,
            "width_m": 0.3,
            "height_m": 0.08,
            "open_area_fraction": 0.6,
            "discharge_coefficient": 0.61,
            "direction": "INLET",
            "elevation_m": 0.05,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Bottom inlet louvre"
    assert body["open_area_fraction"] == 0.6
    assert body["enclosure_id"] == enc_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_external_opening_rejects_fraction_out_of_range(client):
    project_id = await _create_project(client, "ExtOpenBadTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/external-openings",
        json={
            "position_x_m": 0.1,
            "position_y_m": 0.05,
            "width_m": 0.3,
            "height_m": 0.08,
            "open_area_fraction": 1.5,
        },
    )
    assert resp.status_code == 422


# ─── InternalOpening ─────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_internal_opening_returns_201(client):
    project_id = await _create_project(client, "IntOpenTest")
    enc_id = await _create_enclosure(client, project_id)

    part_resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/partitions",
        json={
            "orientation": "VERTICAL_YZ",
            "position_x_m": 0.278,
            "position_y_m": 0.0,
            "position_z_m": 0.0,
            "width_m": 0.356,
            "height_m": 1.95,
        },
    )
    assert part_resp.status_code == 201
    partition_id = part_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/partitions/{partition_id}/internal-openings",
        json={
            "name": "Cable gland aperture",
            "position_x_m": 0.0,
            "position_y_m": 0.1,
            "width_m": 0.15,
            "height_m": 0.1,
            "open_area_fraction": 0.7,
            "discharge_coefficient": 0.61,
            "direction": "BIDIRECTIONAL",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["partition_id"] == partition_id
    assert body["open_area_fraction"] == 0.7


# ─── DevicePlacement ─────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_device_placement_returns_201(client):
    project_id = await _create_project(client, "DevTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/device-placements",
        json={
            "name": "Circuit breaker CB-01",
            "position_x_m": 0.05,
            "position_y_m": 0.1,
            "position_z_m": 0.05,
            "width_m": 0.1,
            "height_m": 0.15,
            "depth_m": 0.08,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Circuit breaker CB-01"
    assert body["enclosure_id"] == enc_id
    assert body["width_m"] == 0.1


# ─── BusbarPlacement ─────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_busbar_placement_returns_201(client):
    project_id = await _create_project(client, "BusbarTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/busbar-placements",
        json={
            "name": "L1 main busbar",
            "position_x_m": 0.05,
            "position_y_m": 1.8,
            "position_z_m": 0.05,
            "width_m": 0.05,
            "thickness_m": 0.006,
            "length_m": 0.45,
            "phase_designation": "L1",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "L1 main busbar"
    assert body["phase_designation"] == "L1"
    assert body["enclosure_id"] == enc_id


# ─── Geometry validation ─────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_clean_enclosure_returns_zero_issues(client):
    project_id = await _create_project(client, "ValidClean")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enclosure_id"] == enc_id
    assert body["issue_count"] == 0
    assert body["error_count"] == 0
    assert body["issues"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_enclosure_detects_geo002_error(client):
    """Compartment placed outside enclosure internal envelope raises GEO-002."""
    project_id = await _create_project(client, "ValidGeo002")
    enc_id = await _create_enclosure(client, project_id)

    # Place compartment at x=0.5 with width=0.2 → x1=0.7 > internal_width=0.556
    await client.post(
        f"/api/v1/enclosures/{enc_id}/compartments",
        json={
            "name": "Oversized Bay",
            "position_x_m": 0.5,
            "position_y_m": 0.0,
            "position_z_m": 0.0,
            "width_m": 0.2,
            "height_m": 0.9,
            "depth_m": 0.35,
        },
    )

    resp = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error_count"] >= 1
    rule_ids = [i["rule_id"] for i in body["issues"]]
    assert "GEO-002" in rule_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_detects_geo003_duplicate_compartment_names(client):
    """Two compartments with the same name raise GEO-003."""
    project_id = await _create_project(client, "ValidGeo003")
    enc_id = await _create_enclosure(client, project_id)

    for x in (0.0, 0.1):
        await client.post(
            f"/api/v1/enclosures/{enc_id}/compartments",
            json={"name": "Same Name", "position_x_m": x, "position_y_m": 0.0,
                  "position_z_m": 0.0, "width_m": 0.08, "height_m": 0.5, "depth_m": 0.3},
        )

    resp = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    body = resp.json()
    rule_ids = [i["rule_id"] for i in body["issues"]]
    assert "GEO-003" in rule_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_clears_and_replaces_existing_issues(client):
    """Re-running validation replaces prior unresolved issues, not accumulates."""
    project_id = await _create_project(client, "ValidReplace")
    enc_id = await _create_enclosure(client, project_id)

    # First run: no issues
    r1 = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert r1.json()["issue_count"] == 0

    # Add an invalid compartment
    await client.post(
        f"/api/v1/enclosures/{enc_id}/compartments",
        json={"name": "Bad", "position_x_m": 0.9, "position_y_m": 0.0,
              "position_z_m": 0.0, "width_m": 0.2, "height_m": 0.5, "depth_m": 0.3},
    )

    # Second run: GEO-002 appears
    r2 = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert r2.json()["error_count"] >= 1

    # Third run (nothing changed): issue count identical, not doubled
    r3 = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert r3.json()["issue_count"] == r2.json()["issue_count"]


# ─── Audit events ─────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enclosure_create_records_audit_event(client, test_engine):
    """enclosure.created audit event is persisted on POST /enclosures."""
    project_id = await _create_project(client, "AuditEncTest")
    enc_id = await _create_enclosure(client, project_id, name="Audit Enc")

    import uuid as _uuid
    enc_uuid = _uuid.UUID(enc_id)

    async with test_engine.connect() as conn:
        from sqlalchemy import text
        rows = (await conn.execute(
            text(
                "SELECT action, entity_type, entity_id FROM audit_events "
                "WHERE action = 'enclosure.created' AND entity_id = :eid"
            ),
            {"eid": enc_uuid},
        )).fetchall()

    assert len(rows) == 1
    assert rows[0].action == "enclosure.created"
    assert rows[0].entity_type == "Enclosure"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compartment_create_records_audit_event(client, test_engine):
    """compartment.created audit event is persisted on POST /compartments."""
    project_id = await _create_project(client, "AuditCompTest")
    enc_id = await _create_enclosure(client, project_id)

    comp_resp = await client.post(
        f"/api/v1/enclosures/{enc_id}/compartments",
        json={"name": "Audit Bay", "width_m": 0.3, "height_m": 0.9, "depth_m": 0.3},
    )
    assert comp_resp.status_code == 201
    comp_id = comp_resp.json()["id"]

    import uuid as _uuid
    comp_uuid = _uuid.UUID(comp_id)

    async with test_engine.connect() as conn:
        from sqlalchemy import text
        rows = (await conn.execute(
            text(
                "SELECT action FROM audit_events "
                "WHERE action = 'compartment.created' AND entity_id = :eid"
            ),
            {"eid": comp_uuid},
        )).fetchall()

    assert len(rows) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_geometry_records_audit_event(client, test_engine):
    """enclosure.validated audit event is persisted on POST /validate."""
    project_id = await _create_project(client, "AuditValidTest")
    enc_id = await _create_enclosure(client, project_id)

    resp = await client.post(f"/api/v1/enclosures/{enc_id}/validate")
    assert resp.status_code == 200

    import uuid as _uuid
    enc_uuid = _uuid.UUID(enc_id)

    async with test_engine.connect() as conn:
        from sqlalchemy import text
        rows = (await conn.execute(
            text(
                "SELECT action, entity_type FROM audit_events "
                "WHERE action = 'enclosure.validated' AND entity_id = :eid"
            ),
            {"eid": enc_uuid},
        )).fetchall()

    assert len(rows) == 1
    assert rows[0].entity_type == "Enclosure"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enclosure_delete_records_audit_event(client, test_engine):
    """enclosure.deleted audit event is persisted on DELETE /enclosures/{id}."""
    project_id = await _create_project(client, "AuditDelTest")
    enc_id = await _create_enclosure(client, project_id, name="To Be Deleted")

    resp = await client.delete(f"/api/v1/enclosures/{enc_id}")
    assert resp.status_code == 204

    import uuid as _uuid
    enc_uuid = _uuid.UUID(enc_id)

    async with test_engine.connect() as conn:
        from sqlalchemy import text
        rows = (await conn.execute(
            text(
                "SELECT action FROM audit_events "
                "WHERE action = 'enclosure.deleted' AND entity_id = :eid"
            ),
            {"eid": enc_uuid},
        )).fetchall()

    assert len(rows) == 1

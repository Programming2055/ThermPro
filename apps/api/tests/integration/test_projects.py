"""Integration tests for project CRUD endpoints."""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_retrieve_project(client):
    """Creating a project and then retrieving it by ID should return consistent data."""
    # Create
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Test Switchboard MCC-01", "description": "Integration test project"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Test Switchboard MCC-01"
    project_id = body["id"]

    # Retrieve
    resp2 = await client.get(f"/api/v1/projects/{project_id}")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["id"] == project_id
    assert body2["name"] == "Test Switchboard MCC-01"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_projects(client):
    """Listing projects returns at least the ones we created."""
    resp = await client.post("/api/v1/projects", json={"name": "MCC-ListTest"})
    assert resp.status_code == 201

    resp2 = await client.get("/api/v1/projects")
    assert resp2.status_code == 200
    names = [p["name"] for p in resp2.json()]
    assert "MCC-ListTest" in names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_nonexistent_project_returns_404(client):
    """Fetching a non-existent project UUID returns 404."""
    resp = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404

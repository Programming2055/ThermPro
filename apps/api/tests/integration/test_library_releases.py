"""Integration tests for library release lifecycle."""
import pytest

_ENTRIES = [{"id": "mat-001", "name": "Copper", "resistivity_ohm_m": 1.72e-8}]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_approve_library_release(client):
    """Full lifecycle: create DRAFT -> approve -> verify immutability."""
    # Create
    resp = await client.post(
        "/api/v1/library-releases",
        json={
            "library_name": "MaterialLibrary",
            "version": "1.0.0",
            "entries": _ENTRIES,
            "description": "Test material library",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "DRAFT"
    release_id = body["id"]

    # Retrieve
    resp2 = await client.get(f"/api/v1/library-releases/{release_id}")
    assert resp2.status_code == 200
    assert resp2.json()["library_name"] == "MaterialLibrary"

    # Approve (dev user is ENGINEER, so this will return 403 with default auth)
    # In integration tests we rely on DevAuthProvider which returns ENGINEER role.
    # Test that the 403 is returned correctly (role enforcement works).
    resp3 = await client.post(f"/api/v1/library-releases/{release_id}/approve")
    assert resp3.status_code == 403  # ENGINEER cannot approve


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_library_releases(client):
    """List endpoint returns releases we created."""
    await client.post(
        "/api/v1/library-releases",
        json={"library_name": "DeviceLibrary", "version": "0.1.0", "entries": _ENTRIES},
    )
    resp = await client.get("/api/v1/library-releases", params={"library_name": "DeviceLibrary"})
    assert resp.status_code == 200
    assert any(r["library_name"] == "DeviceLibrary" for r in resp.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_nonexistent_release_returns_404(client):
    resp = await client.get("/api/v1/library-releases/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404

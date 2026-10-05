"""
Integration tests for the full calculate-and-retrieve flow.

Submit an M0-03 document, execute it, fetch the M0-04 result back, and check
that what comes out of the API is what the engine produced. Requires a running
PostgreSQL instance.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest
from thermal_core.reference_model import m003_document
from thermpro_schemas import validate_result_snapshot

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _project(client: Any, name: str = "Execution test") -> str:
    response = await client.post("/api/v1/projects", json={"name": name})
    assert response.status_code in (200, 201), response.text
    project_id: str = response.json()["id"]
    return project_id


def _document(mode: str = "MODE_2", **kwargs: Any) -> dict[str, Any]:
    """The reference model. Its pins resolve via the approved_libraries fixture."""
    return m003_document(mode, **kwargs)


async def test_submit_leaves_the_run_pending(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    response = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": _document()},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["has_result"] is False
    assert body["engine_version"] is None


async def test_execute_produces_a_retrievable_result(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    submitted = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": _document()},
    )
    run_id = submitted.json()["id"]

    executed = await client.post(f"/api/v1/calculation-runs/{run_id}/execute")
    assert executed.status_code == 200, executed.text
    assert executed.json()["status"] == "COMPLETED"
    assert executed.json()["has_result"] is True

    fetched = await client.get(f"/api/v1/calculation-runs/{run_id}/result")
    assert fetched.status_code == 200
    result = fetched.json()
    validate_result_snapshot(result)
    assert result["run_id"] == run_id
    assert result["status"] == "CONVERGED"
    assert result["temperatures"]["entities"]
    assert fetched.headers["X-Result-Checksum-SHA256"]


async def test_submit_and_execute_in_one_request(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    response = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": _document(),
            "execute": True,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["has_result"] is True


async def test_result_is_404_before_execution(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    submitted = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": _document()},
    )
    run_id = submitted.json()["id"]
    response = await client.get(f"/api/v1/calculation-runs/{run_id}/result")
    assert response.status_code == 404
    assert "execute" in response.json()["detail"]


async def test_a_completed_run_is_not_re_executed(client: Any, approved_libraries: Any) -> None:
    """Its result is part of the audit record (CR-ENG-012 in spirit)."""
    project_id = await _project(client)
    submitted = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": _document(),
            "execute": True,
        },
    )
    run_id = submitted.json()["id"]
    again = await client.post(f"/api/v1/calculation-runs/{run_id}/execute")
    assert again.status_code == 409


async def test_input_snapshot_is_returned_verbatim(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    document = _document()
    submitted = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": document},
    )
    run_id = submitted.json()["id"]
    await client.post(f"/api/v1/calculation-runs/{run_id}/execute")

    fetched = await client.get(f"/api/v1/calculation-runs/{run_id}/input")
    assert fetched.status_code == 200
    # Running a calculation must not alter the question it answered.
    assert fetched.json() == document
    assert fetched.headers["X-Input-Checksum-SHA256"] == (
        submitted.json()["input_checksum_sha256"]
    )


async def test_mode_1_fails_without_the_licensed_dataset(
    client: Any, approved_libraries: Any
) -> None:
    """CR-ENG-002, end to end: a clear failure, not an invented answer."""
    project_id = await _project(client)
    response = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": _document("MODE_1"),
            "execute": True,
        },
    )
    assert response.status_code == 201
    run_id = response.json()["id"]
    assert response.json()["status"] == "FAILED"

    result = (await client.get(f"/api/v1/calculation-runs/{run_id}/result")).json()
    assert result["status"] == "FAILED"
    assert "CR-ENG-002" in result["failure_reason"]


async def test_non_converged_run_is_stored_and_served(client: Any, approved_libraries: Any) -> None:
    """CR-ENG-005: the UI needs the result to put RESULT INVALID on."""
    project_id = await _project(client)
    document = _document()
    document["solver_settings"]["max_inner_iterations"] = 1
    response = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": document,
            "execute": True,
        },
    )
    run_id = response.json()["id"]
    result = (await client.get(f"/api/v1/calculation-runs/{run_id}/result")).json()
    assert result["status"] == "NON_CONVERGED"
    assert result["compliance"]["overall_compliant"] is False


async def test_unmappable_input_is_rejected_with_a_reason(
    client: Any, approved_libraries: Any
) -> None:
    project_id = await _project(client)
    document = copy.deepcopy(_document())
    document["enclosure"]["conductors"][0]["resistance_ohm_per_m"] = None
    response = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": document,
            "execute": True,
        },
    )
    assert response.status_code == 422
    assert "resistance_ohm_per_m" in str(response.json()["detail"])


async def test_cfd_export_is_downloadable(client: Any, approved_libraries: Any) -> None:
    project_id = await _project(client)
    submitted = await client.post(
        "/api/v1/calculation-runs",
        json={"project_id": project_id, "input_snapshot": _document("MODE_4")},
    )
    run_id = submitted.json()["id"]
    response = await client.get(f"/api/v1/calculation-runs/{run_id}/cfd-export")
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    package = response.json()
    assert package["format"] == "thermpro-cfd-export"
    assert package["units"].startswith("SI base units")


async def test_run_list_total_respects_its_filters(client: Any, approved_libraries: Any) -> None:
    """A page count that ignores the filter is simply wrong."""
    first = await _project(client, "Filter test A")
    second = await _project(client, "Filter test B")
    for project_id in (first, first, second):
        await client.post(
            "/api/v1/calculation-runs",
            json={"project_id": project_id, "input_snapshot": _document()},
        )

    listed = await client.get(f"/api/v1/calculation-runs?project_id={first}")
    body = listed.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert all(item["project_id"] == first for item in body["items"])

    by_status = await client.get("/api/v1/calculation-runs?run_status=COMPLETED")
    assert by_status.json()["total"] == len(by_status.json()["items"])


async def test_iec60890_template_is_empty(client: Any) -> None:
    """CR-ENG-002: the only IEC TR 60890 artefact this repository ships."""
    response = await client.get("/api/v1/iec60890-datasets/template")
    assert response.status_code == 200
    assert response.json()["coefficients"]["c0"] == 0.0


async def test_importing_the_dataset_enables_mode_1(
    client: Any, as_admin: None, approved_libraries: Any
) -> None:
    """
    The full CR-ENG-002 path: import, then MODE 1 runs.

    The coefficients here are invented. They exercise the import and the
    MODE 1 code path; they are not the licensed values and must never be
    used for a real assessment.
    """
    imported = await client.post(
        "/api/v1/iec60890-datasets",
        json={
            "version": "test-0.0.1",
            "source_reference": "Invented values for an integration test.",
            "coefficients": {
                "c0": 1.8,
                "n": 0.8,
                "d": 1.35,
                "installation_factors": {
                    "VERTICAL": 0.9,
                    "HORIZONTAL_UP": 1.4,
                    "HORIZONTAL_DOWN": 0.5,
                },
            },
        },
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["is_active"] is True
    # The licensed numbers are never handed back out.
    assert "coefficients" not in imported.json()

    project_id = await _project(client, "MODE 1 with dataset")
    response = await client.post(
        "/api/v1/calculation-runs",
        json={
            "project_id": project_id,
            "input_snapshot": _document("MODE_1"),
            "execute": True,
        },
    )
    run_id = response.json()["id"]
    result = (await client.get(f"/api/v1/calculation-runs/{run_id}/result")).json()
    assert result["status"] == "CONVERGED"
    assert result["mode_1_result"]["effective_cooling_area_m2"] > 0.0


async def test_a_dataset_version_cannot_be_reimported(
    client: Any, as_admin: None, approved_libraries: Any
) -> None:
    """CR-ENG-012: an imported dataset is immutable."""
    payload = {
        "version": "test-immutable-0.0.1",
        "source_reference": "Invented values for an integration test.",
        "coefficients": {"c0": 1.8, "n": 0.8, "d": 1.35},
    }
    first = await client.post("/api/v1/iec60890-datasets", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/iec60890-datasets", json=payload)
    assert second.status_code == 422
    assert "immutable" in str(second.json()["detail"])


async def test_importing_the_dataset_requires_an_administrator(client: Any) -> None:
    """CR-ENG-002: an engineer cannot install the licensed coefficients."""
    response = await client.post(
        "/api/v1/iec60890-datasets",
        json={
            "version": "test-forbidden-0.0.1",
            "source_reference": "Invented values for an integration test.",
            "coefficients": {"c0": 1.8, "n": 0.8, "d": 1.35},
        },
    )
    assert response.status_code == 403


async def test_an_unfilled_template_is_refused_on_import(
    client: Any, as_admin: None, approved_libraries: Any
) -> None:
    """A zero c_0 would silently report no temperature rise at all."""
    template = (await client.get("/api/v1/iec60890-datasets/template")).json()
    response = await client.post(
        "/api/v1/iec60890-datasets",
        json={
            "version": "test-empty-0.0.1",
            "source_reference": "An unfilled template.",
            "coefficients": template["coefficients"],
        },
    )
    assert response.status_code == 422

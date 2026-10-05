"""
End-to-end contract conformance: M0-03 in, M0-04 out.

The engine's own tests check that the mapping is right. These check the other
half of CR-TECH-001: that the document the engine accepts really validates
against the published M0-03 schema, and the document it returns really
validates against M0-04 — for every mode, converged or not.

This is the layer that owns both schemas, so it is the layer that proves they
are honoured.
"""
from __future__ import annotations

import pytest
from thermal_core.benchmarks.iec60890 import IEC60890Coefficients
from thermal_core.contract import JsonThermalSolver, solve_json
from thermal_core.reference_model import m003_document
from thermpro_schemas import validate_input_snapshot, validate_result_snapshot

TEST_COEFFICIENTS = IEC60890Coefficients(
    c0=1.8,
    n=0.8,
    d=1.35,
    installation_factors={
        "VERTICAL": 0.9,
        "HORIZONTAL_UP": 1.4,
        "HORIZONTAL_DOWN": 0.5,
    },
    dataset_version="TEST-DATASET-ONLY",
)
"""
Invented values. CR-ENG-002 forbids the real IEC TR 60890 coefficients in this
repository; these exercise the MODE_1 code path and nothing else.
"""


@pytest.mark.contract
def test_reference_model_is_a_valid_m003_document() -> None:
    validate_input_snapshot(m003_document())


@pytest.mark.contract
@pytest.mark.parametrize("mode", ["MODE_1", "MODE_2", "MODE_3", "MODE_4"])
def test_every_mode_returns_a_valid_m004_document(mode: str) -> None:
    """
    A failure is still a contract-conforming result.

    MODE_1 without the licensed dataset and MODE_4 both fail by design; the
    API layer still has to be able to store and serve what comes back.
    """
    document = m003_document(mode, with_fan=(mode == "MODE_3"))
    validate_input_snapshot(document)
    result = solve_json(document)
    validate_result_snapshot(result)
    assert result["mode"] == mode
    assert result["status"] in ("CONVERGED", "NON_CONVERGED", "FAILED")


@pytest.mark.contract
def test_mode_1_with_a_dataset_returns_a_valid_document() -> None:
    result = solve_json(
        m003_document("MODE_1"), iec60890_coefficients=TEST_COEFFICIENTS
    )
    validate_result_snapshot(result)
    assert result["status"] == "CONVERGED"
    assert result["mode_1_result"] is not None


@pytest.mark.contract
def test_non_converged_result_is_still_a_valid_document() -> None:
    """CR-ENG-005: the UI needs a well-formed result to put the watermark on."""
    document = m003_document()
    document["solver_settings"]["max_inner_iterations"] = 1
    result = solve_json(document)
    validate_result_snapshot(result)
    assert result["status"] == "NON_CONVERGED"
    assert result["compliance"]["overall_compliant"] is False


@pytest.mark.contract
def test_single_compartment_model_returns_a_valid_document() -> None:
    result = solve_json(m003_document(with_compartments=False))
    validate_result_snapshot(result)
    assert result["status"] == "CONVERGED"


@pytest.mark.contract
def test_solver_interface_round_trip_validates() -> None:
    solver = JsonThermalSolver(run_id="11111111-2222-3333-4444-555555555555")
    document = m003_document()
    validate_input_snapshot(document)
    result = solver.solve(document)
    validate_result_snapshot(result)
    assert result["run_id"] == "11111111-2222-3333-4444-555555555555"


@pytest.mark.contract
def test_result_is_json_serialisable() -> None:
    """A result that cannot be stored or sent is not a result."""
    import json

    payload = json.dumps(solve_json(m003_document()), allow_nan=False)
    assert json.loads(payload)["status"] == "CONVERGED"

"""
Unit tests for calculation execution, without a database.

The service's decisions — which statuses may execute, how a solver status
maps onto a run status, that the stored document is the engine's verbatim
output — are pure logic and deserve a test that runs on every push rather
than only when PostgreSQL is available. Persistence itself is covered by the
integration tests.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from thermal_core.benchmarks.iec60890 import IEC60890Coefficients
from thermal_core.contract import solve_json
from thermal_core.reference_model import m003_document
from thermpro_api.models.calculation_run import CalculationRun
from thermpro_api.services.auth import UserContext
from thermpro_api.services.calculation import (
    EXECUTABLE_STATUSES,
    CalculationExecutionError,
    CalculationService,
)
from thermpro_api.services.hashing import sha256_hex
from thermpro_api.services.iec60890 import (
    COEFFICIENT_TEMPLATE,
    Iec60890ImportError,
    coefficients_from_json,
)
from thermpro_schemas import validate_result_snapshot

ACTOR = UserContext(
    user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    email="engineer@example.test",
    role="ENGINEER",
)


class _FakeSession:
    """
    Just enough AsyncSession for the execution path.

    A real session would need a database; what these tests check is the
    service's decisions, not SQLAlchemy's.
    """

    def __init__(self) -> None:
        self.flushes = 0
        self.added: list[Any] = []

    async def flush(self) -> None:
        self.flushes += 1

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the execution path under test must not query the database"
        )


def _run(status: str = "PENDING", mode: str = "MODE_2") -> CalculationRun:
    document = m003_document(mode)
    return CalculationRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        submitted_by_id=ACTOR.user_id,
        input_snapshot=document,
        input_checksum_sha256=sha256_hex(document),
        mode=mode,
        schema_version="1.0",
        status=status,
    )


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> CalculationService:
    import thermpro_api.services.calculation as module

    class _NoAudit:
        def __init__(self, _db: Any) -> None: ...

        async def record_event(self, **_: Any) -> None: ...

    class _NoCoefficients:
        def __init__(self, _db: Any) -> None: ...

        async def active_coefficients(self) -> None:
            return None

    monkeypatch.setattr(module, "AuditService", _NoAudit)
    monkeypatch.setattr(module, "Iec60890Service", _NoCoefficients)
    return CalculationService(_FakeSession())  # type: ignore[arg-type]


class TestExecution:
    async def test_converged_run_stores_the_engine_document_verbatim(
        self, service: CalculationService
    ) -> None:
        run = _run()
        await service.execute(run, ACTOR)
        assert run.status == "COMPLETED"
        assert run.result_snapshot is not None
        assert run.result_snapshot["status"] == "CONVERGED"
        assert run.result_snapshot["run_id"] == str(run.id)
        # The checksum is of what was stored, so it proves the document has
        # not been reshaped between the engine and the database.
        assert run.result_checksum_sha256 == sha256_hex(run.result_snapshot)
        validate_result_snapshot(run.result_snapshot)

    async def test_engine_version_is_recorded(
        self, service: CalculationService
    ) -> None:
        run = _run()
        await service.execute(run, ACTOR)
        assert run.engine_version
        assert run.result_snapshot is not None
        assert run.engine_version == run.result_snapshot["engine_version"]

    async def test_timing_is_recorded(self, service: CalculationService) -> None:
        run = _run()
        await service.execute(run, ACTOR)
        assert run.started_at is not None
        assert run.completed_at is not None
        assert run.completed_at >= run.started_at

    async def test_non_converged_run_completes_and_keeps_its_result(
        self, service: CalculationService
    ) -> None:
        """
        CR-ENG-005: the result is stored, not discarded.

        The UI needs it to show the RESULT INVALID watermark, and the audit
        trail needs it to record that the calculation was attempted.
        """
        run = _run()
        run.input_snapshot = {
            **run.input_snapshot,
            "solver_settings": {
                **run.input_snapshot["solver_settings"],
                "max_inner_iterations": 1,
            },
        }
        await service.execute(run, ACTOR)
        assert run.status == "COMPLETED"
        assert run.result_snapshot is not None
        assert run.result_snapshot["status"] == "NON_CONVERGED"
        assert run.result_snapshot["compliance"]["overall_compliant"] is False
        assert run.rejection_reason

    async def test_failed_solve_is_stored_not_raised(
        self, service: CalculationService
    ) -> None:
        """MODE_1 without the licensed dataset: a result, not an exception."""
        run = _run(mode="MODE_1")
        await service.execute(run, ACTOR)
        assert run.status == "FAILED"
        assert run.result_snapshot is not None
        assert "CR-ENG-002" in run.result_snapshot["failure_reason"]

    async def test_unmappable_input_rejects_the_run(
        self, service: CalculationService
    ) -> None:
        run = _run()
        document = {**run.input_snapshot}
        enclosure = {**document["enclosure"]}
        conductors = [dict(c) for c in enclosure["conductors"]]
        conductors[0]["resistance_ohm_per_m"] = None
        enclosure["conductors"] = conductors
        document["enclosure"] = enclosure
        run.input_snapshot = document

        with pytest.raises(CalculationExecutionError, match="solvable model"):
            await service.execute(run, ACTOR)
        assert run.status == "REJECTED"
        assert run.rejection_reason is not None
        assert "resistance_ohm_per_m" in run.rejection_reason

    @pytest.mark.parametrize("status", sorted(EXECUTABLE_STATUSES))
    async def test_executable_statuses_run(
        self, service: CalculationService, status: str
    ) -> None:
        run = _run(status=status)
        await service.execute(run, ACTOR)
        assert run.result_snapshot is not None

    @pytest.mark.parametrize("status", ["COMPLETED", "RUNNING", "CANCELLED"])
    async def test_a_completed_run_is_not_re_executed(
        self, service: CalculationService, status: str
    ) -> None:
        """Its result is part of the audit record; a new question is a new run."""
        run = _run(status=status)
        with pytest.raises(CalculationExecutionError, match="cannot be executed"):
            await service.execute(run, ACTOR)

    async def test_cfd_export_package_describes_the_model(
        self, service: CalculationService
    ) -> None:
        run = _run(mode="MODE_4")
        filename, package = await service.cfd_export_package(run)
        assert filename.startswith("thermpro-cfd-export-")
        assert package["format"] == "thermpro-cfd-export"
        assert package["calculation_id"] == str(run.id)
        assert package["compartments"]
        assert package["heat_sources"]
        # Meshing and solver settings are the CFD engineer's judgement.
        assert "mesh" not in package


class TestResultRetrieval:
    def test_no_result_before_execution(self, service: CalculationService) -> None:
        assert service.result_document(_run()) is None

    async def test_result_matches_a_direct_engine_call(
        self, service: CalculationService
    ) -> None:
        """The API adds nothing to the result, and takes nothing away."""
        run = _run()
        await service.execute(run, ACTOR)
        direct = solve_json(run.input_snapshot, run_id=str(run.id))
        stored = service.result_document(run)
        assert stored is not None
        for document in (direct, stored):
            document["solver_summary"].pop("wall_clock_s")
        assert stored == direct


class TestIec60890Import:
    def test_the_shipped_template_contains_no_coefficients(self) -> None:
        """CR-ENG-002: a shape, not a dataset."""
        coefficients = COEFFICIENT_TEMPLATE["coefficients"]
        assert coefficients["c0"] == 0.0
        assert coefficients["n"] == 0.0
        assert coefficients["d"] == 0.0
        assert all(
            value == 0.0 for value in coefficients["installation_factors"].values()
        )

    def test_an_unfilled_template_is_refused(self) -> None:
        """A zero c_0 would report no temperature rise at all."""
        with pytest.raises(Iec60890ImportError):
            coefficients_from_json(dict(COEFFICIENT_TEMPLATE["coefficients"]))

    def test_a_filled_template_builds_engine_coefficients(self) -> None:
        payload = {
            **COEFFICIENT_TEMPLATE["coefficients"],
            "c0": 1.8,
            "n": 0.8,
            "d": 1.35,
            "installation_factors": {"VERTICAL": 0.9, "HORIZONTAL_UP": 1.4},
            "height_distribution": [[0.0, 0.5], [1.0, 1.35]],
            "dataset_version": "2022.1.0",
        }
        coefficients = coefficients_from_json(payload)
        assert isinstance(coefficients, IEC60890Coefficients)
        assert coefficients.dataset_version == "2022.1.0"
        assert coefficients.installation_factor("VERTICAL") == 0.9
        # An orientation the dataset does not name falls back, it does not fail.
        assert coefficients.installation_factor("HORIZONTAL_DOWN") == 1.0

    def test_a_top_cooler_than_the_middle_is_refused(self) -> None:
        payload = {**COEFFICIENT_TEMPLATE["coefficients"], "c0": 1.8, "n": 0.8, "d": 0.9}
        with pytest.raises(Iec60890ImportError):
            coefficients_from_json(payload)

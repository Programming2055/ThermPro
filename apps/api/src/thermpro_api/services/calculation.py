"""
Calculation submission and execution.

Submission validates and stores an immutable InputSnapshot. Execution hands
that snapshot to `thermpro_engine` and stores the ResultSnapshot it returns.
The two are separate because the input is a record of what was asked and the
result is a record of what was computed: re-running a calculation must never
be able to change the question it answered.

The engine is reached only through its JSON contract (CR-TECH-001). This
module knows nothing about thermal physics, and the engine knows nothing
about this database.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from thermal_core.cfd_export import build_cfd_export_package, cfd_export_filename
from thermal_core.contract import (
    ContractError,
    input_snapshot_from_json,
    solve_json,
)
from thermal_core.solver.iterative import ZonalSolver
from thermpro_api.models.calculation_run import CalculationRun
from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.audit import AuditService
from thermpro_api.services.auth import UserContext
from thermpro_api.services.hashing import sha256_hex
from thermpro_api.services.iec60890 import Iec60890Service
from thermpro_schemas import (
    SchemaValidationError,
    validate_input_snapshot,
    validate_result_snapshot,
)

logger = structlog.get_logger()

#: Statuses from which a run may be executed. A COMPLETED run is not one of
#: them: its result is part of the audit record.
EXECUTABLE_STATUSES = frozenset({"PENDING", "FAILED", "ENGINE_NOT_IMPLEMENTED"})


class CalculationSubmissionError(ValueError):
    """Raised when a calculation cannot be submitted due to validation failures."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


class CalculationExecutionError(ValueError):
    """
    Raised when a run cannot be executed at all.

    A solver that runs and fails is not this: that produces a FAILED
    ResultSnapshot, which is stored like any other result. This is for a run
    that cannot be started — already completed, or an input the engine cannot
    map onto a model.
    """

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


class CalculationService:
    """Service for submitting and querying calculation runs."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def submit(
        self,
        input_snapshot: dict[str, Any],
        project_id: uuid.UUID,
        actor: UserContext,
    ) -> CalculationRun:
        """
        Submit a thermal calculation.

        Steps (in order):
        1. Validate schema_version field is present.
        2. Validate full InputSnapshot against M0-03 JSON Schema.
        3. Validate library manifest — all pins must resolve to APPROVED releases
           with matching content hashes.
        4. Compute canonical input checksum (SHA-256 of canonical JSON).
        5. Persist immutable CalculationRun with status PENDING.

        Submission does not solve. The run is queued, and `execute` hands it
        to the engine; separating the two keeps a long solve from holding a
        request open, and keeps the stored question independent of the
        stored answer.

        The input_snapshot is NEVER modified after submission.

        Args:
            input_snapshot: Raw InputSnapshot dict from the API request.
            project_id: UUID of the owning project.
            actor: Authenticated user submitting the calculation.

        Returns:
            Persisted CalculationRun.

        Raises:
            CalculationSubmissionError: If any validation step fails.
        """
        # Step 1 + 2: JSON Schema validation
        try:
            validate_input_snapshot(input_snapshot)
        except SchemaValidationError as exc:
            raise CalculationSubmissionError(
                f"InputSnapshot failed schema validation: {exc}",
                details=exc.errors,
            ) from exc

        # Step 3: library manifest validation
        manifest_errors = await self._validate_library_manifest(
            input_snapshot.get("library_manifest", {})
        )
        if manifest_errors:
            raise CalculationSubmissionError(
                "Library manifest validation failed.",
                details=manifest_errors,
            )

        # Step 4: canonical checksum
        checksum = sha256_hex(input_snapshot)

        # Step 5: persist immutable run
        now_iso = datetime.now(UTC).isoformat()
        run = CalculationRun(
            project_id=project_id,
            submitted_by_id=actor.user_id,
            input_snapshot=input_snapshot,
            input_checksum_sha256=checksum,
            mode=input_snapshot["mode"],
            schema_version=input_snapshot.get("schema_version", "1.0"),
            status="PENDING",
            submitted_at=now_iso,
        )
        self._db.add(run)
        await self._db.flush()

        # Record audit event
        audit = AuditService(self._db)
        await audit.record_event(
            action="calculation_run.submitted",
            entity_type="CalculationRun",
            entity_id=run.id,
            actor=actor,
            metadata={
                "mode": run.mode,
                "schema_version": run.schema_version,
                "input_checksum": checksum,
            },
        )

        return run

    async def get_by_id(self, run_id: uuid.UUID) -> CalculationRun | None:
        """Return a CalculationRun by primary key, or None."""
        result = await self._db.execute(
            select(CalculationRun).where(CalculationRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        project_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CalculationRun]:
        """List calculation runs with optional project and status filters."""
        stmt = (
            self._filtered(select(CalculationRun), project_id, status)
            .order_by(CalculationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count_runs(
        self,
        project_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> int:
        """
        How many runs match the filters.

        The same filters as `list_runs`: a total that counted every run in the
        database would make the page count wrong for anyone looking at one
        project.
        """
        stmt = self._filtered(
            select(func.count()).select_from(CalculationRun), project_id, status
        )
        result = await self._db.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _filtered(
        stmt: Any, project_id: uuid.UUID | None, status: str | None
    ) -> Any:
        if project_id is not None:
            stmt = stmt.where(CalculationRun.project_id == project_id)
        if status is not None:
            stmt = stmt.where(CalculationRun.status == status)
        return stmt

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self, run: CalculationRun, actor: UserContext
    ) -> CalculationRun:
        """
        Run the thermal engine against a submitted snapshot and store the result.

        The engine is called through its JSON contract and nothing else
        (CR-TECH-001). A solver failure is a stored FAILED result, not an
        exception: an engineer needs to see why a calculation did not
        converge, and that reasoning belongs in the audit record.

        Raises
        ------
        CalculationExecutionError
            If the run is not in an executable state, or the input cannot be
            mapped onto a model at all.
        """
        if run.status not in EXECUTABLE_STATUSES:
            raise CalculationExecutionError(
                f"Run {run.id} has status {run.status!r} and cannot be executed. "
                f"A completed run's result is part of the audit record; submit a "
                f"new run instead."
            )

        coefficients = None
        if run.mode == "MODE_1":
            # CR-ENG-002: the licensed dataset is never in this repository, so
            # it comes from whatever the administrator imported.
            coefficients = await Iec60890Service(self._db).active_coefficients()

        run.status = "RUNNING"
        run.started_at = datetime.now(UTC).isoformat()
        await self._db.flush()

        try:
            # The solve is CPU-bound and pure; running it off the event loop
            # keeps a slow model from blocking every other request.
            result = await asyncio.to_thread(
                solve_json,
                run.input_snapshot,
                run_id=str(run.id),
                iec60890_coefficients=coefficients,
            )
        except ContractError as exc:
            run.status = "REJECTED"
            run.rejection_reason = str(exc)
            run.completed_at = datetime.now(UTC).isoformat()
            await self._db.flush()
            raise CalculationExecutionError(
                f"The InputSnapshot could not be mapped onto a solvable model: {exc}",
                details=list(exc.errors),
            ) from exc
        except Exception as exc:
            # The engine is documented never to raise on a modelling or
            # convergence failure, so reaching here means a defect. Record it
            # and re-raise: a run left in RUNNING looks like work still in
            # progress and would be waited on forever.
            run.status = "FAILED"
            run.rejection_reason = (
                f"The engine raised an unexpected {type(exc).__name__}: {exc}"
            )
            run.completed_at = datetime.now(UTC).isoformat()
            await self._db.flush()
            logger.exception("thermpro_api.engine_crashed", run_id=str(run.id))
            raise

        try:
            validate_result_snapshot(result)
        except SchemaValidationError as exc:
            # The engine produced something the contract does not describe.
            # Storing it would corrupt the audit trail, so the run fails loudly.
            run.status = "FAILED"
            run.rejection_reason = (
                f"The engine returned a result that does not conform to M0-04: {exc}"
            )
            run.completed_at = datetime.now(UTC).isoformat()
            await self._db.flush()
            logger.error(
                "thermpro_api.result_contract_violation",
                run_id=str(run.id),
                errors=exc.errors[:5],
            )
            raise CalculationExecutionError(
                str(run.rejection_reason), details=exc.errors
            ) from exc

        run.result_snapshot = result
        run.result_checksum_sha256 = sha256_hex(result)
        run.engine_version = str(result.get("engine_version"))
        run.completed_at = datetime.now(UTC).isoformat()
        # CR-ENG-005: a NON_CONVERGED result is stored and shown, carrying the
        # RESULT INVALID treatment downstream — it is never silently dropped
        # and never presented as a usable answer.
        run.status = {
            "CONVERGED": "COMPLETED",
            "NON_CONVERGED": "COMPLETED",
            "FAILED": "FAILED",
        }.get(str(result.get("status")), "FAILED")
        if result.get("failure_reason"):
            run.rejection_reason = str(result["failure_reason"])
        await self._db.flush()

        await AuditService(self._db).record_event(
            action="calculation_run.executed",
            entity_type="CalculationRun",
            entity_id=run.id,
            actor=actor,
            metadata={
                "solver_status": result.get("status"),
                "engine_version": run.engine_version,
                "result_checksum": run.result_checksum_sha256,
                "wall_clock_s": result["solver_summary"]["wall_clock_s"],
            },
        )
        return run

    async def cfd_export_package(
        self, run: CalculationRun
    ) -> tuple[str, dict[str, Any]]:
        """
        Build the MODE 4 CFD export package for a run (filename, document).

        A converged result is used to seed the external solver's initial
        conditions when one exists; without it the CFD run simply starts from
        ambient and takes longer to reach the same answer.
        """
        try:
            mapped = input_snapshot_from_json(run.input_snapshot, run_id=str(run.id))
        except ContractError as exc:
            raise CalculationExecutionError(
                f"The InputSnapshot could not be mapped for export: {exc}",
                details=list(exc.errors),
            ) from exc

        seed = None
        if run.result_snapshot and run.result_snapshot.get("status") == "CONVERGED":
            # Re-solve rather than reconstruct: the stored document is the
            # M0-04 projection of the result, not the result itself, and
            # inventing the missing interior nodes would be guesswork.
            seed = await asyncio.to_thread(ZonalSolver().solve, mapped.snapshot)
            if not seed.is_valid:
                seed = None

        package = build_cfd_export_package(mapped.snapshot, seed_result=seed)
        return cfd_export_filename(mapped.snapshot), package

    def result_document(self, run: CalculationRun) -> dict[str, Any] | None:
        """The stored M0-04 document for a run, or None if it has not run."""
        return run.result_snapshot

    async def _validate_library_manifest(
        self, manifest: dict[str, Any]
    ) -> list[str]:
        """
        Verify each pin in the library_manifest resolves to an APPROVED release
        with a matching content hash.

        Returns a list of error strings (empty = valid).
        """
        errors: list[str] = []
        for library_key, pin in manifest.items():
            if not isinstance(pin, dict):
                errors.append(f"{library_key}: pin must be an object.")
                continue

            library_name = pin.get("name")
            version = pin.get("version")
            expected_hash = pin.get("content_hash_sha256")

            if not library_name or not version or not expected_hash:
                errors.append(
                    f"{library_key}: pin missing required fields"
                    " (name, version, content_hash_sha256)."
                )
                continue

            result = await self._db.execute(
                select(LibraryRelease).where(
                    LibraryRelease.library_name == library_name,
                    LibraryRelease.version == version,
                    LibraryRelease.status == "APPROVED",
                )
            )
            release = result.scalar_one_or_none()

            if release is None:
                errors.append(
                    f"{library_key}: no APPROVED release found for "
                    f"'{library_name}' version '{version}'."
                )
                continue

            if release.content_hash_sha256 != expected_hash:
                errors.append(
                    f"{library_key}: content hash mismatch for '{library_name}' v{version}. "
                    f"Expected {expected_hash[:12]}..., got {release.content_hash_sha256[:12]}..."
                )

        return errors

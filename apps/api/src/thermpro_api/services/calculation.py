"""Calculation submission service."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from thermpro_schemas import SchemaValidationError, validate_input_snapshot

from thermal_core import __version__ as ENGINE_VERSION
from thermal_core import solve as run_solver
from thermal_core.serialization import result_to_dict

from thermpro_api.models.calculation_run import CalculationRun
from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.audit import AuditService
from thermpro_api.services.auth import UserContext
from thermpro_api.services.hashing import sha256_hex
from thermpro_api.services.solver_adapter import AdaptationError, build_solver_input

_STATUS_BY_SOLVER = {
    "CONVERGED": "COMPLETED",
    "NON_CONVERGED": "NON_CONVERGED",  # CR-ENG-005: never presented as a valid result
    "FAILED": "FAILED",
}


class CalculationSubmissionError(ValueError):
    """Raised when a calculation cannot be submitted due to validation failures."""

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
        5. Persist immutable CalculationRun.
        6. MODE_2 runs the M4 zonal solver synchronously (COMPLETED | NON_CONVERGED |
           FAILED); other modes stay ENGINE_NOT_IMPLEMENTED.

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

        # Step 4b: only MODE_2 is executable today; build the solver input up front
        # so an unsolvable snapshot is rejected before anything is stored.
        adaptation = None
        run_id = uuid.uuid4()
        if input_snapshot["mode"] == "MODE_2":
            try:
                adaptation = build_solver_input(input_snapshot, str(run_id))
            except (AdaptationError, ValueError) as exc:
                raise CalculationSubmissionError(str(exc), details=[str(exc)]) from exc

        # Step 5: persist immutable run
        now_iso = datetime.now(UTC).isoformat()
        run = CalculationRun(
            id=run_id,
            project_id=project_id,
            submitted_by_id=actor.user_id,
            input_snapshot=input_snapshot,
            input_checksum_sha256=checksum,
            mode=input_snapshot["mode"],
            schema_version=input_snapshot.get("schema_version", "1.0"),
            status="ENGINE_NOT_IMPLEMENTED",
            submitted_at=now_iso,
        )
        if adaptation is not None:
            run.started_at = datetime.now(UTC).isoformat()
            result = run_solver(adaptation.solver_input)
            payload = result_to_dict(result)
            payload["assumptions"] = list(adaptation.assumptions)
            payload["warnings"] = payload["warnings"] + list(adaptation.warnings)
            run.result_snapshot = payload
            run.result_checksum_sha256 = sha256_hex(payload)
            run.engine_version = ENGINE_VERSION
            run.status = _STATUS_BY_SOLVER[result.status.value]
            run.completed_at = datetime.now(UTC).isoformat()
            if result.status.value != "CONVERGED":
                run.rejection_reason = (
                    "Solver did not converge: result is INVALID."
                    if result.status.value == "NON_CONVERGED"
                    else "; ".join(w.message for w in result.warnings)
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
        stmt = select(CalculationRun).order_by(CalculationRun.created_at.desc())
        if project_id:
            stmt = stmt.where(CalculationRun.project_id == project_id)
        if status:
            stmt = stmt.where(CalculationRun.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

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

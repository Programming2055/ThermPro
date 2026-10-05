"""
Administration of the licensed IEC TR 60890 coefficient dataset.

CR-ENG-002: these coefficients are licensed and are never committed to this
repository. This service is the import path an administrator uses to supply
them, and the lookup the calculation service uses to attach the active set to
a MODE 1 run.

The empty template this module emits is the only IEC TR 60890 artefact that
*is* shipped: it describes the shape of the data without containing any of it.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from thermal_core.benchmarks.iec60890 import IEC60890Coefficients
from thermpro_api.models.iec60890_dataset import Iec60890Dataset
from thermpro_api.services.audit import AuditService
from thermpro_api.services.auth import UserContext
from thermpro_api.services.hashing import sha256_hex

COEFFICIENT_TEMPLATE: dict[str, Any] = {
    "version": "",
    "source_reference": (
        "IEC TR 60890:<edition>, Table <n> — transcribed by <name>, <date>"
    ),
    "coefficients": {
        "c0": 0.0,
        "n": 0.0,
        "d": 0.0,
        "installation_factors": {
            "VERTICAL": 0.0,
            "HORIZONTAL_UP": 0.0,
            "HORIZONTAL_DOWN": 0.0,
        },
        "default_installation_factor": 1.0,
        "height_distribution": [],
    },
}
"""
The empty import template (CR-ENG-002).

Every number is zero: this is a shape, not a dataset. `IEC60890Coefficients`
rejects a non-positive c_0 precisely so that an unfilled template cannot be
mistaken for an imported one and quietly report no temperature rise.
"""


class Iec60890ImportError(ValueError):
    """Raised when a submitted coefficient dataset cannot be accepted."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


def coefficients_from_json(payload: dict[str, Any]) -> IEC60890Coefficients:
    """
    Build the engine's coefficient object from a stored dataset.

    Raises
    ------
    Iec60890ImportError
        If the values are not a usable coefficient set. The engine's own
        validation does the real checking; this turns it into an API error.
    """
    distribution = payload.get("height_distribution") or []
    try:
        return IEC60890Coefficients(
            c0=float(payload["c0"]),
            n=float(payload["n"]),
            d=float(payload["d"]),
            installation_factors={
                str(key): float(value)
                for key, value in (payload.get("installation_factors") or {}).items()
            },
            default_installation_factor=float(
                payload.get("default_installation_factor", 1.0)
            ),
            height_distribution=tuple(
                (float(point[0]), float(point[1])) for point in distribution
            ),
            dataset_version=str(payload.get("dataset_version", "")),
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise Iec60890ImportError(
            f"The coefficient set is not usable: {exc}"
        ) from exc


class Iec60890Service:
    """Import, activate and read the licensed coefficient dataset."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def import_dataset(
        self,
        version: str,
        source_reference: str,
        coefficients: dict[str, Any],
        actor: UserContext,
        *,
        activate: bool = True,
    ) -> Iec60890Dataset:
        """
        Import a coefficient dataset and, by default, make it the active one.

        Raises
        ------
        Iec60890ImportError
            If the version already exists — a dataset is immutable once
            imported (CR-ENG-012), so a correction is a new version — or if
            the coefficients themselves are not usable.
        """
        if not version.strip():
            raise Iec60890ImportError("A dataset version is required (M0-09).")
        if not source_reference.strip():
            raise Iec60890ImportError(
                "A source_reference is required: a coefficient that cannot be "
                "traced to its licensed source cannot be defended in a review."
            )

        existing = await self._db.execute(
            select(Iec60890Dataset).where(Iec60890Dataset.version == version)
        )
        if existing.scalar_one_or_none() is not None:
            raise Iec60890ImportError(
                f"IEC TR 60890 dataset version {version!r} is already imported. "
                f"CR-ENG-012: an imported dataset is immutable; import a new "
                f"version instead of changing this one."
            )

        # Validate by constructing the engine's own type: a template that was
        # never filled in has c0 = 0 and is rejected here, not at solve time.
        coefficients_from_json({**coefficients, "dataset_version": version})

        dataset = Iec60890Dataset(
            version=version,
            source_reference=source_reference,
            content_hash_sha256=sha256_hex(coefficients),
            coefficients=coefficients,
            is_active=False,
            imported_by_id=actor.user_id,
        )
        self._db.add(dataset)
        await self._db.flush()

        if activate:
            await self.activate(dataset.id, actor)

        await AuditService(self._db).record_event(
            action="iec60890_dataset.imported",
            entity_type="Iec60890Dataset",
            entity_id=dataset.id,
            actor=actor,
            metadata={
                "version": version,
                "content_hash": dataset.content_hash_sha256,
                "source_reference": source_reference,
                # The coefficients themselves are licensed and are deliberately
                # not copied into the audit trail.
            },
        )
        return dataset

    async def activate(self, dataset_id: uuid.UUID, actor: UserContext) -> None:
        """Make one dataset the active one, deactivating any other."""
        await self._db.execute(
            update(Iec60890Dataset)
            .where(Iec60890Dataset.id != dataset_id)
            .values(is_active=False)
        )
        await self._db.execute(
            update(Iec60890Dataset)
            .where(Iec60890Dataset.id == dataset_id)
            .values(is_active=True)
        )
        await AuditService(self._db).record_event(
            action="iec60890_dataset.activated",
            entity_type="Iec60890Dataset",
            entity_id=dataset_id,
            actor=actor,
            metadata={"activated_at": datetime.now(UTC).isoformat()},
        )

    async def active_dataset(self) -> Iec60890Dataset | None:
        """The dataset MODE 1 runs use, or None if none has been imported."""
        result = await self._db.execute(
            select(Iec60890Dataset).where(Iec60890Dataset.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def active_coefficients(self) -> IEC60890Coefficients | None:
        """The active coefficients as the engine's own type, or None."""
        dataset = await self.active_dataset()
        if dataset is None:
            return None
        return coefficients_from_json(
            {**dataset.coefficients, "dataset_version": dataset.version}
        )

    async def list_datasets(self) -> list[Iec60890Dataset]:
        """Every imported dataset, newest first."""
        result = await self._db.execute(
            select(Iec60890Dataset).order_by(Iec60890Dataset.created_at.desc())
        )
        return list(result.scalars().all())

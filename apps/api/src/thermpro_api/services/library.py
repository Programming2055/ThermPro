"""Library release service — create and approve versioned library releases."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.hashing import sha256_hex


class LibraryImmutabilityError(ValueError):
    """Raised when attempting to modify an APPROVED library release."""


class LibraryService:
    """Service for managing versioned library releases."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_release(
        self,
        library_name: str,
        version: str,
        entries: list[dict[str, Any]],
        description: str | None = None,
    ) -> LibraryRelease:
        """
        Create a new DRAFT library release.

        The content_hash_sha256 is computed from the canonical JSON of *entries*.
        Entries are the library data rows; the hash is used for pin verification.

        Args:
            library_name: Logical library identifier e.g. "MaterialLibrary".
            version: Semantic version string e.g. "1.2.0".
            entries: List of library entry dicts. Content-hashed for integrity.
            description: Optional human-readable description.

        Returns:
            Persisted LibraryRelease in DRAFT status.
        """
        content_hash = sha256_hex(
            {"library_name": library_name, "version": version, "entries": entries}
        )
        release = LibraryRelease(
            library_name=library_name,
            version=version,
            status="DRAFT",
            content_hash_sha256=content_hash,
            description=description,
        )
        self._db.add(release)
        await self._db.flush()
        return release

    async def get_by_id(self, release_id: uuid.UUID) -> LibraryRelease | None:
        """Return a LibraryRelease by primary key, or None."""
        result = await self._db.execute(
            select(LibraryRelease).where(LibraryRelease.id == release_id)
        )
        return result.scalar_one_or_none()

    async def list_releases(
        self,
        library_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LibraryRelease]:
        """List library releases with optional filters."""
        stmt = select(LibraryRelease).order_by(LibraryRelease.created_at.desc())
        if library_name:
            stmt = stmt.where(LibraryRelease.library_name == library_name)
        if status:
            stmt = stmt.where(LibraryRelease.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def approve_release(
        self,
        release_id: uuid.UUID,
        approver_id: uuid.UUID,
    ) -> LibraryRelease:
        """
        Transition a release from UNDER_REVIEW to APPROVED.

        Once APPROVED the release is immutable (DR-002 / M0-09).

        Raises:
            ValueError: If the release is not found.
            LibraryImmutabilityError: If the release is already APPROVED.
        """
        release = await self.get_by_id(release_id)
        if release is None:
            raise ValueError(f"LibraryRelease {release_id} not found.")
        if release.status == "APPROVED":
            raise LibraryImmutabilityError(
                f"LibraryRelease {release_id} is already APPROVED and is immutable. "
                "Create a new release with a new semantic version instead (DR-002)."
            )
        release.status = "APPROVED"
        release.approved_by_id = approver_id
        release.approved_at = datetime.now(UTC).isoformat()
        await self._db.flush()
        return release

    async def submit_for_review(self, release_id: uuid.UUID) -> LibraryRelease:
        """Transition a DRAFT release to UNDER_REVIEW."""
        release = await self.get_by_id(release_id)
        if release is None:
            raise ValueError(f"LibraryRelease {release_id} not found.")
        if release.status == "APPROVED":
            raise LibraryImmutabilityError(
                f"LibraryRelease {release_id} is APPROVED and cannot be modified."
            )
        if release.status != "DRAFT":
            raise ValueError(
                f"LibraryRelease {release_id} is in status {release.status}; "
                "only DRAFT releases can be submitted for review."
            )
        release.status = "UNDER_REVIEW"
        await self._db.flush()
        return release

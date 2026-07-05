"""Dataset manifest service — pin set validation against approved library releases."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.models.dataset_manifest import DatasetManifest, DatasetManifestEntry
from thermpro_api.models.library_release import LibraryRelease


@dataclass
class LibraryPinResult:
    """Validation result for a single library pin."""

    library_key: str
    library_name: str
    version: str
    content_hash_sha256: str
    resolved: bool
    is_approved: bool
    hash_matches: bool
    detail: str = ""


@dataclass
class ManifestValidationResult:
    """Aggregate validation result for a DatasetManifest."""

    manifest_id: uuid.UUID
    is_valid: bool
    validated_at: str
    pin_results: list[LibraryPinResult] = field(default_factory=list)


class ManifestService:
    """Service for creating and validating dataset manifests."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_manifest(
        self,
        name: str,
        pins: list[dict[str, Any]],
        created_by_id: uuid.UUID,
        description: str | None = None,
    ) -> DatasetManifest:
        """
        Create a new DatasetManifest from a list of library pins.

        Each pin must have: library_key, library_name, version, content_hash_sha256.

        Args:
            name: Human-readable manifest name.
            pins: List of pin dicts with library_key, library_name, version,
                  content_hash_sha256.
            created_by_id: ID of the creating user.
            description: Optional description.

        Returns:
            Persisted DatasetManifest with entries.
        """
        manifest = DatasetManifest(
            name=name,
            description=description,
            created_by_id=created_by_id,
            is_valid=None,
        )
        self._db.add(manifest)
        await self._db.flush()

        for pin in pins:
            entry = DatasetManifestEntry(
                manifest_id=manifest.id,
                library_key=pin["library_key"],
                library_name=pin["library_name"],
                version=pin["version"],
                content_hash_sha256=pin["content_hash_sha256"],
            )
            self._db.add(entry)

        await self._db.flush()
        return manifest

    async def validate_manifest(self, manifest_id: uuid.UUID) -> ManifestValidationResult:
        """
        Validate a DatasetManifest: resolve each pin to an APPROVED release
        and verify the content hash matches.

        Updates manifest.is_valid and manifest.validated_at.

        Args:
            manifest_id: UUID of the DatasetManifest to validate.

        Returns:
            ManifestValidationResult with per-pin detail.

        Raises:
            ValueError: If the manifest is not found.
        """
        manifest = await self._get_manifest(manifest_id)
        if manifest is None:
            raise ValueError(f"DatasetManifest {manifest_id} not found.")

        entries_result = await self._db.execute(
            select(DatasetManifestEntry).where(DatasetManifestEntry.manifest_id == manifest_id)
        )
        entries = list(entries_result.scalars().all())

        pin_results: list[LibraryPinResult] = []
        all_valid = True

        for entry in entries:
            # Find matching approved release
            rel_result = await self._db.execute(
                select(LibraryRelease).where(
                    LibraryRelease.library_name == entry.library_name,
                    LibraryRelease.version == entry.version,
                    LibraryRelease.status == "APPROVED",
                )
            )
            release = rel_result.scalar_one_or_none()

            if release is None:
                pin_results.append(
                    LibraryPinResult(
                        library_key=entry.library_key,
                        library_name=entry.library_name,
                        version=entry.version,
                        content_hash_sha256=entry.content_hash_sha256,
                        resolved=False,
                        is_approved=False,
                        hash_matches=False,
                        detail="No APPROVED release found for this name+version.",
                    )
                )
                all_valid = False
                continue

            hash_matches = release.content_hash_sha256 == entry.content_hash_sha256
            if not hash_matches:
                all_valid = False

            pin_results.append(
                LibraryPinResult(
                    library_key=entry.library_key,
                    library_name=entry.library_name,
                    version=entry.version,
                    content_hash_sha256=entry.content_hash_sha256,
                    resolved=True,
                    is_approved=True,
                    hash_matches=hash_matches,
                    detail=(
                        "OK" if hash_matches
                        else f"Hash mismatch: expected {release.content_hash_sha256}"
                    ),
                )
            )

        now_iso = datetime.now(UTC).isoformat()
        manifest.is_valid = all_valid
        manifest.validated_at = now_iso
        await self._db.flush()

        return ManifestValidationResult(
            manifest_id=manifest_id,
            is_valid=all_valid,
            validated_at=now_iso,
            pin_results=pin_results,
        )

    async def get_by_id(self, manifest_id: uuid.UUID) -> DatasetManifest | None:
        """Return a DatasetManifest by primary key, or None."""
        return await self._get_manifest(manifest_id)

    async def _get_manifest(self, manifest_id: uuid.UUID) -> DatasetManifest | None:
        result = await self._db.execute(
            select(DatasetManifest).where(DatasetManifest.id == manifest_id)
        )
        return result.scalar_one_or_none()

"""Tests for dataset manifest validation logic."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from thermpro_api.models.dataset_manifest import DatasetManifestEntry
from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.manifest import ManifestService


def _make_manifest(manifest_id: uuid.UUID):
    from thermpro_api.models.dataset_manifest import DatasetManifest
    m = DatasetManifest.__new__(DatasetManifest)
    m.id = manifest_id
    m.name = "Test Manifest"
    m.description = None
    m.is_valid = None
    m.validated_at = None
    return m


def _make_entry(manifest_id: uuid.UUID, library_name: str, version: str, hash_val: str) -> DatasetManifestEntry:
    e = DatasetManifestEntry.__new__(DatasetManifestEntry)
    e.id = uuid.uuid4()
    e.manifest_id = manifest_id
    e.library_key = "material_library"
    e.library_name = library_name
    e.version = version
    e.content_hash_sha256 = hash_val
    return e


def _make_release(library_name: str, version: str, hash_val: str, status: str = "APPROVED") -> LibraryRelease:
    r = LibraryRelease.__new__(LibraryRelease)
    r.id = uuid.uuid4()
    r.library_name = library_name
    r.version = version
    r.status = status
    r.content_hash_sha256 = hash_val
    return r


class _MultiCallMock:
    """Helper to sequence execute() return values for multiple queries."""

    def __init__(self, *results):
        self._results = list(results)
        self._idx = 0

    async def __call__(self, *args, **kwargs):
        result = self._results[self._idx % len(self._results)]
        self._idx += 1
        return result


@pytest.mark.asyncio
async def test_manifest_valid_when_all_pins_resolve():
    """Manifest is valid when all pins resolve to APPROVED releases with matching hashes."""
    manifest_id = uuid.uuid4()
    manifest = _make_manifest(manifest_id)
    entry = _make_entry(manifest_id, "MaterialLibrary", "1.0.0", "a" * 64)
    release = _make_release("MaterialLibrary", "1.0.0", "a" * 64)

    manifest_result = MagicMock()
    manifest_result.scalar_one_or_none = MagicMock(return_value=manifest)

    entries_result = MagicMock()
    entries_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[entry])))

    release_result = MagicMock()
    release_result.scalar_one_or_none = MagicMock(return_value=release)

    db = AsyncMock()
    db.flush = AsyncMock()
    call_sequence = _MultiCallMock(manifest_result, entries_result, release_result)
    db.execute = call_sequence

    svc = ManifestService(db)
    result = await svc.validate_manifest(manifest_id)

    assert result.is_valid is True
    assert len(result.pin_results) == 1
    assert result.pin_results[0].resolved is True
    assert result.pin_results[0].hash_matches is True


@pytest.mark.asyncio
async def test_manifest_invalid_when_release_not_found():
    """Manifest is invalid when a pin has no matching APPROVED release."""
    manifest_id = uuid.uuid4()
    manifest = _make_manifest(manifest_id)
    entry = _make_entry(manifest_id, "MaterialLibrary", "99.0.0", "a" * 64)

    manifest_result = MagicMock()
    manifest_result.scalar_one_or_none = MagicMock(return_value=manifest)

    entries_result = MagicMock()
    entries_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[entry])))

    no_release_result = MagicMock()
    no_release_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.flush = AsyncMock()
    call_sequence = _MultiCallMock(manifest_result, entries_result, no_release_result)
    db.execute = call_sequence

    svc = ManifestService(db)
    result = await svc.validate_manifest(manifest_id)

    assert result.is_valid is False
    assert result.pin_results[0].resolved is False


@pytest.mark.asyncio
async def test_manifest_invalid_when_hash_mismatch():
    """Manifest is invalid when the content hash does not match the stored release."""
    manifest_id = uuid.uuid4()
    manifest = _make_manifest(manifest_id)
    entry = _make_entry(manifest_id, "MaterialLibrary", "1.0.0", "a" * 64)
    release = _make_release("MaterialLibrary", "1.0.0", "b" * 64)  # hash differs

    manifest_result = MagicMock()
    manifest_result.scalar_one_or_none = MagicMock(return_value=manifest)

    entries_result = MagicMock()
    entries_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[entry])))

    release_result = MagicMock()
    release_result.scalar_one_or_none = MagicMock(return_value=release)

    db = AsyncMock()
    db.flush = AsyncMock()
    call_sequence = _MultiCallMock(manifest_result, entries_result, release_result)
    db.execute = call_sequence

    svc = ManifestService(db)
    result = await svc.validate_manifest(manifest_id)

    assert result.is_valid is False
    assert result.pin_results[0].hash_matches is False

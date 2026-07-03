"""
Tests for library release immutability enforcement.

Once a LibraryRelease is APPROVED it must not be modified.
Any attempt must raise LibraryImmutabilityError.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from thermpro_api.models.library_release import LibraryRelease
from thermpro_api.services.library import LibraryImmutabilityError, LibraryService


def _make_release(status: str) -> LibraryRelease:
    """Create a minimal LibraryRelease stub."""
    r = LibraryRelease.__new__(LibraryRelease)
    r.id = uuid.uuid4()
    r.library_name = "MaterialLibrary"
    r.version = "1.0.0"
    r.status = status
    r.content_hash_sha256 = "a" * 64
    r.description = None
    r.approved_by_id = None
    r.approved_at = None
    return r


@pytest.fixture
def db_session():
    """Mock async SQLAlchemy session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_approve_approved_release_raises(db_session):
    """Approving an already-APPROVED release must raise LibraryImmutabilityError."""
    approved_release = _make_release("APPROVED")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=approved_release)
    db_session.execute = AsyncMock(return_value=result_mock)

    svc = LibraryService(db_session)
    with pytest.raises(LibraryImmutabilityError, match="immutable"):
        await svc.approve_release(approved_release.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_approve_draft_release_succeeds(db_session):
    """Approving a DRAFT release sets status to APPROVED."""
    draft_release = _make_release("DRAFT")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=draft_release)
    db_session.execute = AsyncMock(return_value=result_mock)

    svc = LibraryService(db_session)
    # DRAFT can be approved (via UNDER_REVIEW in workflow, but approve_release
    # only checks != APPROVED)
    result = await svc.approve_release(draft_release.id, uuid.uuid4())
    assert result.status == "APPROVED"
    assert result.approved_at is not None


@pytest.mark.asyncio
async def test_approve_nonexistent_release_raises(db_session):
    """Approving a non-existent release raises ValueError."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    db_session.execute = AsyncMock(return_value=result_mock)

    svc = LibraryService(db_session)
    with pytest.raises(ValueError, match="not found"):
        await svc.approve_release(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_submit_for_review_approved_raises(db_session):
    """Submitting an APPROVED release for review raises LibraryImmutabilityError."""
    approved_release = _make_release("APPROVED")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=approved_release)
    db_session.execute = AsyncMock(return_value=result_mock)

    svc = LibraryService(db_session)
    with pytest.raises(LibraryImmutabilityError):
        await svc.submit_for_review(approved_release.id)

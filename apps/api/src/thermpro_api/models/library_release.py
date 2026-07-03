"""Library release models — immutable once APPROVED (DR-002 / M0-09)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class LibraryRelease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A versioned library release.

    Once status transitions to APPROVED the release is immutable.
    Any change must create a new release with a new semantic version (DR-002).
    """

    __tablename__ = "library_releases"
    __table_args__ = (
        UniqueConstraint("library_name", "version", name="uq_library_release_name_version"),
    )

    library_name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="e.g. MaterialLibrary, DeviceLibrary",
    )
    version: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="Semantic version e.g. 1.2.0",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT",
        comment="DRAFT | UNDER_REVIEW | APPROVED | SUPERSEDED | WITHDRAWN",
    )
    content_hash_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 of canonical JSON of all entries",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="ISO-8601 UTC timestamp of approval",
    )

    files: Mapped[list["LibraryReleaseFile"]] = relationship(
        "LibraryReleaseFile",
        back_populates="release",
        cascade="all, delete-orphan",
    )


class LibraryReleaseFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single file (entry set) attached to a library release.

    Stored in object storage; this row holds the metadata reference.
    """

    __tablename__ = "library_release_files"

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/json")
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    release: Mapped["LibraryRelease"] = relationship("LibraryRelease", back_populates="files")

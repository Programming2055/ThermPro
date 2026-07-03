"""Dataset manifest models — pin set of approved library releases (M0-09)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DatasetManifest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A named, versioned set of library pins used together for a calculation.

    Each calculation run references exactly one manifest. The manifest
    records which library releases (and their content hashes) were active.
    """

    __tablename__ = "dataset_manifests"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_valid: Mapped[bool | None] = mapped_column(
        nullable=True,
        comment="Null = not yet validated; True = all pins resolve; False = stale or missing",
    )
    validated_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    entries: Mapped[list["DatasetManifestEntry"]] = relationship(
        "DatasetManifestEntry",
        back_populates="manifest",
        cascade="all, delete-orphan",
    )


class DatasetManifestEntry(UUIDPrimaryKeyMixin, Base):
    """A single library pin within a DatasetManifest."""

    __tablename__ = "dataset_manifest_entries"

    manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    library_key: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="JSON key in library_manifest, e.g. material_library",
    )
    library_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_releases.id", ondelete="SET NULL"),
        nullable=True,
    )

    manifest: Mapped["DatasetManifest"] = relationship(
        "DatasetManifest", back_populates="entries"
    )

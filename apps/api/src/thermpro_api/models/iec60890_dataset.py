"""
Storage for the administrator-imported IEC TR 60890 coefficient dataset.

CR-ENG-002: the IEC TR 60890 coefficient tables are licensed and are NEVER
shipped in this repository. A deployment that needs MODE 1 imports them here,
from the licensed document, and the engine receives them on the InputSnapshot.
Until that import happens, MODE 1 fails with a clear reason rather than
falling back to numbers nobody can trace.

The coefficients are versioned and content-hashed like any other library
(CR-ENG-012, M0-09): an imported dataset is immutable, and correcting it means
importing a new version, so every past result can still be reproduced.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Iec60890Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One imported release of the licensed IEC TR 60890 coefficient set."""

    __tablename__ = "iec60890_datasets"
    __table_args__ = (
        UniqueConstraint("version", name="uq_iec60890_datasets_version"),
    )

    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Semantic version of this import, e.g. '2022.1.0'.",
    )
    source_reference: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The licensed document this was transcribed from, including edition "
            "and table numbers, so a result can be traced to its source."
        ),
    )
    content_hash_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of the canonical JSON of coefficients.",
    )
    coefficients: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "c0, n, d, installation_factors, height_distribution. Licensed "
            "content: present only in deployments that hold a licence."
        ),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Exactly one dataset is active; MODE 1 runs use that one.",
    )
    imported_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

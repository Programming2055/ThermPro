"""CalculationRun model — immutable input snapshot after submission."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class CalculationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single submitted thermal calculation.

    The input_snapshot is IMMUTABLE after submission. It is stored as JSONB
    together with its SHA-256 content hash for audit and reproducibility.

    status lifecycle:
      DRAFT -> VALIDATING -> REJECTED (schema/manifest failure)
                          -> PENDING -> RUNNING -> COMPLETED
                                                -> FAILED
                                                -> CANCELLED
                          -> ENGINE_NOT_IMPLEMENTED (M1 only)
    """

    __tablename__ = "calculation_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Immutable input
    input_snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Verbatim validated InputSnapshot JSON. Never modified after submission.",
    )
    input_checksum_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 of canonical JSON of input_snapshot.",
    )

    # Calculation metadata
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="MODE_1 | MODE_2 | MODE_3 | MODE_4",
    )
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    engine_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="thermpro_engine version that ran this calculation",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", index=True,
        comment="DRAFT | VALIDATING | REJECTED | PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | ENGINE_NOT_IMPLEMENTED",
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    submitted_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Result (stored as JSONB when available; null until completed)
    result_snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="ResultSnapshot JSON. Null until status=COMPLETED.",
    )
    result_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relations
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]
        "Project", back_populates="calculation_runs"
    )
    artifacts: Mapped[list["CalculationArtifact"]] = relationship(  # type: ignore[name-defined]
        "CalculationArtifact",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )

"""Calculation artifact model — metadata in PG, file in S3."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from thermpro_api.database import Base
from thermpro_api.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class CalculationArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An output artifact produced by a calculation run.

    File bytes are stored in object storage (S3 / MinIO).
    This model stores only the metadata required to locate and describe them.
    """

    __tablename__ = "calculation_artifacts"

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. REPORT_PDF, RESULT_JSON, CONVERGENCE_PLOT, CFD_EXPORT",
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(128), nullable=False, default="application/octet-stream"
    )
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    calculation_run: Mapped["CalculationRun"] = relationship(  # type: ignore[name-defined]
        "CalculationRun", back_populates="artifacts"
    )

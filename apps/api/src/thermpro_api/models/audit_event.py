"""Audit event model — append-only, never updated or deleted."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from thermpro_api.database import Base
from thermpro_api.models.base import UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """
    Immutable audit log entry.

    Rules:
    - INSERT only; never UPDATE or DELETE.
    - All timestamps are UTC.
    - actor_id / actor_email recorded at write time (not FK to users,
      so the record survives user deletion).
    - metadata_json contains the before/after state or relevant context.
    """

    __tablename__ = "audit_events"

    # When the event occurred (server UTC clock)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="e.g. library_release.approved, calculation_run.submitted",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. LibraryRelease, CalculationRun",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Who did it
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Correlation / tracing
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Context payload
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

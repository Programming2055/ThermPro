"""Audit event service — append-only event recording."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from thermpro_api.models.audit_event import AuditEvent
from thermpro_api.services.auth import UserContext


class AuditService:
    """
    Service for recording immutable audit events.

    All events are INSERT-only. This service must never UPDATE or DELETE
    existing AuditEvent rows.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record_event(
        self,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor: UserContext | None = None,
        metadata: dict[str, Any] | None = None,
        note: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> AuditEvent:
        """
        Insert a new audit event row.

        Args:
            action: Event identifier e.g. "library_release.approved".
            entity_type: Class name of the affected entity e.g. "LibraryRelease".
            entity_id: UUID of the affected entity.
            actor: UserContext of the actor; None for system-generated events.
            metadata: Optional key-value payload (before/after state, etc.).
            note: Optional human-readable note.
            correlation_id: Optional trace/request ID for correlating events.

        Returns:
            The persisted AuditEvent.
        """
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor.user_id if actor else None,
            actor_email=actor.email if actor else None,
            correlation_id=correlation_id,
            metadata_json=metadata,
            note=note,
        )
        self._db.add(event)
        await self._db.flush()
        return event

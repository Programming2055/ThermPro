"""Authentication provider interface and development implementation."""
from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request


@dataclass(frozen=True)
class UserContext:
    """Authenticated user identity carried through a request."""

    user_id: uuid.UUID
    email: str
    role: str  # ADMIN | ENGINEER | REVIEWER | VIEWER
    display_name: str = "Unknown"


class AuthProvider(abc.ABC):
    """Abstract authentication provider."""

    @abc.abstractmethod
    async def get_current_user(self, request: Request) -> UserContext:
        """
        Extract and validate the current user from the request.

        Raises:
            HTTPException(401): If the request carries no valid credentials.
            HTTPException(403): If the user lacks the required role.
        """
        raise NotImplementedError


class DevAuthProvider(AuthProvider):
    """
    Development-only identity provider.

    Returns a fixed ENGINEER user so the API is usable without an IdP.
    Do NOT enable in production (Settings.dev_auth_enabled must be False).
    """

    _DEV_USER = UserContext(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="dev-engineer@thermpro.local",
        role="ENGINEER",
        display_name="Dev Engineer",
    )

    async def get_current_user(self, request: Request) -> UserContext:
        return self._DEV_USER


async def ensure_dev_user(db) -> None:  # type: ignore[no-untyped-def]
    """Idempotently insert the development user so FK constraints are satisfiable."""
    from sqlalchemy.dialects.postgresql import insert

    from thermpro_api.models.user import User

    u = DevAuthProvider._DEV_USER
    await db.execute(
        insert(User)
        .values(id=u.user_id, email=u.email, display_name=u.display_name, role=u.role,
                is_active=True)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.commit()


# Module-level singleton (replaced in tests)
_auth_provider: AuthProvider = DevAuthProvider()


def set_auth_provider(provider: AuthProvider) -> None:
    """Override the auth provider (used in tests)."""
    global _auth_provider
    _auth_provider = provider


async def get_current_user(request: Request) -> UserContext:
    """FastAPI dependency that yields the current authenticated user."""
    return await _auth_provider.get_current_user(request)


CurrentUser = Annotated[UserContext, Depends(get_current_user)]

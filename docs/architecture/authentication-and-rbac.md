# Authentication and RBAC

**Document ID:** THERM-ARCH-M1-004  
**Revision:** M1r1

---

## AuthProvider Interface

```python
class AuthProvider(Protocol):
    async def authenticate(self, request: Request) -> UserContext: ...

@dataclass
class UserContext:
    user_id: UUID
    email: str
    role: str  # ADMIN | REVIEWER | ENGINEER | VIEWER
```

All routers receive a `UserContext` through FastAPI dependency injection. No router has
a direct dependency on JWT libraries or session stores.

---

## DevAuthProvider (M1)

In development (`THERMPRO_DEV_AUTH_ENABLED=true`), every request is authenticated as a
synthetic dev user with role `ADMIN`. No token is required.

```python
DEV_USER = UserContext(
    user_id=UUID("00000000-0000-0000-0000-000000000001"),
    email="dev@thermpro.local",
    role="ADMIN",
)
```

This allows the frontend to make API calls without authentication headers during development.

**Important:** `DevAuthProvider` MUST NOT be shipped to production. The `THERMPRO_DEV_AUTH_ENABLED`
environment variable defaults to `true` in `docker-compose.yml` only.

---

## Role Permissions (M1)

| Action | ADMIN | REVIEWER | ENGINEER | VIEWER |
|--------|-------|----------|----------|--------|
| Create project | ✓ | ✓ | ✓ | |
| Create library release | ✓ | ✓ | | |
| Approve library release | ✓ | ✓ | | |
| Submit calculation | ✓ | ✓ | ✓ | |
| View all resources | ✓ | ✓ | ✓ | ✓ |

Role enforcement is implemented in individual routers using `current_user.role` checks.
A dedicated RBAC middleware will be introduced in a future milestone.

---

## Production Path (Future)

1. Replace `DevAuthProvider` with `JWTAuthProvider`.
2. `JWTAuthProvider` validates a Bearer token against `THERMPRO_JWT_SECRET` (HS256 in MVP,
   RS256 with JWKS in production).
3. Claims decoded from JWT populate `UserContext`.
4. No router code changes needed — the `AuthProvider` interface abstracts the mechanism.

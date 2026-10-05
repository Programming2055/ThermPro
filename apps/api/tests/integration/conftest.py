"""
Integration test fixtures.

Requires a running PostgreSQL instance. In CI this is provided by
docker-compose or testcontainers. Set THERMPRO_DATABASE_URL to override.

These tests are marked with @pytest.mark.integration and are excluded from
the default test run. Run with: pytest tests/integration/ -m integration
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from thermpro_api.database import Base, get_db
from thermpro_api.main import app
from thermpro_api.services.auth import (
    AuthProvider,
    UserContext,
    set_auth_provider,
)

TEST_DB_URL = os.getenv(
    "THERMPRO_TEST_DATABASE_URL",
    "postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create the schema in the test database and point the app at it.

    Creating the tables is not enough on its own: the application resolves
    its own engine from Settings, so without overriding `get_db` the
    requests under test would run against the developer's real database —
    or, more often, against one that does not exist.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


#: The identities the auth providers hand out. Rows that own projects and
#: audit events must exist, or every write fails on a foreign key.
SEEDED_USERS = (
    (
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "dev-engineer@thermpro.local",
        "Dev Engineer",
        "ENGINEER",
    ),
    (
        uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "dev-admin@thermpro.local",
        "Dev Admin",
        "ADMIN",
    ),
)


@pytest_asyncio.fixture
async def clean_tables(test_engine):
    """
    Empty every table between tests, then re-seed the users.

    Integration tests share one schema for speed, so without this a test
    that counts rows would depend on which tests ran before it.
    """
    async with test_engine.begin() as conn:
        tables = ", ".join(
            f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
        )
        if tables:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        for user_id, email, display_name, role in SEEDED_USERS:
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, display_name, role, is_active) "
                    "VALUES (:id, :email, :display_name, :role, true)"
                ),
                {
                    "id": user_id,
                    "email": email,
                    "display_name": display_name,
                    "role": role,
                },
            )
    yield


@pytest_asyncio.fixture
async def client(test_engine, clean_tables):
    """HTTP test client with ASGI transport — no real server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class _AdminAuthProvider(AuthProvider):
    """An ADMIN identity, for the endpoints that require one."""

    _ADMIN = UserContext(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="dev-admin@thermpro.local",
        role="ADMIN",
        display_name="Dev Admin",
    )

    async def get_current_user(self, request: Request) -> UserContext:
        return self._ADMIN


@pytest.fixture
def as_admin() -> Iterator[None]:
    """
    Run a test as an administrator.

    Importing the licensed IEC TR 60890 dataset is an administrator action
    (CR-ENG-002), and the dev provider hands out an ENGINEER. Testing that
    path by skipping it would leave the rule unverified.
    """
    from thermpro_api.services.auth import DevAuthProvider

    set_auth_provider(_AdminAuthProvider())
    try:
        yield
    finally:
        set_auth_provider(DevAuthProvider())


@pytest_asyncio.fixture
async def approved_libraries(test_engine, clean_tables):
    """
    APPROVED releases matching the reference model's library pins.

    CR-TECH-002 requires every InputSnapshot to name the libraries it was
    built from, and the API refuses a pin that does not resolve to an
    APPROVED release. Emptying the manifest to dodge that would test a path
    no real submission takes.
    """
    from thermal_core.reference_model import m003_document

    manifest = m003_document()["library_manifest"]
    async with test_engine.begin() as conn:
        for pin in manifest.values():
            await conn.execute(
                text(
                    "INSERT INTO library_releases "
                    "(id, library_name, version, status, content_hash_sha256) "
                    "VALUES (:id, :name, :version, 'APPROVED', :digest)"
                ),
                {
                    "id": uuid.uuid4(),
                    "name": pin["name"],
                    "version": pin["version"],
                    "digest": pin["content_hash_sha256"],
                },
            )
    yield manifest

"""
Integration test fixtures.

Requires a running PostgreSQL instance. In CI this is provided by
docker-compose or testcontainers. Set THERMPRO_DATABASE_URL to override.

These tests are marked with @pytest.mark.integration and are excluded from
the default test run. Run with: pytest tests/integration/ -m integration
"""
from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from thermpro_api.database import Base
from thermpro_api.main import app

TEST_DB_URL = os.getenv(
    "THERMPRO_TEST_DATABASE_URL",
    "postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create tables in the test database and return the engine."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    """HTTP test client with ASGI transport — no real server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

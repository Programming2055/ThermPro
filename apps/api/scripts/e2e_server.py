"""
Start the API against a throw-away database for end-to-end tests.

Drops and recreates all tables, seeds the development user, then serves on
the given port. Never point THERMPRO_DATABASE_URL at real data.
"""
from __future__ import annotations

import asyncio
import os
import sys

import uvicorn

os.environ.setdefault(
    "THERMPRO_DATABASE_URL",
    "postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro_e2e",
)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from thermpro_api import models  # noqa: E402,F401  (registers tables)
from thermpro_api.database import Base  # noqa: E402
from thermpro_api.services.auth import ensure_dev_user  # noqa: E402


async def prepare() -> None:
    engine = create_async_engine(os.environ["THERMPRO_DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        await ensure_dev_user(session)
    await engine.dispose()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    asyncio.run(prepare())
    uvicorn.run("thermpro_api.main:app", host="127.0.0.1", port=port, log_level="warning")

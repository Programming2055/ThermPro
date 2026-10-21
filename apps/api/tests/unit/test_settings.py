import pytest

from thermpro_api.settings import Settings


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://", "postgresql+psycopg://"])
def test_provider_style_urls_use_psycopg3_dialect(scheme):
    s = Settings(database_url=f"{scheme}u:p@host:5432/db")
    assert str(s.database_url).startswith("postgresql+psycopg://u:p@host:5432/db")


def test_serverless_engine_uses_no_pool(monkeypatch):
    from sqlalchemy.pool import NullPool

    from thermpro_api import database, settings

    monkeypatch.setattr(settings, "_settings", Settings(serverless=True))
    monkeypatch.setattr(database, "_engine", None)
    engine = database.get_engine()
    assert isinstance(engine.sync_engine.pool, NullPool)
    monkeypatch.setattr(database, "_engine", None)

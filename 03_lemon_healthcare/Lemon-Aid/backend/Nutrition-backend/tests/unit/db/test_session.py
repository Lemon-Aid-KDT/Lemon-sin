"""Database session helper tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.dependencies import get_async_session
from src.db.session import dispose_engine, get_engine, get_sessionmaker


class DummySettings:
    """Minimal settings object for database session tests.

    Attributes:
        database_url: SQLAlchemy async database URL.
    """

    database_url = "postgresql+asyncpg://user:pass@localhost:5432/lemon_test"


def get_dummy_settings() -> DummySettings:
    """Return deterministic settings for session tests.

    Returns:
        Dummy settings object with a PostgreSQL async URL.
    """
    return DummySettings()


async def test_get_engine_uses_configured_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the engine is created from the application settings."""
    await dispose_engine()
    monkeypatch.setattr("src.db.session.get_settings", get_dummy_settings)

    engine = get_engine()

    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == "lemon_test"

    await dispose_engine()


async def test_get_sessionmaker_returns_async_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the session factory creates AsyncSession instances."""
    await dispose_engine()
    monkeypatch.setattr("src.db.session.get_settings", get_dummy_settings)

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        assert isinstance(session, AsyncSession)

    await dispose_engine()


async def test_get_async_session_dependency_yields_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the FastAPI dependency yields an AsyncSession."""
    await dispose_engine()
    monkeypatch.setattr("src.db.session.get_settings", get_dummy_settings)

    async for session in get_async_session():
        assert isinstance(session, AsyncSession)
        break

    await dispose_engine()

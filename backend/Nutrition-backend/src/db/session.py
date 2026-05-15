"""Async SQLAlchemy engine and session factory helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings


@dataclass
class _DatabaseState:
    """Hold lazy database infrastructure instances.

    Attributes:
        engine: Cached async SQLAlchemy engine.
        sessionmaker: Cached async session factory.
    """

    engine: AsyncEngine | None = None
    sessionmaker: async_sessionmaker[AsyncSession] | None = None


_state = _DatabaseState()


def get_engine() -> AsyncEngine:
    """Return the shared async SQLAlchemy engine.

    Returns:
        Lazily initialized async engine using the configured database URL.
    """
    if _state.engine is None:
        settings = get_settings()
        _state.engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    return _state.engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory.

    Returns:
        Async sessionmaker configured for request-scoped database sessions.
    """
    if _state.sessionmaker is None:
        _state.sessionmaker = async_sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )

    return _state.sessionmaker


async def dispose_engine() -> None:
    """Dispose the shared async engine and reset cached factories.

    Returns:
        None.
    """
    if _state.engine is not None:
        await _state.engine.dispose()

    _state.engine = None
    _state.sessionmaker = None

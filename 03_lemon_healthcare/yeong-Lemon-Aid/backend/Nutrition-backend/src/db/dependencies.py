"""FastAPI database dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_sessionmaker


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async database session.

    This dependency does not auto-commit. Write operations must use an
    explicit service-level transaction such as ``async with session.begin()``.

    Yields:
        SQLAlchemy AsyncSession bound to the configured async engine.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session

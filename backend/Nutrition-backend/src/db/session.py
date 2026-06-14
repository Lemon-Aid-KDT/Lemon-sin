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
    audit_engine: AsyncEngine | None = None
    audit_sessionmaker: async_sessionmaker[AsyncSession] | None = None


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


def get_audit_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for privileged audit writes.

    Audit rows are written out-of-band of the request transaction (preserving
    the legacy "commit the audit immediately" semantics). Under the FORCE RLS
    Stage-2 posture the request role (``lemon_app``) holds only SELECT on
    ``audit_logs``, so audits must use a privileged connection: set
    ``AUDIT_DATABASE_URL`` to a role that can INSERT audit rows. When it is unset
    (or equal to ``DATABASE_URL``, e.g. today's superuser request role) the main
    factory is reused — but each audit still opens its own short-lived session,
    so the write is always independent of the request transaction.

    Returns:
        Async sessionmaker bound to the audit (privileged) engine.
    """
    settings = get_settings()
    audit_url = settings.audit_database_url
    if audit_url is None or audit_url == settings.database_url:
        return get_sessionmaker()

    if _state.audit_sessionmaker is None:
        _state.audit_engine = create_async_engine(audit_url, pool_pre_ping=True)
        _state.audit_sessionmaker = async_sessionmaker(
            bind=_state.audit_engine,
            autoflush=False,
            expire_on_commit=False,
        )

    return _state.audit_sessionmaker


async def dispose_engine() -> None:
    """Dispose the shared async engines and reset cached factories.

    Returns:
        None.
    """
    if _state.engine is not None:
        await _state.engine.dispose()
    if _state.audit_engine is not None:
        await _state.audit_engine.dispose()

    _state.engine = None
    _state.sessionmaker = None
    _state.audit_engine = None
    _state.audit_sessionmaker = None

"""FastAPI database dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.db.rls_context import set_request_rls_context
from src.db.session import get_sessionmaker
from src.db.tx import REQUEST_MANAGED_TX
from src.security.auth import AuthenticatedUser, require_current_user
from src.security.privacy import hash_actor_subject
from src.security.subjects import build_owner_subject


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


async def get_rls_context_session(
    current_user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session inside a transaction with RLS GUCs set.

    This is the FORCE RLS rollout's Stage-1 request seam
    (docs/2026-05-31-force-rls-rollout-design.md): it opens a single
    request-scoped transaction and sets the owner-subject GUCs that the
    migration 0023b owner policies read. While the app still connects as the
    superuser ``lemon`` the GUCs are ignored (superuser bypasses RLS), so
    adopting this dependency is safe before Stage-2 flips ``DATABASE_URL`` to the
    non-superuser ``lemon_app`` role.

    Adoption contract: a route using this session relies on the request-scoped
    transaction opened here and must NOT call ``session.begin()`` or
    ``session.commit()`` itself — committing mid-request releases the
    transaction-local GUCs. Routes that manage their own transactions keep using
    ``get_async_session`` until they are migrated as part of the staged rollout.

    Args:
        current_user: Authenticated principal resolved before the route runs.
        settings: Runtime settings supplying the privacy hash secret.

    Yields:
        AsyncSession with ``app.current_subject`` / ``app.current_subject_hash``
        set for the owner-scoped RLS policies. A missing subject is impossible
        here because auth has already validated it; the policies still fail
        closed (empty GUC matches no row) as a defensive default.
    """
    owner_subject = build_owner_subject(current_user)
    subject_hash = hash_actor_subject(current_user, settings)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session, session.begin():
        await set_request_rls_context(
            session,
            subject=owner_subject,
            subject_hash=subject_hash,
        )
        # Mark this request as owning the transaction so write/audit services
        # participate (flush only) instead of committing — committing mid-request
        # would drop the transaction-local RLS GUCs set above. See src/db/tx.py.
        session.info[REQUEST_MANAGED_TX] = True
        yield session


@asynccontextmanager
async def rls_request_transaction(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    settings: Settings,
) -> AsyncIterator[AsyncSession]:
    """Open a route-owned RLS transaction that commits before the route returns.

    Same owner-scoped, single-transaction semantics as
    :func:`get_rls_context_session`, but the request transaction is opened and
    committed *inside the route body* rather than at dependency teardown. This
    is required for routes that schedule post-commit work via FastAPI
    ``BackgroundTasks``: Starlette runs background tasks **before** the
    yield-dependency teardown, so a ``get_rls_context_session`` route (which
    commits at teardown) would run the background task before its writes are
    durable. Committing in the route body — which happens before the response is
    sent and therefore before the background task runs — keeps the deferred
    fresh-session work (e.g. learning image storage) safely post-commit.

    Use with ``get_async_session`` (which opens no transaction). The wrapped
    block must perform all owner-scoped reads/writes via ``persist_scope`` and
    must not call ``session.commit()``/``session.begin()`` itself; the context
    manager owns begin + commit (rollback on error), and clears the
    request-managed marker on exit so any later use of the session reverts to
    legacy ownership.

    Args:
        session: Request-scoped async session from ``get_async_session``.
        current_user: Authenticated principal whose owner subject scopes the RLS GUCs.
        settings: Runtime settings supplying the privacy hash secret.

    Yields:
        The same session, inside an open transaction with owner-subject GUCs set.
    """
    owner_subject = build_owner_subject(current_user)
    subject_hash = hash_actor_subject(current_user, settings)
    async with session.begin():
        await set_request_rls_context(
            session,
            subject=owner_subject,
            subject_hash=subject_hash,
        )
        session.info[REQUEST_MANAGED_TX] = True
        try:
            yield session
        finally:
            session.info.pop(REQUEST_MANAGED_TX, None)

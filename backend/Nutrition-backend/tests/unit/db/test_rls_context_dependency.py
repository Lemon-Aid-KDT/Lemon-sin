"""Unit tests for the RLS-context request session dependency (Stage-1 seam)."""

from __future__ import annotations

from typing import Any

import pytest
from src.config import Settings
from src.db import dependencies as deps
from src.db.dependencies import get_rls_context_session, rls_request_transaction
from src.db.tx import REQUEST_MANAGED_TX
from src.security.auth import AuthenticatedUser


class _FakeTransaction:
    """Fake async transaction context manager."""

    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeTransaction:
        self._session.begun = True
        return self

    async def __aexit__(self, *exc: object) -> bool:
        if exc and exc[0] is not None:
            self._session.rolled_back = True
        else:
            self._session.committed = True
        return False


class _FakeSession:
    """Fake async session recording set_config executions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.begun = False
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.info: dict[str, Any] = {}

    async def execute(self, statement: object, params: dict[str, Any]) -> None:
        """Record an executed statement and its bind params."""
        self.calls.append((str(statement), params))

    def begin(self) -> _FakeTransaction:
        """Return a fake transaction context manager."""
        return _FakeTransaction(self)

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        self.closed = True
        return False


def _fake_sessionmaker(session: _FakeSession) -> Any:
    """Return a callable yielding the given fake session."""

    def _maker() -> _FakeSession:
        return session

    return _maker


@pytest.mark.asyncio
async def test_get_rls_context_session_sets_owner_gucs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dependency opens a transaction and sets both owner GUCs from the user."""
    session = _FakeSession()
    monkeypatch.setattr(deps, "get_sessionmaker", lambda: _fake_sessionmaker(session))
    user = AuthenticatedUser(subject="user-1", issuer="https://issuer.example/")
    settings = Settings(_env_file=None)

    agen = get_rls_context_session(user, settings)
    yielded = await agen.__anext__()

    assert yielded is session
    assert session.begun is True  # GUCs are set inside a transaction
    # Subject GUC is set before the hash GUC (set_request_rls_context order).
    names = [params["name"] for _sql, params in session.calls]
    assert names == ["app.current_subject", "app.current_subject_hash"]
    values = {params["name"]: params["value"] for _sql, params in session.calls}
    assert values["app.current_subject"] == "https://issuer.example/::user-1"
    assert values["app.current_subject_hash"]  # non-empty HMAC
    assert values["app.current_subject_hash"] != values["app.current_subject"]

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()
    assert session.committed is True
    assert session.closed is True


@pytest.mark.asyncio
async def test_get_rls_context_session_rejects_empty_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An invalid (empty) subject fails closed before any session work."""
    session = _FakeSession()
    monkeypatch.setattr(deps, "get_sessionmaker", lambda: _fake_sessionmaker(session))
    user = AuthenticatedUser(subject="", issuer="https://issuer.example/")
    settings = Settings(_env_file=None)

    agen = get_rls_context_session(user, settings)
    with pytest.raises(ValueError, match="owner subject"):
        await agen.__anext__()
    assert session.calls == []  # no GUCs set when the subject is invalid


@pytest.mark.asyncio
async def test_rls_request_transaction_sets_gucs_marks_and_commits() -> None:
    """The route-owned helper opens a tx, sets owner GUCs, marks request-managed."""
    session = _FakeSession()
    user = AuthenticatedUser(subject="user-1", issuer="https://issuer.example/")
    settings = Settings(_env_file=None)

    async with rls_request_transaction(session, user, settings) as yielded:  # type: ignore[arg-type]
        assert yielded is session
        assert session.begun is True
        # Owner-scoped writes participate (flush only) while inside the block.
        assert session.info.get(REQUEST_MANAGED_TX) is True
        names = [params["name"] for _sql, params in session.calls]
        assert names == ["app.current_subject", "app.current_subject_hash"]
        values = {params["name"]: params["value"] for _sql, params in session.calls}
        assert values["app.current_subject"] == "https://issuer.example/::user-1"
        assert values["app.current_subject_hash"]

    # Commit happens at block exit (before the route returns); marker cleared.
    assert session.committed is True
    assert REQUEST_MANAGED_TX not in session.info


@pytest.mark.asyncio
async def test_rls_request_transaction_clears_marker_on_error() -> None:
    """An error inside the block propagates and still clears the request marker."""
    session = _FakeSession()
    user = AuthenticatedUser(subject="user-1", issuer="https://issuer.example/")
    settings = Settings(_env_file=None)

    with pytest.raises(RuntimeError, match="boom"):
        async with rls_request_transaction(session, user, settings):  # type: ignore[arg-type]
            assert session.info.get(REQUEST_MANAGED_TX) is True
            raise RuntimeError("boom")

    assert REQUEST_MANAGED_TX not in session.info
    assert session.rolled_back is True  # the request transaction rolls back on error
    assert session.committed is False

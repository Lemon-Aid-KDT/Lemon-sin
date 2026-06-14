"""Unit tests for ambient-transaction-aware audit writing (services/privacy.py).

Verifies record_audit_event's three branches without a DB/Request: legacy
own-commit, request-managed success (flush, no commit), and request-managed
failure (out-of-band commit). _build_audit_log / _commit_audit_out_of_band are
monkeypatched so the control flow is asserted in isolation.
"""

from __future__ import annotations

import pytest

from src.db.tx import REQUEST_MANAGED_TX
from src.services import privacy


class _FakeSession:
    def __init__(self, *, request_managed: bool = False) -> None:
        self.info: dict[str, object] = (
            {REQUEST_MANAGED_TX: True} if request_managed else {}
        )
        self.calls: list[str] = []

    def add(self, _obj: object) -> None:
        self.calls.append("add")

    async def flush(self) -> None:
        self.calls.append("flush")

    async def commit(self) -> None:
        self.calls.append("commit")


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> tuple[object, list[object]]:
    sentinel = object()
    monkeypatch.setattr(privacy, "_build_audit_log", lambda **_kw: sentinel)
    out_of_band: list[object] = []

    async def _fake_out_of_band(audit_log: object) -> object:
        out_of_band.append(audit_log)
        return audit_log

    monkeypatch.setattr(privacy, "_commit_audit_out_of_band", _fake_out_of_band)
    return sentinel, out_of_band


async def _record(session: _FakeSession, **extra: object) -> object:
    return await privacy.record_audit_event(
        session=session,  # type: ignore[arg-type]
        user=object(),  # type: ignore[arg-type]
        action="action",
        resource_type="resource",
        resource_id=None,
        outcome="success",
        request=object(),  # type: ignore[arg-type]
        settings=object(),  # type: ignore[arg-type]
        **extra,
    )


@pytest.mark.asyncio
async def test_legacy_session_adds_then_commits(
    patched: tuple[object, list[object]],
) -> None:
    sentinel, out_of_band = patched
    session = _FakeSession()
    result = await _record(session)
    assert result is sentinel
    assert session.calls == ["add", "commit"]
    assert out_of_band == []


@pytest.mark.asyncio
async def test_request_managed_success_flushes_not_commits(
    patched: tuple[object, list[object]],
) -> None:
    sentinel, out_of_band = patched
    session = _FakeSession(request_managed=True)
    result = await _record(session)
    assert result is sentinel
    assert session.calls == ["add", "flush"]
    assert "commit" not in session.calls
    assert out_of_band == []


@pytest.mark.asyncio
async def test_request_managed_failure_commits_out_of_band(
    patched: tuple[object, list[object]],
) -> None:
    sentinel, out_of_band = patched
    session = _FakeSession(request_managed=True)
    result = await _record(session, on_failure=True)
    assert result is sentinel
    # The audit rides its own transaction; the request session is untouched.
    assert out_of_band == [sentinel]
    assert session.calls == []

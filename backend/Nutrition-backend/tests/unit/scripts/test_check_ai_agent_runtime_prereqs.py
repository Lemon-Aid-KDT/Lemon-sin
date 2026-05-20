"""Tests for AI Agent runtime prerequisite checks."""

from __future__ import annotations

from scripts import check_ai_agent_runtime_prereqs as prereqs


def test_database_host_port_uses_test_database_url_port() -> None:
    """Verify PostgreSQL smoke readiness follows TEST_DATABASE_URL, not port 5432."""
    host, port = prereqs._database_host_port(
        "postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_smoke"
    )

    assert host == "127.0.0.1"
    assert port == 55432


def test_database_host_port_defaults_to_local_postgres() -> None:
    """Verify missing TEST_DATABASE_URL reports the default local PostgreSQL port."""
    host, port = prereqs._database_host_port(None)

    assert host == "127.0.0.1"
    assert port == 5432


def test_http_host_port_uses_sglang_base_url_port() -> None:
    """Verify SGLang readiness follows SGLANG_BASE_URL."""
    host, port = prereqs._http_host_port(
        "http://localhost:31000/v1",
        default_port=30000,
    )

    assert host == "localhost"
    assert port == 31000

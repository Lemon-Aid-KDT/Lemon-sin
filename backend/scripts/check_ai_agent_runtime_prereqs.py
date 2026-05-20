"""Check local prerequisites for AI Agent live smoke tests."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import socket
from urllib.parse import urlparse


def main() -> int:
    """Print local readiness for PostgreSQL and SGLang smoke tests."""
    postgres_host, postgres_port = _database_host_port(os.getenv("TEST_DATABASE_URL"))
    sglang_host, sglang_port = _http_host_port(
        os.getenv("SGLANG_BASE_URL", "http://127.0.0.1:30000/v1"),
        default_port=30000,
    )
    checks = [
        ("postgres command", _command_available("postgres")),
        ("pg_ctl command", _command_available("pg_ctl")),
        ("psql command", _command_available("psql")),
        ("docker command", _command_available("docker")),
        ("wsl command", _command_available("wsl")),
        ("conda executable", _conda_available()),
        (f"PostgreSQL port {postgres_host}:{postgres_port}", _port_open(postgres_host, postgres_port)),
        (f"SGLang port {sglang_host}:{sglang_port}", _port_open(sglang_host, sglang_port)),
        ("sglang Python package", _module_available("sglang")),
        ("torch Python package", _module_available("torch")),
        ("RUN_POSTGRES_MIGRATION_SMOKE", os.getenv("RUN_POSTGRES_MIGRATION_SMOKE") == "1"),
        ("TEST_DATABASE_URL", bool(os.getenv("TEST_DATABASE_URL"))),
        ("RUN_SGLANG_SMOKE", os.getenv("RUN_SGLANG_SMOKE") == "1"),
        ("SGLANG_MODEL", bool(os.getenv("SGLANG_MODEL"))),
    ]

    for label, ok in checks:
        print(f"{label}: {'ok' if ok else 'missing'}")

    postgres_ready = (
        os.getenv("RUN_POSTGRES_MIGRATION_SMOKE") == "1"
        and bool(os.getenv("TEST_DATABASE_URL"))
        and _port_open(postgres_host, postgres_port)
    )
    sglang_ready = (
        os.getenv("RUN_SGLANG_SMOKE") == "1"
        and bool(os.getenv("SGLANG_MODEL"))
        and _port_open(sglang_host, sglang_port)
    )

    if not postgres_ready:
        print(
            "PostgreSQL live migration smoke is not ready. "
            "Set RUN_POSTGRES_MIGRATION_SMOKE=1, TEST_DATABASE_URL, and start a test DB."
        )
    if not sglang_ready:
        print(
            "SGLang live smoke is not ready. "
            "Set RUN_SGLANG_SMOKE=1, SGLANG_MODEL, and start a local SGLang server."
        )

    return 0 if postgres_ready and sglang_ready else 1


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _conda_available() -> bool:
    """Return whether conda is available on PATH or in common user-local installs."""
    if shutil.which("conda") is not None:
        return True
    home = Path.home()
    candidates = [
        home / "anaconda3" / "Scripts" / "conda.exe",
        home / "miniconda3" / "Scripts" / "conda.exe",
    ]
    return any(path.exists() for path in candidates)


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _database_host_port(database_url: str | None) -> tuple[str, int]:
    """Extract host and port from a SQLAlchemy database URL."""
    if not database_url:
        return "127.0.0.1", 5432
    parsed = urlparse(database_url)
    return parsed.hostname or "127.0.0.1", parsed.port or 5432


def _http_host_port(url: str, *, default_port: int) -> tuple[str, int]:
    """Extract host and port from a local HTTP endpoint."""
    parsed = urlparse(url)
    return parsed.hostname or "127.0.0.1", parsed.port or default_port


def _port_open(host: str, port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


if __name__ == "__main__":
    raise SystemExit(main())

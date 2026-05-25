"""Check local prerequisites for AI Agent live smoke tests."""

from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
NUTRITION_BACKEND_DIR = BACKEND_DIR / "Nutrition-backend"
AI_AGENT_CHAT_SRC_DIR = BACKEND_DIR / "ai_agent_chat" / "src"
DEFAULT_POSTGRES_SMOKE_PORT = 55432
for import_path in (NUTRITION_BACKEND_DIR, AI_AGENT_CHAT_SRC_DIR):
    import_path_text = str(import_path)
    if import_path_text not in sys.path:
        sys.path.insert(0, import_path_text)

from src.config import Settings  # noqa: E402
from src.services.medical_source_readiness import build_medical_source_readiness  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    """Print local readiness for PostgreSQL and SGLang smoke tests."""
    args = _parse_args(argv)
    settings = Settings(_env_file=None)
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
    for line in _medical_source_readiness_lines(settings):
        print(line)

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
    medical_source_failures = _required_medical_source_failures(
        settings,
        args.require_medical_sources,
    )
    if medical_source_failures:
        print(
            "Required medical sources are not ready: "
            + ", ".join(medical_source_failures)
        )

    return 0 if postgres_ready and sglang_ready and not medical_source_failures else 1


def _parse_args(argv: Sequence[str] | None) -> Namespace:
    parser = ArgumentParser(
        description="Check local AI Agent runtime and optional medical source gates."
    )
    parser.add_argument(
        "--require-medical-sources",
        nargs="*",
        default=(),
        metavar="SOURCE_ID",
        help=(
            "Fail if any listed reviewed medical source is not ready. "
            "Example: --require-medical-sources kdca-healthinfo mfds-drug-safety"
        ),
    )
    return parser.parse_args(argv)


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
        return "127.0.0.1", DEFAULT_POSTGRES_SMOKE_PORT
    parsed = urlparse(database_url)
    return parsed.hostname or "127.0.0.1", parsed.port or DEFAULT_POSTGRES_SMOKE_PORT


def _http_host_port(url: str, *, default_port: int) -> tuple[str, int]:
    """Extract host and port from a local HTTP endpoint."""
    parsed = urlparse(url)
    return parsed.hostname or "127.0.0.1", parsed.port or default_port


def _medical_source_readiness_lines(
    settings: Settings,
    *,
    today: date | None = None,
) -> list[str]:
    readiness = build_medical_source_readiness(settings, today=today)
    lines: list[str] = []
    for source in readiness.sources:
        state = "ok" if source.ready else "missing"
        detail = f" ({source.error_code})" if source.error_code else ""
        lines.append(f"medical source {source.source_id}: {state}{detail}")
    return lines


def _required_medical_source_failures(
    settings: Settings,
    required_source_ids: Sequence[str],
    *,
    today: date | None = None,
) -> list[str]:
    """Return strict readiness failures for explicitly required medical sources."""
    readiness = build_medical_source_readiness(settings, today=today)
    by_source_id = {source.source_id: source for source in readiness.sources}
    failures: list[str] = []
    for source_id in required_source_ids:
        source = by_source_id.get(source_id)
        if source is None:
            failures.append(f"{source_id}=unknown_source")
        elif not source.ready:
            failures.append(f"{source_id}={source.error_code or 'not_ready'}")
    return failures


def _port_open(host: str, port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


if __name__ == "__main__":
    raise SystemExit(main())

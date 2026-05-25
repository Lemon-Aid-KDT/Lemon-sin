"""Check local prerequisites for AI Agent live smoke tests."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

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
    settings = _build_settings(args)
    postgres_host, postgres_port = _database_host_port(os.getenv("TEST_DATABASE_URL"))
    sglang_host, sglang_port = _http_host_port(
        os.getenv("SGLANG_BASE_URL", "http://127.0.0.1:30000/v1"),
        default_port=30000,
    )
    ollama_host, ollama_port = _http_host_port(settings.ollama_base_url, default_port=11434)
    checks = [
        ("postgres command", _command_available("postgres")),
        ("pg_ctl command", _command_available("pg_ctl")),
        ("psql command", _command_available("psql")),
        ("docker command", _command_available("docker")),
        ("wsl command", _command_available("wsl")),
        ("conda executable", _conda_available()),
        (f"PostgreSQL port {postgres_host}:{postgres_port}", _port_open(postgres_host, postgres_port)),
        (f"SGLang port {sglang_host}:{sglang_port}", _port_open(sglang_host, sglang_port)),
        (f"Ollama port {ollama_host}:{ollama_port}", _port_open(ollama_host, ollama_port)),
        ("sglang Python package", _module_available("sglang")),
        ("torch Python package", _module_available("torch")),
        ("RUN_POSTGRES_MIGRATION_SMOKE", os.getenv("RUN_POSTGRES_MIGRATION_SMOKE") == "1"),
        ("TEST_DATABASE_URL", bool(os.getenv("TEST_DATABASE_URL"))),
        ("RUN_SGLANG_SMOKE", os.getenv("RUN_SGLANG_SMOKE") == "1"),
        ("SGLANG_MODEL", bool(os.getenv("SGLANG_MODEL"))),
        ("OLLAMA_MODEL", bool(settings.ollama_model)),
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
    ollama_failure = _ollama_readiness_failure(settings) if args.require_ollama else None
    if ollama_failure:
        print(f"Required Ollama runtime is not ready: ollama={ollama_failure}")

    return (
        0
        if postgres_ready and sglang_ready and not medical_source_failures and not ollama_failure
        else 1
    )


def _parse_args(argv: Sequence[str] | None) -> Namespace:
    parser = ArgumentParser(
        description="Check local AI Agent runtime and optional medical source gates."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Load settings from this dotenv file instead of the default project/backend .env files.",
    )
    parser.add_argument(
        "--ignore-env-file",
        action="store_true",
        help="Ignore dotenv files and read settings only from the process environment.",
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
    parser.add_argument(
        "--require-ollama",
        action="store_true",
        help="Fail if the configured local Ollama server or model is not available.",
    )
    return parser.parse_args(argv)


def _build_settings(args: Namespace) -> Settings:
    """Build runtime settings using the same dotenv behavior as the app by default."""
    if args.ignore_env_file:
        return Settings(_env_file=None)
    if args.env_file is not None:
        return Settings(_env_file=args.env_file)
    return Settings()


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


def _ollama_readiness_failure(
    settings: Settings,
    *,
    port_open: bool | None = None,
    model_names: Sequence[str] | None = None,
) -> str | None:
    """Return a stable failure code for required local Ollama readiness."""
    if not settings.ollama_model:
        return "missing_model"
    host, port = _http_host_port(settings.ollama_base_url, default_port=11434)
    if port_open is None:
        port_open = _port_open(host, port)
    if not port_open:
        return "port_closed"
    if model_names is None:
        try:
            model_names = _ollama_model_names(settings)
        except RuntimeError:
            return "tags_unavailable"
    if settings.ollama_model not in model_names:
        return "model_missing"
    return None


def _ollama_model_names(settings: Settings) -> tuple[str, ...]:
    """Fetch sanitized model tags from the local Ollama `/api/tags` endpoint."""
    endpoint = _join_url(settings.ollama_base_url, "/api/tags")
    try:
        with urlopen(endpoint, timeout=float(settings.ollama_timeout_sec)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama tags request failed.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Ollama tags response is not an object.")
    models = payload.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Ollama tags response has no models list.")
    names: list[str] = []
    for model in models:
        if isinstance(model, dict) and isinstance(model.get("name"), str):
            names.append(model["name"])
    return tuple(names)


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _port_open(host: str, port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


if __name__ == "__main__":
    raise SystemExit(main())

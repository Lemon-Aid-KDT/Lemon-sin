"""Tests for AI Agent runtime prerequisite checks."""

from __future__ import annotations

from datetime import date

from src.config import Settings

from scripts import check_ai_agent_runtime_prereqs as prereqs


def test_database_host_port_uses_test_database_url_port() -> None:
    """Verify PostgreSQL smoke readiness follows TEST_DATABASE_URL, not port 5432."""
    host, port = prereqs._database_host_port(
        "postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_smoke"
    )

    assert host == "127.0.0.1"
    assert port == 55432


def test_database_host_port_defaults_to_local_postgres() -> None:
    """Verify missing TEST_DATABASE_URL reports the local dev stack PostgreSQL port."""
    host, port = prereqs._database_host_port(None)

    assert host == "127.0.0.1"
    assert port == 55432


def test_http_host_port_uses_sglang_base_url_port() -> None:
    """Verify SGLang readiness follows SGLANG_BASE_URL."""
    host, port = prereqs._http_host_port(
        "http://localhost:31000/v1",
        default_port=30000,
    )

    assert host == "localhost"
    assert port == 31000


def test_medical_source_readiness_lines_show_keyed_source_status() -> None:
    """Verify preflight output includes non-secret medical source readiness."""
    lines = prereqs._medical_source_readiness_lines(
        Settings(_env_file=None),
        today=date(2026, 5, 24),
    )

    assert "medical source kdca-healthinfo: missing (missing_api_key)" in lines
    assert "medical source kdris-2025: ok" in lines
    assert "medical source semantic-scholar: missing (not_reviewed)" in lines


def test_required_medical_source_failures_report_missing_keys() -> None:
    """Verify strict medical-source gates fail when required keys are absent."""
    failures = prereqs._required_medical_source_failures(
        Settings(_env_file=None),
        ("kdca-healthinfo", "mfds-drug-safety"),
        today=date(2026, 5, 24),
    )

    assert failures == [
        "kdca-healthinfo=missing_api_key",
        "mfds-drug-safety=missing_api_key",
    ]


def test_required_medical_source_failures_pass_with_configured_keys() -> None:
    """Verify strict medical-source gates pass once required source keys exist."""
    failures = prereqs._required_medical_source_failures(
        Settings(
            _env_file=None,
            kdca_healthinfo_api_key="kdca-key",
            mfds_data_api_key="mfds-key",
        ),
        ("kdca-healthinfo", "mfds-drug-safety"),
        today=date(2026, 5, 24),
    )

    assert failures == []


def test_required_medical_source_failures_report_unknown_source() -> None:
    """Verify strict gates fail loudly for misspelled source IDs."""
    failures = prereqs._required_medical_source_failures(
        Settings(_env_file=None),
        ("not-a-source",),
        today=date(2026, 5, 24),
    )

    assert failures == ["not-a-source=unknown_source"]


def test_ollama_readiness_failure_reports_closed_port() -> None:
    """Verify strict Ollama gates fail when the local API port is closed."""
    failure = prereqs._ollama_readiness_failure(
        Settings(_env_file=None, ollama_model="qwen3.5:9b"),
        port_open=False,
        model_names=("qwen3.5:9b",),
    )

    assert failure == "port_closed"


def test_ollama_readiness_failure_reports_missing_model() -> None:
    """Verify strict Ollama gates fail when the configured model is absent."""
    failure = prereqs._ollama_readiness_failure(
        Settings(_env_file=None, ollama_model="qwen3.5:9b"),
        port_open=True,
        model_names=("qwen2.5:7b",),
    )

    assert failure == "model_missing"


def test_ollama_readiness_failure_passes_when_model_is_available() -> None:
    """Verify strict Ollama gates pass with an open port and configured model."""
    failure = prereqs._ollama_readiness_failure(
        Settings(_env_file=None, ollama_model="qwen3.5:9b"),
        port_open=True,
        model_names=("qwen3.5:9b", "qwen2.5:7b"),
    )

    assert failure is None

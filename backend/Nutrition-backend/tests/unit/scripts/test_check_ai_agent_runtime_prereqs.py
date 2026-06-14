"""Tests for AI Agent runtime prerequisite checks."""

from __future__ import annotations

from datetime import date
from textwrap import dedent
from types import SimpleNamespace

from lemon_ai_agent.knowledge import REVIEWED_MEDICAL_SOURCE_REGISTRY
from src.config import Settings

from scripts import check_ai_agent_runtime_prereqs as prereqs


def _kdca_topic_ids() -> dict[str, str]:
    by_id = {source.source_id: source for source in REVIEWED_MEDICAL_SOURCE_REGISTRY}
    return {
        topic_id: f"{index:04d}"
        for index, (topic_id, _label) in enumerate(
            by_id["kdca-healthinfo"].topic_id_requirements,
            start=1,
        )
    }


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

    assert "medical source kdca-healthinfo: missing (missing_topic_ids; missing_topics=54)" in lines
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
        "kdca-healthinfo=missing_topic_ids",
        "mfds-drug-safety=missing_api_key",
    ]


def test_required_medical_source_failures_pass_with_configured_keys() -> None:
    """Verify strict medical-source gates pass once required source keys exist."""
    failures = prereqs._required_medical_source_failures(
        Settings(
            _env_file=None,
            kdca_healthinfo_topic_ids=_kdca_topic_ids(),
            mfds_data_api_key="mfds-key",
        ),
        ("kdca-healthinfo", "mfds-drug-safety"),
        today=date(2026, 5, 24),
    )

    assert failures == []


def test_build_settings_loads_explicit_env_file(tmp_path) -> None:
    """Verify preflight can read user-provided API keys from a dotenv file."""
    topic_ids_file = tmp_path / "kdca_healthinfo_topics.local.json"
    topic_ids_file.write_text(
        '{"topics": {'
        + ", ".join(
            f'"{topic_id}": {{"topic_id": "{value}"}}'
            for topic_id, value in _kdca_topic_ids().items()
        )
        + "}}",
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        dedent(
            f"""
            KDCA_HEALTHINFO_TOPIC_IDS_FILE={topic_ids_file}
            MFDS_DATA_API_KEY=mfds-key
            """
        ).strip(),
        encoding="utf-8",
    )
    args = prereqs._parse_args(["--env-file", str(env_file)])

    settings = prereqs._build_settings(args)
    failures = prereqs._required_medical_source_failures(
        settings,
        ("kdca-healthinfo", "mfds-drug-safety"),
        today=date(2026, 5, 24),
    )

    assert failures == []


def test_build_settings_can_ignore_dotenv_files() -> None:
    """Verify tests and CI can force environment-only preflight settings."""
    args = prereqs._parse_args(["--ignore-env-file"])

    settings = prereqs._build_settings(args)

    assert isinstance(settings, Settings)


def test_exit_code_ignores_advisory_runtime_when_required_sources_pass() -> None:
    """Verify medical-source-only checks are not failed by smoke runtime env gaps."""
    args = prereqs._parse_args(["--require-medical-sources", "kdca-healthinfo"])

    exit_code = prereqs._exit_code(
        args,
        postgres_ready=False,
        sglang_ready=False,
        medical_source_failures=[],
        ollama_failure=None,
    )

    assert exit_code == 0


def test_exit_code_can_require_runtime_smoke_gates() -> None:
    """Verify live-smoke mode can still fail on PostgreSQL and SGLang readiness."""
    args = prereqs._parse_args(["--require-postgres-smoke", "--require-sglang-smoke"])

    exit_code = prereqs._exit_code(
        args,
        postgres_ready=False,
        sglang_ready=False,
        medical_source_failures=[],
        ollama_failure=None,
    )

    assert exit_code == 1


def test_exit_code_fails_required_medical_sources_and_ollama() -> None:
    """Verify strict source and Ollama gates still control the exit code."""
    args = prereqs._parse_args(["--require-medical-sources", "kdca-healthinfo", "--require-ollama"])

    exit_code = prereqs._exit_code(
        args,
        postgres_ready=True,
        sglang_ready=True,
        medical_source_failures=["kdca-healthinfo=missing_topic_ids"],
        ollama_failure="port_closed",
    )

    assert exit_code == 1


def test_exit_code_fails_required_ollama_parser_smoke() -> None:
    """Verify parser-smoke mode controls the exit code when explicitly required."""
    args = prereqs._parse_args(["--require-ollama-parser-smoke"])

    exit_code = prereqs._exit_code(
        args,
        postgres_ready=True,
        sglang_ready=True,
        medical_source_failures=[],
        ollama_failure=None,
        ollama_parser_smoke_failure="parser_smoke_failed",
    )

    assert exit_code == 1


def test_ollama_parser_smoke_failure_passes_expected_result(monkeypatch) -> None:
    """Verify the parser smoke helper accepts the expected structured result."""

    async def fake_smoke(_settings: Settings) -> SimpleNamespace:
        return SimpleNamespace(
            ingredient_candidates=[
                SimpleNamespace(amount=25.0, unit="mcg"),
            ]
        )

    monkeypatch.setattr(prereqs, "_run_ollama_parser_smoke", fake_smoke)

    failure = prereqs._ollama_parser_smoke_failure(Settings(_env_file=None))

    assert failure is None


def test_ollama_parser_smoke_failure_reports_unexpected_result(monkeypatch) -> None:
    """Verify the parser smoke helper fails closed on unexpected output."""

    async def fake_smoke(_settings: Settings) -> SimpleNamespace:
        return SimpleNamespace(
            ingredient_candidates=[
                SimpleNamespace(amount=10.0, unit="mg"),
            ]
        )

    monkeypatch.setattr(prereqs, "_run_ollama_parser_smoke", fake_smoke)

    failure = prereqs._ollama_parser_smoke_failure(Settings(_env_file=None))

    assert failure == "unexpected_result"


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

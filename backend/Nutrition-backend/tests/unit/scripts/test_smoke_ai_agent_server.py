"""Tests for AI Agent live smoke script control flow."""

from __future__ import annotations

from scripts import smoke_ai_agent_server as smoke


def test_smoke_args_support_existing_server_without_sglang_check() -> None:
    """Verify local API-level smoke can run without a live SGLang server."""
    args = smoke._parse_args(
        [
            "--database-url",
            "postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev",
            "--use-existing-server",
            "--skip-db-upgrade",
            "--skip-sglang-check",
        ]
    )

    assert args.database_url.endswith("/lemon_agent_dev")
    assert args.use_existing_server is True
    assert args.skip_db_upgrade is True
    assert args.skip_sglang_check is True


def test_smoke_summary_marks_sglang_check_skipped() -> None:
    """Verify output summary records whether SGLang readiness was required."""
    args = smoke._parse_args(
        [
            "--server-url",
            "http://127.0.0.1:18080",
            "--sglang-base-url",
            "http://127.0.0.1:30000/v1",
            "--sglang-model",
            "Qwen/Qwen2.5-0.5B-Instruct",
            "--database-url",
            "postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev",
        ]
    )
    summary = smoke._summary_payload(
        args=args,
        sglang_check="skipped",
        first={"provider": "deterministic"},
        second={"provider": "deterministic", "used_tools": ["agent_memory"]},
        chat={"provider": "sglang", "used_tools": ["chat_agent", "agent_memory"]},
    )

    assert summary["status"] == "ok"
    assert summary["sglang_check"] == "skipped"
    assert summary["first_provider"] == "deterministic"
    assert summary["second_used_tools"] == ["agent_memory"]
    assert summary["chat_provider"] == "sglang"
    assert summary["chat_used_tools"] == ["chat_agent", "agent_memory"]


def test_chat_payload_uses_health_management_question() -> None:
    """Verify smoke exercises the chatbot route without triggering deterministic boundaries."""
    payload = smoke._chat_payload("server-chat-smoke")

    assert payload["request_id"] == "server-chat-smoke"
    assert payload["message"] == "오늘 점심 나트륨이 높았는데 저녁은 어떻게 조절하면 좋을까?"
    assert payload["context"]["profile"]["chronic_conditions"] == ["hypertension"]

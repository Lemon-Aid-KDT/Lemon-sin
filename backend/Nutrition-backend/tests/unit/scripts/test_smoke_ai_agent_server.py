"""Tests for AI Agent live smoke script control flow."""

from __future__ import annotations

import pytest

from scripts import smoke_ai_agent_server as smoke


def test_smoke_args_support_existing_server_without_sglang_check() -> None:
    """Verify local API-level smoke can run without a live SGLang server."""
    args = smoke._parse_args(
        [
            "--database-url",
            "postgresql://postgres@127.0.0.1:55432/lemon_agent_dev?sslmode=require",
            "--use-existing-server",
            "--skip-db-upgrade",
            "--skip-sglang-check",
            "--skip-unknown-backlog-check",
        ]
    )

    assert args.database_url.endswith("/lemon_agent_dev?sslmode=require")
    assert args.use_existing_server is True
    assert args.skip_db_upgrade is True
    assert args.skip_sglang_check is True
    assert args.skip_unknown_backlog_check is True
    assert (
        smoke._normalize_database_url(args.database_url)
        == "postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev?ssl=require"
    )


def test_smoke_missing_database_url_message_points_to_supabase_dev_project() -> None:
    """Missing DB credentials should fail with an actionable local-only setup hint."""
    message = smoke._missing_database_url_message()

    assert "TEST_DATABASE_URL" in message
    assert "DATABASE_URL" in message
    assert "postgresql+asyncpg://postgres.ajgvoxttzsjcwtphtsuz:<password>@" in message
    assert "aws-1-ap-northeast-2.pooler.supabase.com" in message
    assert "Do not commit" in message
    assert "raw question" not in message.casefold()


def test_reviewed_chatbot_response_requires_answerable_with_reviewed_source() -> None:
    """Live smoke should prove the reviewed evidence path, not just any chat response."""
    smoke._assert_reviewed_chatbot_response(
        {
            "answerability": "answerable",
            "sources": [
                {
                    "source_id": "kdris-2025",
                    "source_family": "nutrition_reference",
                    "review_status": "reviewed",
                }
            ],
        }
    )


def test_reviewed_chatbot_response_rejects_unknown_or_missing_sources() -> None:
    """A fail-open or unknown chatbot response is not enough for live DB smoke."""
    with pytest.raises(RuntimeError, match="reviewed sodium/hypertension"):
        smoke._assert_reviewed_chatbot_response(
            {
                "answerability": "unknown_no_reviewed_source",
                "sources": [],
            }
        )

    with pytest.raises(RuntimeError, match="expected reviewed nutrition sources"):
        smoke._assert_reviewed_chatbot_response(
            {
                "answerability": "answerable",
                "sources": [{"source_id": "unknown-source", "review_status": "reviewed"}],
            }
        )

    with pytest.raises(RuntimeError, match="unreviewed source"):
        smoke._assert_reviewed_chatbot_response(
            {
                "answerability": "answerable",
                "sources": [{"source_id": "kdris-2025", "review_status": "draft"}],
            }
        )


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
        chat={
            "provider": "sglang",
            "used_tools": ["chat_agent", "agent_memory"],
            "answerability": "answerable",
            "sources": [
                {
                    "source_id": "kdris-2025",
                    "source_family": "nutrition_reference",
                    "version_label": "2025",
                    "expires_at": "2027-05-19",
                    "source_url": "https://example.test/kdris",
                }
            ],
        },
        unknown_chat={"answerability": "unknown_no_reviewed_source", "sources": []},
        unknown_backlog_before=3,
        unknown_backlog_after=4,
    )

    assert summary["status"] == "ok"
    assert summary["sglang_check"] == "skipped"
    assert summary["first_provider"] == "deterministic"
    assert summary["second_used_tools"] == ["agent_memory"]
    assert summary["chat_provider"] == "sglang"
    assert summary["chat_used_tools"] == ["chat_agent", "agent_memory"]
    assert summary["chat_answerability"] == "answerable"
    assert summary["chat_source_count"] == 1
    assert summary["unknown_answerability"] == "unknown_no_reviewed_source"
    assert summary["unknown_source_count"] == 0
    assert summary["unknown_backlog_delta"] == 1
    assert summary["chat_sources"] == [
        {
            "source_id": "kdris-2025",
            "source_family": "nutrition_reference",
            "version_label": "2025",
            "expires_at": "2027-05-19",
        }
    ]


def test_chat_payload_uses_health_management_question() -> None:
    """Verify smoke exercises the chatbot route without triggering deterministic boundaries."""
    payload = smoke._chat_payload("server-chat-smoke")

    assert payload["request_id"] == "server-chat-smoke"
    assert payload["context"]["profile"]["chronic_conditions"] == ["hypertension"]
    assert "latest_confirmed_entries" in payload["context"]


def test_unknown_chat_payload_uses_known_gap_question_without_sources() -> None:
    """Verify live smoke can prove unknown backlog persistence with a known gap."""
    payload = smoke._unknown_chat_payload("server-chat-unknown-smoke")

    assert payload == {
        "request_id": "server-chat-unknown-smoke",
        "user_id": "client-supplied-user",
        "message": "리튬 약과 타우린 영양제 같이 먹어도 돼?",
        "conversation": [],
        "context": {"profile": {"chronic_conditions": []}},
    }

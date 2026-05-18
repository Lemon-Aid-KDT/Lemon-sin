"""AI Agent chat package import tests."""

from __future__ import annotations

from lemon_ai_agent.adapters import AgentInput, DailyHealthAgentAppAdapter


def test_ai_agent_chat_package_exports_app_adapter() -> None:
    """Verify the backend package path exposes the app adapter contract."""
    request = AgentInput(
        request_id="import-smoke",
        user_id="local-dev-user",
        payload={"date": "2026-05-18"},
    )

    output = DailyHealthAgentAppAdapter().run(request)

    assert output.request_id == "import-smoke"
    assert output.user_id == "local-dev-user"
    assert output.status == "completed"

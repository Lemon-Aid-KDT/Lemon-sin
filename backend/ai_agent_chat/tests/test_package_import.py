"""AI Agent chat package import tests."""

from __future__ import annotations

from lemon_ai_agent import AnswerPlan, ContextResolver, UserHealthContextSnapshot
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


def test_ai_agent_chat_package_exports_user_health_context_contracts() -> None:
    """Verify app-context contracts are available from the package surface."""
    snapshot = UserHealthContextSnapshot.from_mapping(
        {"user_profile_summary": {"health_axes": ["sodium"]}}
    )

    result = ContextResolver().resolve("나트륨 줄이려면 오늘 뭐부터 보면 돼?", snapshot)

    assert result.status == "sufficient"


def test_ai_agent_chat_package_exports_answer_plan_contract() -> None:
    """Verify the planning contract is available from the package surface."""
    plan = AnswerPlan(intent="meal")

    assert plan.intent == "meal"

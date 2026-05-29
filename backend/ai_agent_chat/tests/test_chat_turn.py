"""Chat Turn Module behavior tests."""

from __future__ import annotations

from lemon_ai_agent.chat_session import ChatbotRequest
from lemon_ai_agent.chat_turn import ChatTurnModule


def test_chat_turn_plans_boundary_questions_without_llm_knowledge_leakage() -> None:
    turn = ChatTurnModule().plan(
        ChatbotRequest(
            request_id="chat-turn-drug",
            user_id="local-dev-user",
            message="와파린 복용 중 비타민 K를 같이 먹어도 돼?",
        )
    )

    assert turn.policy.category == "drug_or_interaction"
    assert turn.requires_boundary_response is True
    assert turn.source_families == [
        "supplement_reference",
        "drug_safety_boundary",
        "chronic_condition",
    ]


def test_chat_turn_selects_reviewed_knowledge_for_diabetes_lifestyle() -> None:
    turn = ChatTurnModule().plan(
        ChatbotRequest(
            request_id="chat-turn-diabetes",
            user_id="local-dev-user",
            message="당뇨를 개선하려면 식단, 운동, 수면, 체중관리를 어떻게 해야 해?",
            context={"profile": {"chronic_conditions": ["diabetes"]}},
        )
    )

    sources = {item.source for item in turn.knowledge_items}
    assert turn.policy.category == "chronic_condition_context"
    assert turn.analysis.related_conditions == ("diabetes",)
    assert "CDC Diabetes Meal Planning" in sources
    assert "NIDDK Healthy Living with Diabetes" in sources
    assert "Semantic Scholar Graph API" not in sources


def test_chat_turn_marks_unknown_when_no_reviewed_answer_card_exists() -> None:
    """Unsupported health questions fail closed instead of using broad model knowledge."""
    turn = ChatTurnModule().plan(
        ChatbotRequest(
            request_id="chat-turn-unknown",
            user_id="local-dev-user",
            message="리튬 약을 먹는데 셀레늄 영양제 같이 먹어도 돼?",
        )
    )

    assert turn.answerability == "unknown_no_reviewed_source"
    assert turn.answer_cards == ()
    assert turn.retrieval_status == "no_match"
    assert turn.requires_boundary_response is False

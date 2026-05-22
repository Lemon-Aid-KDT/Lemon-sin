"""Chatbot agent product-safety behavior tests."""

from __future__ import annotations

from lemon_ai_agent.agents.chatbot import ChatbotAgent
from lemon_ai_agent.chat_session import ChatTurn, ChatbotRequest
from lemon_ai_agent.llm import LLMRequest, LLMResponse


class _CapturingLLMClient:
    provider = "fake"

    def __init__(
        self,
        text: str = (
            "오늘의 요약: 현재 입력 기준으로 답변드릴 수 있습니다. "
            "권장 행동: 확인된 기록을 먼저 살펴보세요. "
            "참고 및 주의: 전문가와 상담해 주세요."
        ),
    ) -> None:
        self.request: LLMRequest | None = None
        self.text = text

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.request = request
        return LLMResponse(text=self.text, provider=self.provider, model="fake-ko")


def _request() -> ChatbotRequest:
    return ChatbotRequest(
        request_id="chatbot-test-1",
        user_id="local-dev-user",
        message="오늘 영양제랑 식사 기록을 보고 뭐부터 하면 좋을까?",
        conversation=[
            ChatTurn(
                role="user",
                content="어제 비타민 D를 먹었고 점심은 라면이었어.",
                created_at="2026-05-21T09:00:00+09:00",
            )
        ],
        context={
            "daily_coaching_summary": "나트륨은 높고 단백질은 낮을 수 있습니다.",
            "internal_trace": "supplement totals: vitamin d=25.0mcg",
        },
    )


def test_chatbot_without_llm_returns_safe_korean_fallback() -> None:
    """Verify chatbot fallback is product Korean and hides raw internals."""
    response = ChatbotAgent().answer(_request())

    assert response.request_id == "chatbot-test-1"
    assert response.provider == "deterministic"
    assert "오늘의 요약" in response.message
    assert "권장 행동" in response.message
    assert "참고 및 주의" in response.message
    assert "전문가와 상담" in response.message
    assert "supplement totals" not in response.message
    assert "internal_trace" not in response.message


def test_chatbot_llm_prompt_requires_korean_and_hides_internal_context() -> None:
    """Verify LLM prompt keeps internal context as grounding-only data."""
    client = _CapturingLLMClient()
    response = ChatbotAgent(llm_client=client).answer(_request())

    assert response.provider == "fake"
    assert response.message.startswith("오늘의 요약")
    assert client.request is not None
    system_prompt = client.request.messages[0].content
    user_prompt = client.request.messages[1].content
    assert "Answer only in Korean" in system_prompt
    assert "오늘의 요약" in system_prompt
    assert "권장 행동" in system_prompt
    assert "참고 및 주의" in system_prompt
    assert "Do not mention or quote internal calculation logs" in system_prompt
    assert "supplement totals" in system_prompt
    assert "Internal context for grounding only" in user_prompt
    assert "internal_trace" not in user_prompt
    assert "supplement totals" not in user_prompt


def test_chatbot_unsafe_llm_output_falls_back_to_safe_message() -> None:
    """Verify unsafe LLM text cannot pass through the chatbot."""
    client = _CapturingLLMClient(text="당뇨입니다. 이 제품을 구매하세요.")
    agent = ChatbotAgent(llm_client=client)

    response = agent.answer(_request())

    assert response.provider == "deterministic"
    assert "오늘의 요약" in response.message
    assert "당뇨입니다" not in response.message
    assert "구매하세요" not in response.message
    assert "Forbidden medical expression detected" in response.safety_warnings

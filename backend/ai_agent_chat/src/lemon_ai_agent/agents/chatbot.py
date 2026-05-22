from __future__ import annotations

from lemon_ai_agent.chat_session import ChatbotRequest, ChatbotResponse
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.llm import LLMMessage, LLMRequest, LocalLLMClient


class ChatbotAgent:
    """Answers user chat with the same safety boundary as Daily Coaching."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self._llm_client = llm_client
        self._safety_guard = SafetyGuard()

    def answer(self, request: ChatbotRequest) -> ChatbotResponse:
        warnings: list[str] = []
        fallback = self._fallback_response(request, warnings)

        if self._llm_client is None:
            return fallback

        try:
            llm_response = self._llm_client.generate(self._build_llm_request(request))
        except Exception as exc:
            warnings.append(f"chatbot llm fallback: {exc}")
            return self._fallback_response(request, warnings)

        check = self._safety_guard.check_text(llm_response.text)
        warnings.extend(check.warnings)
        if not check.allowed:
            return self._fallback_response(request, warnings)

        return ChatbotResponse(
            request_id=request.request_id,
            message=llm_response.text,
            provider=llm_response.provider,
            used_tools=["chatbot_agent", "safety_guard"],
            safety_warnings=warnings,
            requires_user_approval=False,
        )

    def _fallback_response(
        self,
        request: ChatbotRequest,
        warnings: list[str],
    ) -> ChatbotResponse:
        summary = self._safe_summary(request.context)
        if summary:
            summary_sentence = f"현재 입력 기준으로 {summary}"
        else:
            summary_sentence = "현재 확인된 기록을 기준으로 답변드릴 수 있습니다."

        return ChatbotResponse(
            request_id=request.request_id,
            message=(
                "오늘의 요약: "
                f"{summary_sentence} "
                "권장 행동: "
                "확정된 식사, 영양제, 건강 기록을 먼저 확인해 주세요. "
                "참고 및 주의: "
                "이 답변은 건강 관리를 위한 참고 자료이며, 의학적 판단이 필요한 경우 "
                "전문가와 상담해 주세요."
            ),
            provider="deterministic",
            used_tools=["chatbot_agent", "safety_guard"],
            safety_warnings=warnings,
            requires_user_approval=False,
        )

    def _build_llm_request(self, request: ChatbotRequest) -> LLMRequest:
        history = "\n".join(
            f"{turn.role}: {turn.content}" for turn in request.conversation[-6:]
        )
        summary = self._safe_summary(request.context) or "none"

        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are the Lemon Aid chatbot for health-management coaching. "
                        "Answer only in Korean. Use the structure '오늘의 요약', "
                        "'권장 행동', and '참고 및 주의'. Do not diagnose, treat, "
                        "prescribe, guarantee effects, or promote buying a specific product. "
                        "Use cautious phrasing such as '현재 입력 기준', "
                        "'주의가 필요할 수 있습니다', and '전문가와 상담해 주세요'. "
                        "Do not mention or quote internal calculation logs, trace, "
                        "tool names, 'supplement totals', or 'nutrition findings'. "
                        "Do not create new health judgments beyond the supplied context."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"User message: {request.message.strip()}\n"
                        f"Recent conversation:\n{history or 'none'}\n"
                        "Internal context for grounding only; do not quote or mention "
                        f"internal keys: {summary}"
                    ),
                ),
            ]
        )

    def _safe_summary(self, context: dict[str, object]) -> str:
        raw_summary = context.get("daily_coaching_summary")
        if not isinstance(raw_summary, str):
            return ""

        check = self._safety_guard.check_text(raw_summary)
        if not check.allowed:
            return ""
        return raw_summary.strip()

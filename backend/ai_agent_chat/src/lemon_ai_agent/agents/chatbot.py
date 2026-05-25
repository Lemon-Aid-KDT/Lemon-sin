from __future__ import annotations

from lemon_ai_agent.chat_session import ChatbotRequest, ChatbotResponse
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    contract_summary,
    policy_for_question,
    source_family_summary,
)
from lemon_ai_agent.llm import LLMMessage, LLMRequest, LocalLLMClient


class ChatbotAgent:
    """Answers user chat with the same safety boundary as Daily Coaching."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self._llm_client = llm_client
        self._safety_guard = SafetyGuard()

    def answer(self, request: ChatbotRequest) -> ChatbotResponse:
        warnings: list[str] = []
        policy = policy_for_question(request.message)
        boundary_response = self._boundary_response(request, policy, warnings)
        if boundary_response is not None:
            return boundary_response

        fallback = self._fallback_response(request, warnings, policy)

        if self._llm_client is None:
            return fallback

        try:
            llm_response = self._llm_client.generate(
                self._build_llm_request(request, policy)
            )
        except Exception as exc:
            warnings.append(f"chatbot llm fallback: {exc}")
            return self._fallback_response(request, warnings, policy)

        check = self._safety_guard.check_text(llm_response.text)
        warnings.extend(check.warnings)
        if not check.allowed:
            return self._fallback_response(request, warnings, policy)
        grounding_check = self._safety_guard.check_grounding(
            llm_response.text,
            self._grounding_context(request),
        )
        warnings.extend(grounding_check.warnings)
        if not grounding_check.allowed:
            return self._fallback_response(request, warnings, policy)

        return ChatbotResponse(
            request_id=request.request_id,
            message=llm_response.text,
            provider=llm_response.provider,
            used_tools=["chatbot_agent", "knowledge_policy", "safety_guard"],
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            requires_user_approval=False,
        )

    def _fallback_response(
        self,
        request: ChatbotRequest,
        warnings: list[str],
        policy: AnswerPolicy,
    ) -> ChatbotResponse:
        summary = self._safe_summary(request.context)
        if summary:
            summary_sentence = f"현재 입력 기준으로 {summary}"
        else:
            summary_sentence = "현재 확인된 기록을 기준으로 답변드릴 수 있습니다."

        if policy.category == "chronic_condition_context":
            next_action = (
                "확정된 식사 기록과 질환 맥락을 함께 보고, 혈당이나 혈압 반응처럼 "
                "직접 확인 가능한 기록을 우선 점검해 주세요."
            )
        elif policy.category == "supplement_question":
            next_action = (
                "제품 라벨, 섭취량, 복용 중인 약 목록을 같이 확인하고 필요하면 "
                "전문가와 상담해 주세요."
            )
        else:
            next_action = "확정된 식사, 영양제, 건강 기록을 먼저 확인해 주세요."

        return ChatbotResponse(
            request_id=request.request_id,
            message=(
                "오늘의 요약: "
                f"{summary_sentence} "
                "권장 행동: "
                f"{next_action} "
                "참고 및 주의: "
                "이 답변은 건강 관리를 위한 참고 자료이며, 의학적 판단이 필요한 경우 "
                "전문가와 상담해 주세요."
            ),
            provider="deterministic",
            used_tools=["chatbot_agent", "knowledge_policy", "safety_guard"],
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            requires_user_approval=False,
        )

    def _build_llm_request(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
    ) -> LLMRequest:
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
                        "Answer only in Korean and follow the response contract sections. "
                        "Do not diagnose, treat, prescribe, guarantee effects, "
                        "or promote buying a specific product. "
                        "Use cautious phrasing such as '현재 입력 기준', "
                        "'주의가 필요할 수 있습니다', and '전문가와 상담해 주세요'. "
                        "Do not mention or quote internal calculation logs, trace, "
                        "tool names, 'supplement totals', or 'nutrition findings'. "
                        "Do not create new health facts without a listed source family. "
                        "Do not create new health judgments beyond the supplied context."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"User message: {request.message.strip()}\n"
                        f"Question category: {policy.category}\n"
                        f"Classification reasons: {', '.join(policy.reasons)}\n"
                        "Allowed source families:\n"
                        f"{source_family_summary(policy.source_families)}\n"
                        "Response contract:\n"
                        f"{contract_summary(policy.contract)}\n"
                        f"Recent conversation:\n{history or 'none'}\n"
                        "Internal context for grounding only; do not quote or mention "
                        f"internal keys: {summary}"
                    ),
                ),
            ],
            temperature=0.1,
        )

    def _boundary_response(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
        warnings: list[str],
    ) -> ChatbotResponse | None:
        if policy.category == "symptom_or_emergency":
            warnings.append("Emergency escalation boundary applied")
            return self._deterministic_response(
                request,
                policy,
                (
                    "즉시 안내: 가슴 통증, 숨참, 마비, 실신처럼 응급 가능성이 있는 "
                    "증상은 식단 코칭보다 긴급 확인이 우선입니다. 지금 증상이 "
                    "지속되거나 심하면 119에 연락하거나 가까운 응급실로 이동하세요. "
                    "주의: Lemon Aid는 이런 상황에서 개인 의료 판단을 대신하지 "
                    "않습니다. 연결 자원: E-Gen 응급의료포털과 보건복지상담센터 "
                    "129를 참고할 수 있습니다."
                ),
                warnings,
            )

        if policy.category == "mental_health_risk":
            warnings.append("Mental health escalation boundary applied")
            return self._deterministic_response(
                request,
                policy,
                (
                    "즉시 안내: 자해, 자살 생각, 극단적인 굶기처럼 안전 위험이 보이면 "
                    "일반 건강관리 안내를 멈추고 사람의 도움을 먼저 받아야 합니다. "
                    "혼자 있지 말고 신뢰할 수 있는 사람이나 가까운 의료기관에 즉시 "
                    "알리세요. 주의: 체중 관리 조언보다 현재 안전 확인이 우선입니다. "
                    "연결 자원: 자살예방상담전화 109, 보건복지상담센터 129, "
                    "국가정신건강정보포털을 이용할 수 있습니다."
                ),
                warnings,
            )

        if policy.category == "drug_or_interaction":
            warnings.append("Drug interaction boundary applied")
            return self._deterministic_response(
                request,
                policy,
                (
                    "요약: 약, 질환, 영양제 병용 질문은 Lemon Aid가 허용 또는 "
                    "금지로 판정하지 않습니다. 주의: 현재 복용 중인 약, 질환, "
                    "검사 수치, 제품 성분표에 따라 확인할 내용이 달라질 수 있습니다. "
                    "다음 행동: 제품 라벨과 복용 중인 약 목록을 가지고 의사 또는 "
                    "약사에게 확인하세요. 임의로 시작, 중단, 증량, 감량하지 않는 "
                    "것이 안전합니다."
                ),
                warnings,
            )

        if policy.category == "out_of_scope":
            warnings.append("Out-of-scope medical decision boundary applied")
            return self._deterministic_response(
                request,
                policy,
                (
                    "요약: 개인 복용량, 처방 변경, 질환 판단처럼 개인 의료 결정에 "
                    "해당하는 질문은 Lemon Aid가 결정하지 않습니다. 주의: 영양소도 "
                    "검사 결과, 현재 섭취량, 복용 중인 약, 질환 맥락에 따라 확인이 "
                    "필요합니다. 다음 행동: 현재 식사와 영양제 섭취량을 정리하고, "
                    "필요하면 검사 결과를 바탕으로 전문가와 상담하세요."
                ),
                warnings,
            )

        return None

    def _deterministic_response(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
        message: str,
        warnings: list[str],
    ) -> ChatbotResponse:
        return ChatbotResponse(
            request_id=request.request_id,
            message=message,
            provider="deterministic",
            used_tools=["chatbot_agent", "knowledge_policy", "safety_guard"],
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            requires_user_approval=False,
        )

    def _safe_summary(self, context: dict[str, object]) -> str:
        raw_summary = context.get("daily_coaching_summary")
        if not isinstance(raw_summary, str):
            return ""

        check = self._safety_guard.check_text(raw_summary)
        if not check.allowed:
            return ""
        return raw_summary.strip()

    def _grounding_context(self, request: ChatbotRequest) -> str:
        conversation = "\n".join(turn.content for turn in request.conversation[-6:])
        summary = self._safe_summary(request.context)
        return "\n".join((request.message, conversation, summary))

from __future__ import annotations

from lemon_ai_agent.answer_card import AnswerCard
from lemon_ai_agent.chat_session import ChatbotRequest, ChatbotResponse
from lemon_ai_agent.chat_turn import ChatTurnModule, ChatTurnPlan
from lemon_ai_agent.guards.safety import SafetyEnvelope, SafetyGuard
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    ChatIntentAnalysis,
    MedicalKnowledgeItem,
    contract_summary,
    source_family_summary,
)
from lemon_ai_agent.llm import LLMCompletion, LLMMessage, LLMRequest, LocalLLMClient

MEAL_LABELS = {
    "breakfast": "아침",
    "lunch": "점심",
    "dinner": "저녁",
    "snack": "간식",
}

NUTRIENT_LABELS = {
    "sodium": "나트륨",
    "protein": "단백질",
    "vitamin d": "비타민 D",
    "vitamin_d": "비타민 D",
    "magnesium": "마그네슘",
    "iron": "철",
    "calcium": "칼슘",
    "fiber": "식이섬유",
    "carbohydrate": "탄수화물",
    "carbohydrates": "탄수화물",
    "fat": "지방",
    "sugar": "당류",
    "sugars": "당류",
}

REQUIRED_CHATBOT_SECTIONS = ("요약", "주의 조건", "오늘 할 일", "관리 포인트", "출처 기준")
CHATBOT_TOOLS = [
    "chatbot_agent",
    "intent_analysis",
    "medical_knowledge_retrieval",
    "knowledge_policy",
    "safety_guard",
]

DIABETES_CONTEXT_TERMS = ("당뇨", "혈당", "diabetes", "glucose")
HYPERTENSION_CONTEXT_TERMS = ("고혈압", "혈압", "hypertension", "blood pressure")
KIDNEY_CONTEXT_TERMS = ("콩팥", "신장", "kidney", "renal")


class ChatbotAgent:
    """Answers user chat with the same safety boundary as Daily Coaching."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self._completion = LLMCompletion(llm_client)
        self._has_llm_client = llm_client is not None
        self._safety_guard = SafetyGuard()
        self._safety_envelope = SafetyEnvelope(self._safety_guard)
        self._chat_turn = ChatTurnModule()

    def answer(self, request: ChatbotRequest) -> ChatbotResponse:  # noqa: PLR0911
        warnings: list[str] = []
        turn = self._chat_turn.plan(request)
        boundary_response = self._boundary_response(turn, warnings)
        if boundary_response is not None:
            return boundary_response
        if turn.answerability == "unknown_no_reviewed_source":
            warnings.extend(turn.retrieval_warnings)
            return self._unknown_response(turn, warnings)

        if not self._has_llm_client:
            return self._fallback_response(turn, warnings)

        completion = self._completion.complete(
            self._build_llm_request(turn)
        )
        if not completion.ok:
            warnings.extend(completion.warnings)
            return self._fallback_response(turn, warnings)

        safety = self._safety_envelope.screen_llm_output(
            completion.text,
            self._grounding_context(turn),
        )
        warnings.extend(safety.warnings)
        card_phrase_check = self._safety_guard.check_forbidden_phrases(
            completion.text,
            self._card_must_not_say(turn.answer_cards),
        )
        warnings.extend(card_phrase_check.warnings)
        has_required_shape = self._has_required_response_shape(completion.text)
        if not has_required_shape:
            warnings.append("Chatbot response contract not followed")
        if not safety.allowed or not card_phrase_check.allowed or not has_required_shape:
            return self._fallback_response(turn, warnings)
        if not self._has_required_card_specificity(completion.text, turn):
            warnings.append("Chatbot response card detail not followed")
            return self._fallback_response(turn, warnings)

        return ChatbotResponse(
            request_id=request.request_id,
            message=safety.text,
            provider=completion.provider,
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=turn.source_families,
            answerability=turn.answerability,
            sources=turn.sources,
            requires_user_approval=False,
        )

    def _fallback_response(
        self,
        turn: ChatTurnPlan,
        warnings: list[str],
    ) -> ChatbotResponse:
        if turn.policy.category == "medication_supplement_caution":
            return self._medication_supplement_caution_response(turn, warnings)
        if self._is_sodium_meal_question(turn):
            return self._sodium_meal_response(turn, warnings)

        request = turn.request
        summary = self._safe_summary(request.context)
        confirmed_foods = self._confirmed_food_summary(request.context)
        if summary:
            summary_sentence = f"현재 입력 기준으로 {summary}"
        elif confirmed_foods:
            summary_sentence = f"확인된 기록은 {confirmed_foods}입니다."
        else:
            summary_sentence = "현재 확인된 기록을 기준으로 답변드릴 수 있습니다."

        if turn.analysis.primary_intent == "symptom" and not turn.analysis.boundary:
            next_action = self._symptom_next_action(turn.analysis)
        elif turn.policy.category == "chronic_condition_context":
            next_action = self._chronic_condition_next_action(request)
        elif turn.policy.category == "supplement_question":
            next_action = (
                "제품 라벨의 섭취량, 원재료, 기능성 표시를 확인하고 같은 성분의 "
                "중복 섭취를 피하세요."
            )
        else:
            next_action = "확정된 식사, 영양제, 건강 기록을 먼저 확인해 주세요."

        caution = self._fallback_caution(request, turn.policy, turn.analysis)
        management_points = self._fallback_management_points(
            turn.analysis,
            turn.knowledge_items,
        )

        return ChatbotResponse(
            request_id=request.request_id,
            message=(
                "요약\n"
                f"- {summary_sentence}\n"
                "주의 조건\n"
                f"- {caution}\n"
                "오늘 할 일\n"
                f"- {next_action}\n"
                "관리 포인트\n"
                f"- {management_points}\n"
                "출처 기준\n"
                f"- {self._source_basis(turn.knowledge_items)}"
            ),
            provider="deterministic",
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=turn.source_families,
            answerability=turn.answerability,
            sources=turn.sources,
            requires_user_approval=False,
        )

    def _build_llm_request(
        self,
        turn: ChatTurnPlan,
    ) -> LLMRequest:
        request = turn.request
        history = "\n".join(
            f"{turn.role}: {turn.content}" for turn in request.conversation[-6:]
        )
        summary = self._safe_summary(request.context) or "none"
        confirmed_foods = self._confirmed_food_summary(request.context) or "none"

        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are the Lemon Aid chatbot for health-management coaching. "
                        "Answer only in Korean. Use exactly these section labels: "
                        "요약, 주의 조건, 오늘 할 일, 관리 포인트, 출처 기준. "
                        "Use 3 to 6 short mobile-readable bullet lines total where possible. "
                        "Do not diagnose, treat, prescribe, guarantee effects, "
                        "or promote buying a specific product. "
                        "Use cautious but practical phrasing such as '현재 입력 기준', "
                        "'줄이는 것이 좋습니다', '다음 끼니에서 조절하세요', "
                        "and '권장합니다'. "
                        "Use professional-confirmation wording only for medication or "
                        "supplement co-use, starting/stopping/changing doses, diagnosis, "
                        "treatment, prescription, lab-value interpretation, emergency or "
                        "mental-health risk, worsening symptoms, or other personal medical "
                        "judgment requests. "
                        "Avoid absolute-ban wording such as '먹으면 안 된다', "
                        "'완전히 금지', or '절대 먹지 마세요'. "
                        "sodium 같은 영문 영양소명은 나트륨처럼 한국어 표시명으로 바꾸세요. "
                        "Do not mention or quote internal calculation logs, trace, "
                        "tool names, 'supplement totals', or 'nutrition findings'. "
                        "Do not create new health facts without a listed source family. "
                        "Do not create new health judgments beyond the supplied context. "
                        "Do not use Semantic Scholar as a user-facing source. "
                        "Use only the provided reviewed answer cards as factual grounding. "
                        "If no reviewed answer card is provided, do not answer with model knowledge. "
                        "Do not answer with only broad categories such as vegetables or protein; "
                        "use concrete examples from the provided knowledge cards. "
                        "For medication/supplement co-use questions, explain general principles "
                        "and checklist items, but do not conclude whether the user personally can "
                        "or cannot take them together. "
                        "Professional-confirmation wording must attach to the decision point; "
                        "it must not replace the useful checklist. "
                        "For emergency questions, do not provide long differential diagnosis; "
                        "prioritize risk reason and immediate action. "
                        "For source basis, write briefly like: "
                        "'출처 기준: 질병관리청 건강정보, KDRIs 영양 기준'."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"User message: {request.message.strip()}\n"
                        f"Question category: {turn.policy.category}\n"
                        f"Classification reasons: {', '.join(turn.policy.reasons)}\n"
                        "Allowed source families:\n"
                        f"{source_family_summary(turn.policy.source_families)}\n"
                        "Response contract:\n"
                        f"{contract_summary(turn.policy.contract)}\n"
                        "Intent analysis:\n"
                        f"{self._intent_analysis_summary(turn.analysis)}\n"
                        "Reviewed knowledge items:\n"
                        f"{self._answer_cards_summary(turn.answer_cards)}\n"
                        "Answer strategy:\n"
                        f"{self._answer_strategy(turn.analysis, turn.knowledge_items)}\n"
                        f"Recent conversation:\n{history or 'none'}\n"
                        "Confirmed meal and nutrient context:\n"
                        f"{confirmed_foods}\n"
                        "Internal context for grounding only; do not quote or mention "
                        f"internal keys: {summary}"
                    ),
                ),
            ],
            temperature=0.1,
        )

    def _boundary_response(
        self,
        turn: ChatTurnPlan,
        warnings: list[str],
    ) -> ChatbotResponse | None:
        request = turn.request
        policy = turn.policy
        if policy.category == "symptom_or_emergency":
            warnings.append("Emergency escalation boundary applied")
            return self._deterministic_response(
                request,
                policy,
                (
                    "즉시 안내: 가슴 통증, 숨참, 마비, 실신처럼 응급 가능성이 있는 "
                    "증상은 단순 피로나 소화불량으로 단정할 수 없고 심장이나 폐 쪽 "
                    "응급 신호일 수 있습니다. 지금 증상이 지속되거나 심하면 119에 "
                    "연락하거나 가까운 응급실로 이동하세요. "
                    "주의: Lemon Aid는 이런 상황에서 개인 의료 판단을 대신하지 "
                    "않습니다. 연결 자원: E-Gen 응급의료포털과 보건복지상담센터 "
                    "129를 참고할 수 있습니다."
                ),
                warnings,
                answerability=turn.answerability,
                sources=turn.sources,
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
                answerability=turn.answerability,
                sources=turn.sources,
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
                answerability=turn.answerability,
                sources=turn.sources,
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
                answerability=turn.answerability,
                sources=turn.sources,
            )

        return None

    def _unknown_response(
        self,
        turn: ChatTurnPlan,
        warnings: list[str],
    ) -> ChatbotResponse:
        request = turn.request
        return ChatbotResponse(
            request_id=request.request_id,
            message=(
                "요약\n"
                "- 현재 검수된 지식 안에서 답할 수 없습니다.\n"
                "현재 답할 수 없는 이유\n"
                "- 이 질문에 맞는 reviewed answer card가 아직 없어 LLM 일반 지식으로 "
                "병용 가능 여부나 건강 판단을 채우지 않습니다.\n"
                "필요한 검수 지식\n"
                "- 정확한 약 이름, 제품 라벨, 성분명, 복용 목적, 관련 질환과 함께 "
                "검수된 출처가 필요합니다.\n"
                "지금 할 수 있는 안전한 행동\n"
                "- 새로 시작하거나 함께 복용할지 결정하기 전에는 제품 라벨과 약 목록을 "
                "가지고 약사 또는 의사에게 확인하세요."
            ),
            provider="deterministic",
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=turn.source_families,
            answerability=turn.answerability,
            sources=[],
            requires_user_approval=False,
        )

    def _medication_supplement_caution_response(
        self,
        turn: ChatTurnPlan,
        warnings: list[str],
    ) -> ChatbotResponse:
        request = turn.request
        return self._deterministic_response(
            request,
            turn.policy,
            (
                "요약\n"
                "- 마그네슘은 근육·신경 기능과 관련된 영양소라 관심을 가질 수 있습니다.\n"
                "주의 조건\n"
                "- 혈압약을 복용 중이면 제품 라벨의 마그네슘 함량, 혈압약 종류, "
                "신장 기능, 다른 영양제 중복 여부를 함께 봐야 합니다.\n"
                "오늘 할 일\n"
                "- 제품 라벨과 복용 중인 혈압약 이름을 확인하고, 최근 어지러움, "
                "설사, 복통 같은 이상 증상이 있었는지 정리하세요.\n"
                "관리 포인트\n"
                "- 식품으로는 견과류, 콩류, 통곡물, 녹색 잎채소처럼 마그네슘을 "
                "포함한 후보를 우선 고려할 수 있습니다. 보충제를 새로 시작하거나 "
                "복용량을 정하는 지점은 약 이름과 제품 라벨을 가지고 약사 또는 "
                "의사에게 확인하세요.\n"
                "출처 기준\n"
                f"- {self._source_basis(turn.knowledge_items)}"
            ),
            warnings,
            answerability=turn.answerability,
            sources=turn.sources,
        )

    def _sodium_meal_response(
        self,
        turn: ChatTurnPlan,
        warnings: list[str],
    ) -> ChatbotResponse:
        request = turn.request
        confirmed_foods = self._confirmed_food_summary(request.context)
        safe_summary = self._safe_summary(request.context)
        if safe_summary:
            summary_sentence = f"현재 입력 기준으로 {safe_summary}"
        elif confirmed_foods:
            summary_sentence = f"확인된 기록은 {confirmed_foods}입니다."
        else:
            summary_sentence = "오늘 저녁 나트륨을 줄이려면 국물, 소스, 장류, 가공육을 먼저 줄이는 쪽이 실용적입니다."
        kidney_caution = ""
        if "kidney_disease" in turn.analysis.related_conditions:
            kidney_caution = (
                " 신장질환이나 콩팥 관련으로 칼륨 제한을 들은 적이 있다면 "
                "채소와 과일 선택은 따로 확인이 필요합니다."
            )

        return self._deterministic_response(
            request,
            turn.policy,
            (
                "요약\n"
                f"- {summary_sentence}\n"
                "주의 조건\n"
                "- 찌개나 라면은 국물을 남기고, 간장·쌈장·고추장·드레싱 같은 "
                f"소스와 장류는 부어 먹기보다 찍어 먹는 쪽이 좋습니다.{kidney_caution}\n"
                "오늘 할 일\n"
                "- 김치류, 장아찌, 젓갈은 한 가지 이하로 줄이고 햄·소시지·베이컨 "
                "같은 가공육 대신 두부, 달걀, 생선구이, 닭가슴살, 살코기, 콩류 중에서 고르세요. "
                "직접 확인 가능한 기록을 우선 점검하세요.\n"
                "관리 포인트\n"
                "- 채소는 오이, 양배추, 브로콜리, 버섯, 토마토, 시금치처럼 "
                "양념을 약하게 해도 먹기 쉬운 후보로 바꿔 보세요. 다음 끼니에서도 "
                "짠 국물과 소스 양을 다시 확인하세요.\n"
                "출처 기준\n"
                f"- {self._source_basis(turn.knowledge_items)}"
            ),
            warnings,
            answerability=turn.answerability,
            sources=turn.sources,
        )

    def _deterministic_response(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
        message: str,
        warnings: list[str],
        *,
        answerability: str = "answerable",
        sources: list[dict[str, str]] | None = None,
    ) -> ChatbotResponse:
        return ChatbotResponse(
            request_id=request.request_id,
            message=message,
            provider="deterministic",
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            answerability=answerability,
            sources=sources or [],
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

    def _grounding_context(
        self,
        turn: ChatTurnPlan,
    ) -> str:
        request = turn.request
        conversation = "\n".join(turn.content for turn in request.conversation[-6:])
        summary = self._safe_summary(request.context)
        confirmed_foods = self._confirmed_food_summary(request.context)
        knowledge = "\n".join(item.concrete_guidance for item in turn.knowledge_items)
        cards = "\n".join(self._answer_card_text(card) for card in turn.answer_cards)
        return "\n".join((request.message, conversation, summary, confirmed_foods, knowledge, cards))

    def _has_required_response_shape(self, text: str) -> bool:
        return all(section in text for section in REQUIRED_CHATBOT_SECTIONS)

    def _has_required_card_specificity(self, text: str, turn: ChatTurnPlan) -> bool:
        if turn.policy.category == "medication_supplement_caution":
            required_terms = ("마그네슘", "제품 라벨", "함량", "혈압약 종류", "신장 기능")
            return all(term in text for term in required_terms)
        return True

    def _card_must_not_say(self, answer_cards: tuple[AnswerCard, ...]) -> tuple[str, ...]:
        phrases: list[str] = []
        for card in answer_cards:
            phrases.extend(card.must_not_say)
        return tuple(dict.fromkeys(phrases))

    def _fallback_caution(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
        analysis: ChatIntentAnalysis,
    ) -> str:
        if analysis.primary_intent == "symptom" and not analysis.boundary:
            return "흉통, 숨참, 마비, 실신, 말이 어눌함 같은 증상이 있으면 일반 코칭을 중단하세요."
        if policy.category == "chronic_condition_context":
            return self._chronic_condition_caution(request)
        if policy.category == "supplement_question":
            return "건강기능식품은 제품 라벨의 섭취량과 성분 중복 여부를 먼저 확인하세요."
        if policy.category == "nutrition_analysis":
            return "KDRIs 영양 기준과 확인된 식사 기록을 기준으로 반복 패턴을 조절하세요."
        return "공식자료와 확인된 기록을 기준으로 일반적인 건강관리 범위에서 조절하세요."

    def _symptom_next_action(self, analysis: ChatIntentAnalysis) -> str:
        if "diabetes" in analysis.related_conditions:
            return (
                "운동을 멈추고 휴식하며 수분을 보충한 뒤 서늘한 곳에서 증상을 보세요. "
                "당뇨 맥락에서는 저혈당 가능성도 조심스럽게 확인하세요."
            )
        return "운동을 멈추고 휴식하며 수분을 보충한 뒤 서늘한 곳에서 증상 변화를 보세요."

    def _fallback_management_points(
        self,
        analysis: ChatIntentAnalysis,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        if analysis.primary_intent == "symptom" and not analysis.boundary:
            return "증상이 반복되거나 악화되면 운동 강도, 수분, 식사 간격을 기록하고 확인하세요."
        if "diabetes" in analysis.related_conditions and knowledge_items:
            return self._diabetes_management_points(knowledge_items)
        return "한 번의 식사보다 반복 패턴을 보고 다음 기록에서 조절하세요."

    def _diabetes_management_points(
        self,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        guidance = " ".join(item.concrete_guidance for item in knowledge_items)
        points: list[str] = []
        if "비전분 채소 1/2" in guidance:
            points.append("식사는 비전분 채소 1/2, 단백질 1/4, 탄수화물 1/4로 잡아 보세요")
        if "주 150분" in guidance:
            points.append("운동은 주 150분 중강도 유산소와 주 2일 근력운동을 목표로 하세요")
        if "7시간" in guidance:
            points.append("수면은 성인 기준 하루 7시간 이상을 기록하세요")
        return "; ".join(points) if points else "식사, 운동, 수면, 체중 기록을 함께 보세요."

    def _source_basis(self, knowledge_items: tuple[MedicalKnowledgeItem, ...]) -> str:
        if not knowledge_items:
            return "질병관리청 건강정보, KDRIs 영양 기준"

        source_names = []
        for item in knowledge_items:
            if item.source_id == "kdca-healthinfo":
                source_names.append("질병관리청 건강정보")
            elif item.source_id == "kdris-2025":
                source_names.append("KDRIs 영양 기준")
            elif item.source.startswith("CDC"):
                source_names.append("CDC")
            elif item.source.startswith("NIDDK"):
                source_names.append("NIDDK")
            else:
                source_names.append(item.source)

        unique_sources = list(dict.fromkeys(source_names))
        if "질병관리청 건강정보" in unique_sources and "KDRIs 영양 기준" in unique_sources:
            ordered = [
                "질병관리청 건강정보",
                "KDRIs 영양 기준",
                *(source for source in unique_sources if source not in {"질병관리청 건강정보", "KDRIs 영양 기준"}),
            ]
            return ", ".join(ordered)
        return ", ".join(unique_sources)

    def _intent_analysis_summary(self, analysis: ChatIntentAnalysis) -> str:
        related = ", ".join(analysis.related_conditions) or "none"
        red_flags = ", ".join(analysis.red_flags) or "none"
        boundary = ", ".join(analysis.boundary) or "none"
        return (
            f"primary_intent={analysis.primary_intent}; category={analysis.category}; "
            f"related_conditions={related}; red_flags={red_flags}; boundary={boundary}"
        )

    def _knowledge_items_summary(
        self,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        if not knowledge_items:
            return "none"
        return "\n".join(self._knowledge_card_text(item) for item in knowledge_items)

    def _answer_cards_summary(
        self,
        answer_cards: tuple[AnswerCard, ...],
    ) -> str:
        if not answer_cards:
            return "none"
        return "\n".join(self._answer_card_text(card) for card in answer_cards)

    def _answer_card_text(self, card: AnswerCard) -> str:
        return (
            f"- card_id={card.card_id} | answerability={card.answerability} | "
            f"source_id={card.source_id} | source_family={card.source_family} | "
            f"review_status={card.review_status} | version={card.version_label} | "
            f"topic={card.topic} | intent={card.intent} | condition={card.condition or 'general'} | "
            f"guidance={card.concrete_guidance} | allowed={'; '.join(card.allowed_guidance)} | "
            f"examples={', '.join(card.specific_examples)} | checklist={', '.join(card.checklist)} | "
            f"cautions={', '.join(card.caution_conditions)} | must_not_say={', '.join(card.must_not_say)} | "
            f"url={card.source_url}"
        )

    def _knowledge_card_text(self, item: MedicalKnowledgeItem) -> str:
        return (
            f"- {item.source} | source_id={item.source_id} | topic={item.topic} | "
            f"intent={item.intent} | condition={item.condition or 'general'} | "
            f"guidance={item.concrete_guidance} | allowed={'; '.join(item.allowed_guidance)} | "
            f"examples={', '.join(item.specific_examples)} | checklist={', '.join(item.checklist)} | "
            f"cautions={', '.join(item.caution_conditions)} | must_not_say={', '.join(item.must_not_say)} | "
            f"url={item.source_url}"
        )

    def _answer_strategy(
        self,
        analysis: ChatIntentAnalysis,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        if analysis.boundary:
            return "Apply the boundary response and do not provide normal coaching."
        if analysis.category == "medication_supplement_caution":
            return (
                "Explain the general nutrient role and checklist from the card, "
                "but do not decide personal co-use safety."
            )
        if analysis.primary_intent == "symptom":
            return "Start with red-flag screening, then rest, hydration, cool place, and observation."
        if knowledge_items:
            return "Use the reviewed guidance items as concrete coaching points without exposing raw retrieval."
        return "Use general health-management coaching only within the allowed source families."

    def _is_sodium_meal_question(self, turn: ChatTurnPlan) -> bool:
        text = self._condition_context(turn.request)
        return turn.analysis.primary_intent == "meal" and self._has_any_context_term(
            text,
            (
                "나트륨",
                "소금",
                "짠",
                "고혈압",
                "혈압",
                "라면",
                "찌개",
                "국물",
                "소스",
                "장류",
                "가공육",
            ),
        )

    def _chronic_condition_caution(self, request: ChatbotRequest) -> str:
        condition_context = self._condition_context(request)
        if self._has_any_context_term(condition_context, DIABETES_CONTEXT_TERMS):
            return (
                "당뇨 맥락에서는 밥, 면, 빵 같은 탄수화물 양과 초콜릿, 아이스크림 같은 "
                "당류 간식을 한 번에 많이 먹는 패턴을 줄이는 것이 좋습니다."
            )
        if self._has_any_context_term(condition_context, HYPERTENSION_CONTEXT_TERMS):
            return "고혈압 맥락에서는 짠 국물, 가공식품, 반복적인 고나트륨 식사를 줄이는 것이 좋습니다."
        if self._has_any_context_term(condition_context, KIDNEY_CONTEXT_TERMS):
            return "콩팥 질환 맥락에서는 짠 음식과 가공식품을 줄이고 기록된 식사 패턴을 확인하세요."
        return "질환 맥락에서는 한 번의 식사보다 반복되는 과식, 고나트륨, 고당류 패턴을 줄이는 것이 좋습니다."

    def _chronic_condition_next_action(self, request: ChatbotRequest) -> str:
        condition_context = self._condition_context(request)
        if self._has_any_context_term(condition_context, DIABETES_CONTEXT_TERMS):
            if self._has_any_context_term(
                condition_context,
                ("개선", "관리", "운동", "수면", "체중관리", "체중 관리", "lifestyle"),
            ):
                return (
                    "식사는 접시 구성을 단순하게 잡고, 운동은 걷기부터 시작하며, "
                    "수면과 체중 기록을 함께 확인해 주세요."
                )
            return (
                "저녁은 밥 양을 줄이고 채소와 단백질 반찬을 곁들이며, 달콤한 간식은 "
                "다음 기록에서 줄여 보세요."
            )
        if self._has_any_context_term(condition_context, HYPERTENSION_CONTEXT_TERMS):
            return (
                "다음 끼니에서 짠 국물, 짠 반찬, 가공식품을 줄이고 혈압 반응처럼 "
                "직접 확인 가능한 기록을 우선 점검해 주세요."
            )
        if self._has_any_context_term(condition_context, KIDNEY_CONTEXT_TERMS):
            return "다음 끼니에서는 국물과 가공식품을 줄이고, 기록된 식사량을 먼저 확인해 주세요."
        return "다음 끼니에서는 과식, 짠 음식, 당류 간식을 줄이고 확인 가능한 기록을 우선 점검해 주세요."

    def _condition_context(self, request: ChatbotRequest) -> str:
        parts = [request.message]
        profile = request.context.get("profile")
        if isinstance(profile, dict):
            conditions = profile.get("chronic_conditions")
            if isinstance(conditions, list):
                parts.extend(str(condition) for condition in conditions)

        parts.extend(turn.content for turn in request.conversation[-6:])
        return " ".join(parts).casefold()

    def _has_any_context_term(self, text: str, terms: tuple[str, ...]) -> bool:
        return any(term.casefold() in text for term in terms)

    def _confirmed_food_summary(self, context: dict[str, object]) -> str:
        entries = context.get("latest_confirmed_entries")
        if not isinstance(entries, dict):
            return ""

        foods = entries.get("foods")
        if not isinstance(foods, list):
            return ""

        lines: list[str] = []
        for raw_food in foods[:6]:
            if not isinstance(raw_food, dict):
                continue

            name = self._clean_label(raw_food.get("name"))
            if not name:
                continue

            meal_type = self._clean_label(raw_food.get("meal_type"))
            meal_label = MEAL_LABELS.get(meal_type.casefold(), meal_type or "식사")
            nutrient_text = self._nutrient_summary(raw_food.get("nutrients"))
            if nutrient_text:
                lines.append(f"{meal_label}: {name}, {nutrient_text}")
            else:
                lines.append(f"{meal_label}: {name}")

        return "\n".join(lines)

    def _nutrient_summary(self, raw_nutrients: object) -> str:
        if not isinstance(raw_nutrients, list):
            return ""

        nutrients: list[str] = []
        for raw_nutrient in raw_nutrients[:6]:
            if not isinstance(raw_nutrient, dict):
                continue

            raw_name = self._clean_label(raw_nutrient.get("name"))
            amount = raw_nutrient.get("amount")
            unit = self._clean_label(raw_nutrient.get("unit"))
            if not raw_name or amount is None or not unit:
                continue

            name = NUTRIENT_LABELS.get(raw_name.casefold(), raw_name)
            nutrients.append(f"{name} {self._format_amount(amount)}{unit}")

        return ", ".join(nutrients)

    def _clean_label(self, value: object) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()

    def _format_amount(self, value: object) -> str:
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(int(value)) if value.is_integer() else f"{value:g}"
        return str(value).strip()

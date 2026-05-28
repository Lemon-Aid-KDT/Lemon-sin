from __future__ import annotations

from lemon_ai_agent.chat_session import ChatbotRequest, ChatbotResponse
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    ChatIntentAnalysis,
    MedicalKnowledgeItem,
    analyze_chat_intent,
    contract_summary,
    policy_for_question,
    select_medical_knowledge,
    source_family_summary,
)
from lemon_ai_agent.llm import LLMMessage, LLMRequest, LocalLLMClient

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
        self._llm_client = llm_client
        self._safety_guard = SafetyGuard()

    def answer(self, request: ChatbotRequest) -> ChatbotResponse:
        warnings: list[str] = []
        policy = policy_for_question(request.message)
        analysis = analyze_chat_intent(request.message, request.context)
        knowledge_items = select_medical_knowledge(analysis)
        boundary_response = self._boundary_response(request, policy, warnings)
        if boundary_response is not None:
            return boundary_response

        fallback = self._fallback_response(request, warnings, policy, analysis, knowledge_items)

        if self._llm_client is None:
            return fallback

        try:
            llm_response = self._llm_client.generate(
                self._build_llm_request(request, policy, analysis, knowledge_items)
            )
        except Exception as exc:
            warnings.append(f"chatbot llm fallback: {exc}")
            return self._fallback_response(request, warnings, policy, analysis, knowledge_items)

        check = self._safety_guard.check_text(llm_response.text)
        warnings.extend(check.warnings)
        if not check.allowed:
            return self._fallback_response(request, warnings, policy, analysis, knowledge_items)
        grounding_check = self._safety_guard.check_grounding(
            llm_response.text,
            self._grounding_context(request, knowledge_items),
        )
        warnings.extend(grounding_check.warnings)
        has_required_shape = self._has_required_response_shape(llm_response.text)
        if not has_required_shape:
            warnings.append("Chatbot response contract not followed")
        if not grounding_check.allowed or not has_required_shape:
            return self._fallback_response(request, warnings, policy, analysis, knowledge_items)

        return ChatbotResponse(
            request_id=request.request_id,
            message=llm_response.text,
            provider=llm_response.provider,
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            requires_user_approval=False,
        )

    def _fallback_response(
        self,
        request: ChatbotRequest,
        warnings: list[str],
        policy: AnswerPolicy,
        analysis: ChatIntentAnalysis,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> ChatbotResponse:
        summary = self._safe_summary(request.context)
        confirmed_foods = self._confirmed_food_summary(request.context)
        if summary:
            summary_sentence = f"현재 입력 기준으로 {summary}"
        elif confirmed_foods:
            summary_sentence = f"확인된 기록은 {confirmed_foods}입니다."
        else:
            summary_sentence = "현재 확인된 기록을 기준으로 답변드릴 수 있습니다."

        if analysis.primary_intent == "symptom" and not analysis.boundary:
            next_action = self._symptom_next_action(analysis)
        elif policy.category == "chronic_condition_context":
            next_action = self._chronic_condition_next_action(request)
        elif policy.category == "supplement_question":
            next_action = (
                "제품 라벨의 섭취량, 원재료, 기능성 표시를 확인하고 같은 성분의 "
                "중복 섭취를 피하세요."
            )
        else:
            next_action = "확정된 식사, 영양제, 건강 기록을 먼저 확인해 주세요."

        caution = self._fallback_caution(request, policy, analysis)
        management_points = self._fallback_management_points(analysis, knowledge_items)

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
                f"- {self._source_basis(knowledge_items)}"
            ),
            provider="deterministic",
            used_tools=CHATBOT_TOOLS.copy(),
            safety_warnings=warnings,
            source_families=list(policy.source_families),
            requires_user_approval=False,
        )

    def _build_llm_request(
        self,
        request: ChatbotRequest,
        policy: AnswerPolicy,
        analysis: ChatIntentAnalysis,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> LLMRequest:
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
                        "For source basis, write briefly like: "
                        "'출처 기준: 질병관리청 건강정보, KDRIs 영양 기준'."
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
                        "Intent analysis:\n"
                        f"{self._intent_analysis_summary(analysis)}\n"
                        "Reviewed knowledge items:\n"
                        f"{self._knowledge_items_summary(knowledge_items)}\n"
                        "Answer strategy:\n"
                        f"{self._answer_strategy(analysis, knowledge_items)}\n"
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
            used_tools=CHATBOT_TOOLS.copy(),
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

    def _grounding_context(
        self,
        request: ChatbotRequest,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        conversation = "\n".join(turn.content for turn in request.conversation[-6:])
        summary = self._safe_summary(request.context)
        confirmed_foods = self._confirmed_food_summary(request.context)
        knowledge = "\n".join(item.concrete_guidance for item in knowledge_items)
        return "\n".join((request.message, conversation, summary, confirmed_foods, knowledge))

    def _has_required_response_shape(self, text: str) -> bool:
        return all(section in text for section in REQUIRED_CHATBOT_SECTIONS)

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
            if item.source.startswith("CDC"):
                source_names.append("CDC")
            elif item.source.startswith("NIDDK"):
                source_names.append("NIDDK")
            else:
                source_names.append(item.source)

        return ", ".join(dict.fromkeys(source_names))

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
        return "\n".join(
            (
                f"- {item.source} | topic={item.topic} | intent={item.intent} | "
                f"condition={item.condition or 'general'} | guidance={item.concrete_guidance} | "
                f"url={item.source_url}"
            )
            for item in knowledge_items
        )

    def _answer_strategy(
        self,
        analysis: ChatIntentAnalysis,
        knowledge_items: tuple[MedicalKnowledgeItem, ...],
    ) -> str:
        if analysis.boundary:
            return "Apply the boundary response and do not provide normal coaching."
        if analysis.primary_intent == "symptom":
            return "Start with red-flag screening, then rest, hydration, cool place, and observation."
        if knowledge_items:
            return "Use the reviewed guidance items as concrete coaching points without exposing raw retrieval."
        return "Use general health-management coaching only within the allowed source families."

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

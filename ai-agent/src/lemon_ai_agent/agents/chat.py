from __future__ import annotations

from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    contract_summary,
    daily_summary_policy,
    policy_for_question,
    source_family_summary,
)
from lemon_ai_agent.llm import LLMMessage, LLMRequest, LocalLLMClient
from lemon_ai_agent.schemas import DailyCoachingResult


class ChatAgent:
    """Explains recommendations from computed result traces only."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self._llm_client = llm_client
        self._safety_guard = SafetyGuard()
        self.last_llm_warnings: list[str] = []
        self.last_llm_error: str | None = None
        self.last_provider = "deterministic"

    def answer(self, question: str, result: DailyCoachingResult) -> str:
        self.last_llm_warnings = []
        self.last_llm_error = None
        self.last_provider = "deterministic"
        policy = policy_for_question(question)
        return self._answer_with_policy(question, result, policy)

    def answer_daily_summary(self, result: DailyCoachingResult) -> str:
        self.last_llm_warnings = []
        self.last_llm_error = None
        self.last_provider = "deterministic"
        return self._answer_with_policy(
            "Summarize today's coaching.",
            result,
            daily_summary_policy(),
        )

    def _answer_with_policy(
        self,
        question: str,
        result: DailyCoachingResult,
        policy: AnswerPolicy,
    ) -> str:
        boundary_answer = self._boundary_answer(question, policy)
        if boundary_answer is not None:
            return boundary_answer

        fallback = self._deterministic_answer(question, result, policy)

        if self._llm_client is None:
            return fallback

        try:
            response = self._llm_client.generate(
                self._build_llm_request(question, result, policy)
            )
        except Exception as exc:
            self.last_llm_error = str(exc)
            return fallback

        check = self._safety_guard.check_text(response.text)
        self.last_llm_warnings.extend(check.warnings)
        if not check.allowed:
            return fallback

        self.last_provider = response.provider
        return response.text

    def _deterministic_answer(
        self,
        question: str,
        result: DailyCoachingResult,
        policy: AnswerPolicy,
    ) -> str:
        recommendation_titles = ", ".join(
            _ko_recommendation_title(recommendation.title)
            for recommendation in result.recommendations[:3]
        )
        _, warnings = self._safety_guard.sanitize_trace(result.trace[:4])
        self.last_llm_warnings.extend(warnings)

        if not recommendation_titles:
            recommendation_titles = "현재 입력 기준으로 우선 실행할 코칭 항목은 크지 않습니다"

        if policy.category == "chronic_condition_context":
            condition_note = self._chronic_condition_note(question)
        else:
            condition_note = ""

        return (
            "요약: "
            f"{result.date}에 확인된 입력과 최근 흐름을 기준으로 답변을 정리했습니다. "
            f"{condition_note}"
            "현재 입력 기준: "
            f"{recommendation_titles}. "
            "주의: "
            "이 내용은 건강 관리를 위한 참고 자료이며, 진단이나 처방처럼 개인 의료 "
            "결정을 대신하지 않습니다. "
            "다음 행동: "
            "증상, 복용 중인 약, 만성질환, 검사 수치가 관련되면 자격을 갖춘 "
            "전문가와 상담해 주세요. "
            "출처 메모: "
            "검토된 건강관리 지식 범위 안에서만 설명했습니다."
        )

    def _build_llm_request(
        self,
        question: str,
        result: DailyCoachingResult,
        policy: AnswerPolicy,
    ) -> LLMRequest:
        findings = "; ".join(
            (
                f"{finding.nutrient}: {finding.level.value}, "
                f"{finding.total_amount}{finding.unit}"
            )
            for finding in result.findings[:3]
        )
        recommendations = "; ".join(
            f"{item.title}: {item.rationale}" for item in result.recommendations[:3]
        )
        trace_lines, warnings = self._safety_guard.sanitize_trace(result.trace[:4])
        self.last_llm_warnings.extend(warnings)
        trace = " / ".join(trace_lines)

        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You explain Lemon Aid health-management coaching. "
                        "Do not diagnose, treat, prescribe, guarantee effects, or "
                        "promote buying a specific product. Use cautious phrasing "
                        "such as 'based on the current input', 'may need attention', "
                        "and 'consult a qualified professional'. Do not create new "
                        "health judgments beyond the supplied findings, "
                        "recommendations, and trace. Do not create new health facts "
                        "without a listed source family. Follow the response contract "
                        "sections in Korean."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Question: {question.strip()}\n"
                        f"Question category: {policy.category}\n"
                        f"Classification reasons: {', '.join(policy.reasons)}\n"
                        "Allowed source families:\n"
                        f"{source_family_summary(policy.source_families)}\n"
                        "Response contract:\n"
                        f"{contract_summary(policy.contract)}\n"
                        f"Date: {result.date}\n"
                        f"Top findings: {findings or 'none'}\n"
                        f"Top recommendations: {recommendations or 'none'}\n"
                        f"Trace summary: {trace or 'none'}"
                    ),
                ),
            ],
            temperature=0.1,
        )

    def _boundary_answer(
        self,
        question: str,
        policy: AnswerPolicy,
    ) -> str | None:
        if policy.category == "symptom_or_emergency":
            self.last_llm_warnings.append("Emergency escalation boundary applied")
            return (
                "즉시 안내: 가슴 통증, 숨참, 마비, 실신처럼 응급 가능성이 있는 증상은 "
                "식단 코칭보다 긴급 확인이 우선입니다. 지금 증상이 지속되거나 심하면 "
                "119에 연락하거나 가까운 응급실로 이동하세요. "
                "주의: Lemon Aid는 이런 상황에서 개인 의료 판단을 대신하지 않습니다. "
                "연결 자원: E-Gen 응급의료포털(https://www.e-gen.or.kr/)과 "
                "보건복지상담센터 129를 참고할 수 있습니다."
            )

        if policy.category == "mental_health_risk":
            self.last_llm_warnings.append("Mental health escalation boundary applied")
            return (
                "즉시 안내: 자해, 자살 생각, 극단적인 굶기처럼 안전 위험이 보이면 "
                "일반 건강관리 안내를 멈추고 사람의 도움을 먼저 받아야 합니다. "
                "혼자 있지 말고 신뢰할 수 있는 사람이나 가까운 의료기관에 즉시 알리세요. "
                "주의: 체중 관리 조언보다 현재 안전 확인이 우선입니다. "
                "연결 자원: 자살예방상담전화 109, 보건복지상담센터 129, "
                "국가정신건강정보포털을 이용할 수 있습니다."
            )

        if policy.category == "drug_or_interaction":
            self.last_llm_warnings.append("Drug interaction boundary applied")
            return (
                "요약: 약, 질환, 영양제 병용 질문은 Lemon Aid가 허용 또는 금지로 "
                "판정하지 않습니다. "
                "주의: 현재 복용 중인 약, 질환, 검사 수치, 제품 성분표에 따라 확인할 "
                "내용이 달라질 수 있습니다. "
                "다음 행동: 제품 라벨과 복용 중인 약 목록을 가지고 의사 또는 약사에게 "
                "확인하세요. 임의로 시작, 중단, 증량, 감량하지 않는 것이 안전합니다. "
                "출처 메모: supplement_reference, drug_safety_boundary, "
                "chronic_condition source family 기준의 안전 경계 응답입니다."
            )

        if policy.category == "out_of_scope":
            self.last_llm_warnings.append("Out-of-scope medical decision boundary applied")
            return (
                "요약: 개인 복용량, 처방 변경, 질환 판단처럼 개인 의료 결정에 해당하는 "
                "질문은 Lemon Aid가 결정하지 않습니다. "
                "주의: 비타민 D 같은 영양소도 검사 결과, 현재 섭취량, 복용 중인 약, "
                "질환 맥락에 따라 확인이 필요합니다. "
                "다음 행동: 현재 식사와 영양제 섭취량을 정리하고, 필요하면 혈액 검사 "
                "결과를 바탕으로 전문가와 상담하세요. "
                "출처 메모: nutrition_reference, supplement_reference, "
                "drug_safety_boundary 기준의 경계 응답입니다."
            )

        return None

    def _chronic_condition_note(self, question: str) -> str:
        lowered = question.casefold()
        if "라면" in lowered or "noodle" in lowered:
            return (
                "금지 단정 대신 나트륨, 탄수화물, 국물 섭취량, 채소와 단백질 보완, "
                "식후 혈당 또는 혈압 반응 확인을 함께 봅니다. "
            )
        return ""


def _ko_recommendation_title(title: str) -> str:
    lowered = title.lower()
    if lowered.startswith("reduce "):
        return f"{_ko_nutrient_label(title[7:])} 섭취를 줄이는 방향"
    if lowered.startswith("add ") and " from food first" in lowered:
        nutrient = lowered.removeprefix("add ").removesuffix(" from food first")
        return f"{_ko_nutrient_label(nutrient)}을 음식으로 먼저 보완하는 방향"
    if lowered.startswith("consider ") and " ingredient support" in lowered:
        nutrient = lowered.removeprefix("consider ").removesuffix(" ingredient support")
        return f"{_ko_nutrient_label(nutrient)} 보충 필요성을 신중히 확인하는 방향"
    return title


def _ko_nutrient_label(nutrient: str) -> str:
    normalized = " ".join(nutrient.strip().lower().replace("_", " ").split())
    labels = {
        "vitamin d": "비타민 D",
        "sodium": "나트륨",
        "protein": "단백질",
        "fiber": "식이섬유",
        "magnesium": "마그네슘",
        "calcium": "칼슘",
        "iron": "철분",
        "omega-3": "오메가-3",
    }
    return labels.get(normalized, nutrient.strip())

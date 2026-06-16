from __future__ import annotations

from lemon_ai_agent.nutrient_names import nutrient_ko
from lemon_ai_agent.schemas import (
    CoachingRecommendation,
    FindingLevel,
    NutrientFinding,
    PersonalizationContext,
)

FOOD_FIRST_SUGGESTIONS = {
    "protein": "두부, 달걀, 생선, 닭고기처럼 단백질이 풍부한 음식을 더해보세요.",
    "fiber": "채소, 콩, 귀리, 미역처럼 식이섬유가 풍부한 음식을 더해보세요.",
    "vitamin d": "달걀이나 강화식품처럼 비타민 D가 들어 있는 음식을 챙겨보세요.",
    "magnesium": "견과류, 콩, 잎채소처럼 마그네슘이 풍부한 음식을 더해보세요.",
}

SUPPLEMENT_INGREDIENT_ALLOWED = {
    "vitamin d",
    "magnesium",
    "omega-3",
    "iron",
    "calcium",
}
REPEATED_PATTERN_THRESHOLD = 2


class CoachingAgent:
    def recommend(
        self,
        findings: list[NutrientFinding],
        context: PersonalizationContext,
    ) -> list[CoachingRecommendation]:
        recommendations: list[CoachingRecommendation] = []
        memory_patterns = _memory_patterns(context.agent_memory)

        for finding in findings:
            nutrient_key = finding.nutrient.lower()
            nutrient_label = nutrient_ko(finding.nutrient)
            repeat_count = memory_patterns.get(nutrient_key, 0)
            repeat_prefix = (
                f" 최근 확인된 기록에서 이 패턴이 {repeat_count}번 나타났어요."
                if repeat_count >= REPEATED_PATTERN_THRESHOLD
                else ""
            )
            if finding.level in {FindingLevel.HIGH, FindingLevel.RISKY}:
                recommendations.append(
                    CoachingRecommendation(
                        category="reduce",
                        title=f"{nutrient_label} 섭취 줄여보기",
                        rationale=f"{finding.message}{repeat_prefix}",
                        priority=min(
                            10,
                            (10 if finding.level == FindingLevel.RISKY else 8)
                            + min(repeat_count, 2),
                        ),
                        requires_professional_consult=finding.level == FindingLevel.RISKY,
                    )
                )
            elif finding.level == FindingLevel.LOW:
                food_text = FOOD_FIRST_SUGGESTIONS.get(
                    nutrient_key,
                    f"{nutrient_label} 함량이 높은 음식을 더해보세요.",
                )
                recommendations.append(
                    CoachingRecommendation(
                        category="add_food",
                        title=f"{nutrient_label}, 먼저 음식으로 채워보기",
                        rationale=f"{finding.message} {food_text}{repeat_prefix}",
                        priority=min(10, 7 + min(repeat_count, 2)),
                    )
                )
                if nutrient_key in SUPPLEMENT_INGREDIENT_ALLOWED:
                    recommendations.append(
                        CoachingRecommendation(
                            category="consider_ingredient",
                            title=f"{nutrient_label} 영양제로 보충 고려하기",
                            rationale=(
                                "음식만으로 채우기 어렵다면, 복용 중인 약이나 만성질환이 "
                                "있을 때는 의사·약사와 상담한 뒤 영양제 보충을 "
                                "고려해보세요."
                            ),
                            priority=5,
                            requires_professional_consult=bool(
                                context.medication_notes or context.caution_tags
                            ),
                        )
                    )

        if context.health_trend_notes:
            recommendations.append(
                CoachingRecommendation(
                    category="mission",
                    title="오늘은 가벼운 식단 관리 미션 하나 해보기",
                    rationale="최근 추이에서 살펴볼 점이 있어요: "
                    + " / ".join(context.health_trend_notes),
                    priority=6,
                )
            )

        return sorted(recommendations, key=lambda item: item.priority, reverse=True)


def _memory_patterns(agent_memory: dict[str, object]) -> dict[str, int]:
    """Return repeated nutrient pattern counters from injected Agent memory."""
    summaries = agent_memory.get("summaries", [])
    if not isinstance(summaries, list):
        return {}

    counters: dict[str, int] = {}
    for item in summaries:
        if not isinstance(item, dict):
            continue
        summary = item.get("summary_json", {})
        if not isinstance(summary, dict):
            continue
        patterns = summary.get("repeated_nutrient_patterns", {})
        if not isinstance(patterns, dict):
            continue
        for nutrient, count in patterns.items():
            if not isinstance(nutrient, str):
                continue
            try:
                repeat_count = int(count)
            except (TypeError, ValueError):
                continue
            key = _canonical_memory_nutrient_key(nutrient)
            counters[key] = max(counters.get(key, 0), repeat_count)
    return counters


def _canonical_memory_nutrient_key(nutrient: str) -> str:
    normalized = " ".join(nutrient.strip().lower().replace("_", " ").split())
    aliases = {
        "vitamin-d": "vitamin d",
        "vitamin d": "vitamin d",
    }
    return aliases.get(normalized, normalized)

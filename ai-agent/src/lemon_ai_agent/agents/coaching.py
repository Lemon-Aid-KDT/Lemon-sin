from __future__ import annotations

from lemon_ai_agent.schemas import (
    CoachingRecommendation,
    FindingLevel,
    NutrientFinding,
    PersonalizationContext,
)


FOOD_FIRST_SUGGESTIONS = {
    "protein": "Add protein-rich foods such as tofu, eggs, fish, or chicken.",
    "fiber": "Add fiber-rich foods such as vegetables, beans, oats, or seaweed.",
    "vitamin d": "Consider vitamin D-rich foods such as eggs or fortified foods.",
    "magnesium": "Add magnesium-rich foods such as nuts, beans, or leafy vegetables.",
}

SUPPLEMENT_INGREDIENT_ALLOWED = {
    "vitamin d",
    "magnesium",
    "omega-3",
    "iron",
    "calcium",
}


class CoachingAgent:
    def recommend(
        self,
        findings: list[NutrientFinding],
        context: PersonalizationContext,
    ) -> list[CoachingRecommendation]:
        recommendations: list[CoachingRecommendation] = []

        for finding in findings:
            nutrient_key = finding.nutrient.lower()
            if finding.level in {FindingLevel.HIGH, FindingLevel.RISKY}:
                recommendations.append(
                    CoachingRecommendation(
                        category="reduce",
                        title=f"Reduce {finding.nutrient}",
                        rationale=finding.message,
                        priority=10 if finding.level == FindingLevel.RISKY else 8,
                        requires_professional_consult=finding.level == FindingLevel.RISKY,
                    )
                )
            elif finding.level == FindingLevel.LOW:
                food_text = FOOD_FIRST_SUGGESTIONS.get(
                    nutrient_key,
                    f"Add foods that provide {finding.nutrient}.",
                )
                recommendations.append(
                    CoachingRecommendation(
                        category="add_food",
                        title=f"Add {finding.nutrient} from food first",
                        rationale=f"{finding.message} {food_text}",
                        priority=7,
                    )
                )
                if nutrient_key in SUPPLEMENT_INGREDIENT_ALLOWED:
                    recommendations.append(
                        CoachingRecommendation(
                            category="consider_ingredient",
                            title=f"Consider {finding.nutrient} ingredient support",
                            rationale=(
                                "If food intake is difficult, consider this ingredient "
                                "with professional review when medication or chronic "
                                "condition context exists."
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
                    title="Follow a small meal-management mission today",
                    rationale="Recent trend signals need attention: "
                    + " / ".join(context.health_trend_notes),
                    priority=6,
                )
            )

        return sorted(recommendations, key=lambda item: item.priority, reverse=True)


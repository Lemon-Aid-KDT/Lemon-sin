from __future__ import annotations

from lemon_ai_agent.agents.action import ActionAgent
from lemon_ai_agent.agents.coaching import CoachingAgent
from lemon_ai_agent.agents.intake import IntakeAgent
from lemon_ai_agent.agents.personalization import PersonalizationAgent
from lemon_ai_agent.engines.nutrition import NutritionEngine
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.schemas import (
    DailyCoachingResult,
    DailyIntake,
    HealthTrend,
    ReferenceRange,
    UserProfile,
)


class DailyHealthAgent:
    """Coordinates deterministic engines, Agent logic, and safety checks."""

    def __init__(self, references: list[ReferenceRange]) -> None:
        self._intake_agent = IntakeAgent()
        self._nutrition_engine = NutritionEngine(references)
        self._personalization_agent = PersonalizationAgent()
        self._coaching_agent = CoachingAgent()
        self._action_agent = ActionAgent()
        self._safety_guard = SafetyGuard()

    def run(
        self,
        profile: UserProfile,
        intake: DailyIntake,
        trends: list[HealthTrend] | None = None,
    ) -> DailyCoachingResult:
        normalized = self._intake_agent.normalize(intake)
        findings = self._nutrition_engine.evaluate(normalized)
        context = self._personalization_agent.build_context(profile, trends or [])
        recommendations = self._coaching_agent.recommend(findings, context)

        safety_warnings: list[str] = []
        for recommendation in recommendations:
            check = self._safety_guard.check_text(
                f"{recommendation.title} {recommendation.rationale}"
            )
            safety_warnings.extend(check.warnings)

        safe_recommendations = [
            recommendation
            for recommendation in recommendations
            if self._safety_guard.check_text(
                f"{recommendation.title} {recommendation.rationale}"
            ).allowed
        ]
        actions = self._action_agent.propose_actions(safe_recommendations)

        return DailyCoachingResult(
            user_id=profile.user_id,
            date=normalized.date,
            findings=findings,
            recommendations=safe_recommendations,
            actions=actions,
            safety_warnings=safety_warnings,
        )


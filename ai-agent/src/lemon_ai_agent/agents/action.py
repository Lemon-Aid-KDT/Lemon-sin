from __future__ import annotations

from lemon_ai_agent.schemas import CoachingRecommendation, ProposedAction


class ActionAgent:
    def propose_actions(
        self, recommendations: list[CoachingRecommendation]
    ) -> list[ProposedAction]:
        actions: list[ProposedAction] = []
        for recommendation in recommendations:
            if recommendation.category == "consider_ingredient":
                actions.append(
                    ProposedAction(
                        action_type="supplement_reminder",
                        title=f"Review reminder for {recommendation.title}",
                        payload={"source": recommendation.title},
                    )
                )
            elif recommendation.category == "mission":
                actions.append(
                    ProposedAction(
                        action_type="daily_mission",
                        title=recommendation.title,
                        payload={"rationale": recommendation.rationale},
                    )
                )
        return actions


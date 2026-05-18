import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lemon_ai_agent import DailyHealthAgent
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.schemas import (
    DailyIntake,
    FindingLevel,
    FoodIntake,
    HealthTrend,
    NutrientAmount,
    ReferenceRange,
    SupplementIntake,
    UserProfile,
)


class DailyHealthAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = DailyHealthAgent(
            references=[
                ReferenceRange("protein", 60, "g"),
                ReferenceRange("sodium", 2000, "mg", upper_limit=2300),
                ReferenceRange("vitamin d", 15, "mcg", upper_limit=100),
                ReferenceRange("magnesium", 350, "mg", upper_limit=700),
            ]
        )

    def test_recommends_reduction_food_first_and_ingredient_support(self) -> None:
        profile = UserProfile(
            user_id="user-1",
            age=52,
            gender="male",
            goals=["meal_management"],
            chronic_conditions=["hypertension"],
            medications=["blood_pressure_medication"],
        )
        intake = DailyIntake(
            user_id="user-1",
            date="2026-05-18",
            foods=[
                FoodIntake(
                    name="instant noodles",
                    meal_type="lunch",
                    serving_label="1 bowl",
                    nutrients=[
                        NutrientAmount("sodium", 2600, "mg"),
                        NutrientAmount("protein", 25, "g"),
                        NutrientAmount("vitamin d", 2, "mcg"),
                    ],
                )
            ],
            supplements=[
                SupplementIntake(
                    product_name="multivitamin",
                    ingredients=[NutrientAmount("magnesium", 100, "mg")],
                )
            ],
        )
        trends = [
            HealthTrend(
                metric="meal_score",
                direction="down",
                severity="watch",
                summary="Meal score has dropped for 7 days.",
            )
        ]

        result = self.agent.run(profile, intake, trends)

        levels = {finding.nutrient: finding.level for finding in result.findings}
        self.assertEqual(levels["sodium"], FindingLevel.RISKY)
        self.assertEqual(levels["protein"], FindingLevel.LOW)
        self.assertEqual(levels["vitamin d"], FindingLevel.LOW)

        categories = [item.category for item in result.recommendations]
        self.assertIn("reduce", categories)
        self.assertIn("add_food", categories)
        self.assertIn("consider_ingredient", categories)
        self.assertIn("mission", categories)
        self.assertTrue(all(action.requires_user_approval for action in result.actions))

    def test_safety_guard_blocks_medical_and_product_claims(self) -> None:
        guard = SafetyGuard()

        unsafe = guard.check_text("당뇨입니다. 이 브랜드 제품을 구매하세요.")

        self.assertFalse(unsafe.allowed)
        self.assertGreaterEqual(len(unsafe.warnings), 2)


if __name__ == "__main__":
    unittest.main()


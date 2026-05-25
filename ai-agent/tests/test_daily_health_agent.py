import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lemon_ai_agent import DailyHealthAgent
from lemon_ai_agent.agents.chat import ChatAgent
from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.schemas import (
    DailyIntake,
    FindingLevel,
    FoodIntake,
    HealthTrend,
    IntakeSource,
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
                ReferenceRange("iron", 10, "mg", upper_limit=45),
                ReferenceRange("calcium", 800, "mg", upper_limit=2500),
                ReferenceRange("fiber", 25, "g"),
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
            sources=[
                IntakeSource(
                    source_type="food_ocr",
                    image_id="meal-image-1",
                    raw_ocr_text="instant noodles sodium 2600mg",
                    user_confirmed=True,
                ),
                IntakeSource(
                    source_type="supplement_ocr",
                    image_id="supplement-image-1",
                    raw_ocr_text="multivitamin magnesium 100mg",
                    user_confirmed=True,
                ),
            ],
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
                    times_per_day=2,
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
        self.assertEqual(result.sources[0].image_id, "meal-image-1")
        supplement_totals = {
            item.ingredient: item.total_amount for item in result.supplement_totals
        }
        self.assertEqual(supplement_totals["magnesium"], 200)
        self.assertTrue(any("confirmed source records: 2" in item for item in result.trace))

    def test_safety_guard_blocks_medical_and_product_claims(self) -> None:
        guard = SafetyGuard()

        unsafe = guard.check_text("당뇨입니다. 이 브랜드 제품을 구매하세요.")
        chronic_certainty = guard.check_text("고혈압입니다. 나트륨을 완전히 금지하세요.")

        self.assertFalse(unsafe.allowed)
        self.assertGreaterEqual(len(unsafe.warnings), 2)
        self.assertFalse(chronic_certainty.allowed)
        self.assertIn("Forbidden medical expression detected", chronic_certainty.warnings)

    def test_upper_limit_excess_for_multiple_supplement_ingredients_is_risky(
        self,
    ) -> None:
        profile = UserProfile(user_id="user-2", age=41, gender="female")
        intake = DailyIntake(
            user_id="user-2",
            date="2026-05-18",
            supplements=[
                SupplementIntake(
                    product_name="stacked mineral pack",
                    ingredients=[
                        NutrientAmount("magnesium", 800, "mg"),
                        NutrientAmount("iron", 60, "mg"),
                        NutrientAmount("calcium", 3000, "mg"),
                    ],
                )
            ],
        )

        result = self.agent.run(profile, intake)

        levels = {finding.nutrient: finding.level for finding in result.findings}
        self.assertEqual(levels["magnesium"], FindingLevel.RISKY)
        self.assertEqual(levels["iron"], FindingLevel.RISKY)
        self.assertEqual(levels["calcium"], FindingLevel.RISKY)
        risky_titles = [
            item.title for item in result.recommendations if item.category == "reduce"
        ]
        self.assertGreaterEqual(len(risky_titles), 3)

    def test_medication_context_uses_caution_not_definitive_claims(self) -> None:
        profile = UserProfile(
            user_id="user-3",
            age=65,
            gender="other",
            medications=["warfarin"],
            chronic_conditions=["kidney_disease"],
        )
        intake = DailyIntake(
            user_id="user-3",
            date="2026-05-18",
            foods=[
                FoodIntake(
                    name="light meal",
                    meal_type="dinner",
                    serving_label="1 plate",
                    nutrients=[
                        NutrientAmount("protein", 20, "g"),
                        NutrientAmount("fiber", 5, "g"),
                        NutrientAmount("vitamin d", 1, "mcg"),
                    ],
                )
            ],
        )

        result = self.agent.run(profile, intake)
        text = " ".join(
            f"{item.title} {item.rationale}" for item in result.recommendations
        )

        self.assertIn("professional review", text)
        self.assertNotIn("safe for you", text.lower())
        self.assertNotIn("take this", text.lower())
        self.assertTrue(
            any(item.requires_professional_consult for item in result.recommendations)
        )

    def test_future_blood_trend_trace_and_chat_avoid_diagnosis(self) -> None:
        profile = UserProfile(user_id="user-4", age=38, gender="male")
        intake = DailyIntake(
            user_id="user-4",
            date="2026-05-18",
            foods=[
                FoodIntake(
                    name="balanced lunch",
                    meal_type="lunch",
                    serving_label="1 plate",
                    nutrients=[
                        NutrientAmount("protein", 62, "g"),
                        NutrientAmount("fiber", 26, "g"),
                        NutrientAmount("sodium", 1700, "mg"),
                    ],
                )
            ],
        )
        trends = [
            HealthTrend(
                metric="blood_glucose",
                direction="up",
                severity="attention",
                summary="Recent readings rose after late meals.",
            )
        ]

        result = self.agent.run(profile, intake, trends)
        answer = ChatAgent().answer("Why did you recommend this?", result)

        self.assertIn("blood_glucose", " ".join(result.trace))
        self.assertIn("최근 흐름", answer)
        self.assertNotIn("diabetes", answer.lower())
        self.assertNotIn("diagnosis", answer.lower())

    def test_unconfirmed_ocr_source_returns_preview_only(self) -> None:
        profile = UserProfile(user_id="user-5", age=45, gender="female")
        intake = DailyIntake(
            user_id="user-5",
            date="2026-05-18",
            sources=[
                IntakeSource(
                    source_type="food_ocr",
                    image_id="unconfirmed-meal",
                    raw_ocr_text="instant noodles sodium 2600mg",
                    user_confirmed=False,
                )
            ],
            foods=[
                FoodIntake(
                    name="instant noodles",
                    meal_type="lunch",
                    serving_label="1 bowl",
                    nutrients=[NutrientAmount("sodium", 2600, "mg")],
                )
            ],
        )

        result = self.agent.run(profile, intake)

        self.assertEqual(result.approval_status, "requires_confirmation")
        self.assertEqual(result.findings, [])
        self.assertEqual(result.recommendations, [])
        self.assertEqual(result.actions, [])
        self.assertEqual(result.supplement_totals, [])
        self.assertIn("requires user confirmation", " ".join(result.trace))

    def test_nutrient_aliases_and_units_are_normalized_before_evaluation(self) -> None:
        profile = UserProfile(user_id="user-6", age=29, gender="other")
        intake = DailyIntake(
            user_id="user-6",
            date="2026-05-18",
            foods=[
                FoodIntake(
                    name="fortified breakfast",
                    meal_type="breakfast",
                    serving_label="1 serving",
                    nutrients=[
                        NutrientAmount("Vitamin D", 400, "IU"),
                        NutrientAmount("비타민D", 5, "mcg"),
                    ],
                )
            ],
        )

        result = self.agent.run(profile, intake)

        vitamin_d_findings = [
            finding for finding in result.findings if finding.nutrient == "vitamin d"
        ]
        self.assertEqual(len(vitamin_d_findings), 1)
        self.assertEqual(vitamin_d_findings[0].total_amount, 15)
        self.assertEqual(vitamin_d_findings[0].unit, "mcg")
        self.assertEqual(vitamin_d_findings[0].level, FindingLevel.ADEQUATE)

    def test_unsafe_trend_trace_is_sanitized_before_result_and_chat_output(self) -> None:
        profile = UserProfile(user_id="user-7", age=50, gender="male")
        intake = DailyIntake(
            user_id="user-7",
            date="2026-05-18",
            foods=[
                FoodIntake(
                    name="balanced lunch",
                    meal_type="lunch",
                    serving_label="1 plate",
                    nutrients=[NutrientAmount("protein", 65, "g")],
                )
            ],
        )
        trends = [
            HealthTrend(
                metric="blood_glucose",
                direction="up",
                severity="attention",
                summary="당뇨입니다. 이 제품을 구매하세요.",
            )
        ]

        result = self.agent.run(profile, intake, trends)
        trace_text = " ".join(result.trace)
        answer = ChatAgent().answer("Why?", result)

        self.assertIn("trace item withheld by policy guard", trace_text)
        self.assertIn("Trace text blocked", " ".join(result.safety_warnings))
        self.assertNotIn("당뇨입니다", trace_text)
        self.assertNotIn("제품을 구매", trace_text)
        self.assertNotIn("당뇨입니다", answer)
        self.assertNotIn("제품을 구매", answer)


if __name__ == "__main__":
    unittest.main()

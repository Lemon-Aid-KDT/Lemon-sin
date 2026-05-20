import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lemon_ai_agent.adapters import (  # noqa: E402
    AgentInput,
    DailyHealthAgentAppAdapter,
    InMemoryAgentRunLogger,
)
from lemon_ai_agent.llm import FakeLLMClient  # noqa: E402


class _MemoryWriter:
    def __init__(self) -> None:
        self.records = []

    def write(self, user_id, result) -> None:
        self.records.append((user_id, result.approval_status))


def _agent_input(
    *,
    request_id: str = "req-1",
    user_confirmed: bool = True,
    unsafe_trend: bool = False,
) -> AgentInput:
    trend_summary = (
        "당뇨입니다. 이 제품을 구매하세요."
        if unsafe_trend
        else "Meal score has dropped for 7 days."
    )
    return AgentInput(
        request_id=request_id,
        user_id="user-app-1",
        context={
            "profile": {
                "age": 52,
                "gender": "male",
                "goals": ["meal_management"],
                "chronic_conditions": ["hypertension"],
                "medications": ["blood_pressure_medication"],
            }
        },
        payload={
            "date": "2026-05-18",
            "sources": [
                {
                    "source_type": "food_ocr",
                    "image_id": "meal-image-1",
                    "raw_ocr_text": "instant noodles sodium 2600mg",
                    "user_confirmed": user_confirmed,
                }
            ],
            "foods": [
                {
                    "name": "instant noodles",
                    "meal_type": "lunch",
                    "serving_label": "1 bowl",
                    "nutrients": [
                        {"name": "sodium", "amount": 2600, "unit": "mg"},
                        {"name": "protein", "amount": 25, "unit": "g"},
                    ],
                }
            ],
            "supplements": [
                {
                    "product_name": "multivitamin",
                    "times_per_day": 1,
                    "ingredients": [
                        {"name": "magnesium", "amount": 100, "unit": "mg"}
                    ],
                }
            ],
            "health_trends": [
                {
                    "metric": "meal_score",
                    "direction": "down",
                    "severity": "watch",
                    "summary": trend_summary,
                }
            ],
            "reference_ranges": [
                {
                    "nutrient": "protein",
                    "target": 60,
                    "unit": "g",
                    "upper_limit": None,
                },
                {
                    "nutrient": "sodium",
                    "target": 2000,
                    "unit": "mg",
                    "upper_limit": 2300,
                },
                {
                    "nutrient": "magnesium",
                    "target": 350,
                    "unit": "mg",
                    "upper_limit": 700,
                },
            ],
        },
    )


class DailyHealthAgentAppAdapterTest(unittest.TestCase):
    def test_adapter_maps_agent_input_to_daily_health_result(self) -> None:
        output = DailyHealthAgentAppAdapter().run(_agent_input())

        self.assertEqual(output.request_id, "req-1")
        self.assertEqual(output.user_id, "user-app-1")
        self.assertEqual(output.status, "completed")
        self.assertEqual(output.approval_status, "confirmed")
        self.assertIn("nutrition_engine", output.used_tools)
        self.assertFalse(output.debug_trace)
        levels = {finding.nutrient: finding.level for finding in output.findings}
        self.assertEqual(levels["sodium"], "risky")
        self.assertEqual(levels["protein"], "low")

    def test_unconfirmed_ocr_returns_preview_without_actions(self) -> None:
        logger = InMemoryAgentRunLogger()
        output = DailyHealthAgentAppAdapter(run_logger=logger).run(
            _agent_input(request_id="req-preview", user_confirmed=False)
        )

        self.assertEqual(output.status, "preview")
        self.assertEqual(output.approval_status, "requires_confirmation")
        self.assertTrue(output.requires_user_approval)
        self.assertEqual(output.findings, [])
        self.assertEqual(output.recommendations, [])
        self.assertEqual(output.actions, [])
        self.assertEqual(logger.records, [])

    def test_confirmed_result_can_update_memory_after_agent_run(self) -> None:
        memory = _MemoryWriter()
        output = DailyHealthAgentAppAdapter(memory_writer=memory).run(_agent_input())

        self.assertEqual(output.status, "completed")
        self.assertEqual(memory.records, [("user-app-1", "confirmed")])

    def test_agent_memory_context_is_used_for_repeated_pattern_recommendation(
        self,
    ) -> None:
        agent_input = _agent_input(request_id="req-memory")
        agent_input.context["agent_memory"] = {
            "summaries": [
                {
                    "memory_type": "nutrition_patterns",
                    "summary_json": {
                        "repeated_nutrient_patterns": {
                            "protein": "3",
                        }
                    },
                }
            ]
        }

        output = DailyHealthAgentAppAdapter().run(agent_input)

        self.assertIn("agent_memory", output.used_tools)
        protein_recommendation = next(
            item
            for item in output.recommendations
            if item.title == "Add protein from food first"
        )
        self.assertIn("appeared 3 times", protein_recommendation.rationale)
        self.assertEqual(protein_recommendation.priority, 9)

    def test_adapter_sanitizes_trace_and_hides_debug_trace_by_default(self) -> None:
        output = DailyHealthAgentAppAdapter().run(
            _agent_input(request_id="req-unsafe", unsafe_trend=True)
        )
        output_text = " ".join(
            [
                output.message,
                " ".join(output.safety_warnings),
                " ".join(output.debug_trace),
            ]
        )

        self.assertFalse(output.debug_trace)
        self.assertIn("Trace text blocked", output_text)
        self.assertNotIn("당뇨입니다", output_text)
        self.assertNotIn("제품을 구매", output_text)

    def test_debug_trace_is_sanitized_when_explicitly_enabled(self) -> None:
        output = DailyHealthAgentAppAdapter(include_debug_trace=True).run(
            _agent_input(request_id="req-debug", unsafe_trend=True)
        )
        trace_text = " ".join(output.debug_trace)

        self.assertIn("trace item withheld by policy guard", trace_text)
        self.assertNotIn("당뇨입니다", trace_text)
        self.assertNotIn("제품을 구매", trace_text)

    def test_fake_llm_provider_runs_without_network_and_logs_zero_cost(self) -> None:
        logger = InMemoryAgentRunLogger()
        client = FakeLLMClient(
            response_text="현재 입력된 정보 기준으로 주의가 필요할 수 있습니다."
        )

        output = DailyHealthAgentAppAdapter(
            llm_client=client,
            run_logger=logger,
        ).run(_agent_input(request_id="req-fake"))

        self.assertEqual(output.provider, "fake")
        self.assertEqual(output.cost_usd, 0)
        self.assertEqual(output.message, client.response_text)
        self.assertEqual(logger.records[0].provider, "fake")
        self.assertEqual(logger.records[0].cost_usd, 0)


if __name__ == "__main__":
    unittest.main()

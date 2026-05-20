"""Agent memory context behavior tests."""

from __future__ import annotations

from lemon_ai_agent.adapters import AgentInput, DailyHealthAgentAppAdapter


def test_repeated_memory_pattern_prioritizes_matching_recommendation() -> None:
    """Verify injected memory can raise repeated nutrient patterns in coaching."""
    request = AgentInput(
        request_id="memory-context-test",
        user_id="local-dev-user",
        context={
            "profile": {"age": 42, "gender": "male"},
            "agent_memory": {
                "summaries": [
                    {
                        "memory_type": "daily_coaching",
                        "summary_json": {
                            "repeated_nutrient_patterns": {
                                "protein": 3,
                                "sodium": 1,
                            }
                        },
                    }
                ]
            },
        },
        payload={
            "date": "2026-05-19",
            "foods": [
                {
                    "name": "light lunch",
                    "meal_type": "lunch",
                    "nutrients": [
                        {"name": "protein", "amount": 20, "unit": "g"},
                        {"name": "sodium", "amount": 1800, "unit": "mg"},
                    ],
                }
            ],
            "sources": [{"source_type": "manual", "user_confirmed": True}],
            "reference_ranges": [
                {"nutrient": "protein", "target": 60, "unit": "g"},
                {"nutrient": "sodium", "target": 2000, "unit": "mg", "upper_limit": 2300},
            ],
        },
    )

    output = DailyHealthAgentAppAdapter().run(request)

    assert "agent_memory" in output.used_tools
    assert output.recommendations[0].title == "Add protein from food first"
    assert "appeared 3 times" in output.recommendations[0].rationale


def test_memory_pattern_accepts_canonicalized_nutrient_key() -> None:
    """Verify memory keys such as vitamin_d still match normalized findings."""
    request = AgentInput(
        request_id="memory-canonical-key-test",
        user_id="local-dev-user",
        context={
            "profile": {"age": 42, "gender": "male"},
            "agent_memory": {
                "summaries": [
                    {
                        "memory_type": "daily_coaching",
                        "summary_json": {
                            "repeated_nutrient_patterns": {
                                "vitamin_d": "2",
                            }
                        },
                    }
                ]
            },
        },
        payload={
            "date": "2026-05-19",
            "foods": [
                {
                    "name": "light breakfast",
                    "meal_type": "breakfast",
                    "nutrients": [
                        {"name": "Vitamin D", "amount": 2, "unit": "mcg"},
                    ],
                }
            ],
            "sources": [{"source_type": "manual", "user_confirmed": True}],
            "reference_ranges": [
                {"nutrient": "vitamin d", "target": 15, "unit": "mcg"},
            ],
        },
    )

    output = DailyHealthAgentAppAdapter().run(request)

    vitamin_d = next(
        item
        for item in output.recommendations
        if item.title == "Add vitamin d from food first"
    )
    assert "appeared 2 times" in vitamin_d.rationale
    assert vitamin_d.priority == 9

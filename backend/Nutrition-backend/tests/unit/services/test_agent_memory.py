"""Agent memory service tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from lemon_ai_agent.adapters import AgentFinding, AgentInput, AgentOutput
from src.config import Settings
from src.models.db.analysis_result import AnalysisResult
from src.models.db.supplement import UserSupplement, UserSupplementIngredient
from src.security.auth import AuthenticatedUser
from src.services.agent_memory import (
    DAILY_COACHING_MEMORY_TYPE,
    NUTRITION_ANALYSIS_MEMORY_TYPE,
    SUPPLEMENT_MEMORY_TYPE,
    record_agent_run,
    upsert_daily_coaching_memory,
    upsert_nutrition_analysis_memory,
    upsert_supplement_memory,
)


class _FakeSession:
    """Minimal async session for Agent memory unit tests."""

    def __init__(self, scalar_results: list[object | None] | None = None) -> None:
        self.scalar_results = list(scalar_results or [])
        self.added: list[object] = []
        self.committed = False

    async def scalar(self, _statement: object) -> object | None:
        return self.scalar_results.pop(0) if self.scalar_results else None

    def add(self, record: object) -> None:
        self.added.append(record)

    async def commit(self) -> None:
        self.committed = True


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="memory-user",
        issuer="https://auth.example.com/",
        claims={"sub": "memory-user"},
    )


def _settings() -> Settings:
    return Settings(_env_file=None)


def _agent_output() -> AgentOutput:
    return AgentOutput(
        request_id="memory-test",
        user_id="memory-user",
        agent_name="daily_health_agent",
        status="completed",
        approval_status="confirmed",
        requires_user_approval=False,
        message="ok",
        findings=[
            AgentFinding(
                nutrient="Vitamin-D",
                total_amount=400,
                unit="IU",
                ratio_to_target=0.5,
                level="low",
                message="Vitamin D intake is low.",
            )
        ],
    )


def _preview_output() -> AgentOutput:
    return AgentOutput(
        request_id="preview-test",
        user_id="memory-user",
        agent_name="daily_health_agent",
        status="preview",
        approval_status="requires_confirmation",
        requires_user_approval=True,
        message="Please confirm OCR results.",
        findings=[],
        recommendations=[],
        actions=[],
    )


def test_daily_coaching_memory_uses_canonical_nutrient_schema() -> None:
    """Verify daily memory stores canonical nutrient keys and sanitized findings."""
    session = _FakeSession()
    request = AgentInput(
        request_id="memory-test",
        user_id="memory-user",
        payload={
            "date": "2026-05-19",
            "raw_ocr_text": "should not be stored",
        },
        context={
            "profile": {
                "chronic_conditions": ["hypertension"],
                "raw_llm_response": "should not be stored",
            }
        },
    )

    memory = asyncio.run(
        upsert_daily_coaching_memory(
            session, _user(), _settings(), request, _agent_output()
        )
    )

    assert memory is not None
    assert memory.memory_type == DAILY_COACHING_MEMORY_TYPE
    assert memory.summary_json["schema_version"] == "agent-memory-summary-v1"
    assert memory.summary_json["repeated_nutrient_patterns"] == {"vitamin d": 1}
    assert memory.summary_json["recent_findings"] == [
        {
            "date": "2026-05-19",
            "nutrient": "vitamin d",
            "level": "low",
            "total_amount": 10.0,
            "unit": "mcg",
        }
    ]
    assert "raw_ocr_text" not in str(memory.summary_json)
    assert "raw_llm_response" not in str(memory.summary_json)
    assert session.committed


def test_preview_daily_coaching_does_not_write_memory_or_run_log() -> None:
    """Verify preview-only OCR output is not persisted to memory or run logs."""
    session = _FakeSession()
    request = AgentInput(
        request_id="preview-test",
        user_id="memory-user",
        payload={"sources": [{"source_type": "food_ocr", "user_confirmed": False}]},
    )
    output = _preview_output()

    memory = asyncio.run(
        upsert_daily_coaching_memory(session, _user(), _settings(), request, output)
    )
    run = asyncio.run(record_agent_run(session, _user(), _settings(), output))

    assert memory is None
    assert run is None
    assert session.added == []
    assert session.committed is False


def test_nutrition_analysis_memory_canonicalizes_priority_items() -> None:
    """Verify nested nutrition analysis priority items use canonical nutrient keys."""
    session = _FakeSession()
    record = AnalysisResult(
        owner_subject="issuer::memory-user",
        analysis_type="nutrition_analysis",
        algorithm_version="test",
        input_snapshot={},
        result_snapshot={
            "priority": [
                {"nutrient_name": "Vitamin-D", "status": "deficient"},
                {"nutrient": "sodium", "level": "high"},
            ],
            "raw_ocr_text": "should not be stored",
        },
    )
    record.created_at = datetime(2026, 5, 19, tzinfo=UTC)

    memory = asyncio.run(
        upsert_nutrition_analysis_memory(session, _user(), _settings(), record)
    )

    assert memory is not None
    assert memory.memory_type == NUTRITION_ANALYSIS_MEMORY_TYPE
    assert memory.summary_json["schema_version"] == "agent-memory-summary-v1"
    assert memory.summary_json["repeated_nutrient_patterns"] == {
        "sodium": 1,
        "vitamin d": 1,
    }
    assert "raw_ocr_text" not in str(memory.summary_json)


def test_supplement_memory_does_not_drive_food_first_patterns() -> None:
    """Verify supplement memory stays separate from food-first nutrient patterns."""
    session = _FakeSession()
    supplement = UserSupplement(
        owner_subject="issuer::memory-user",
        display_name="Vitamin D capsule",
        user_confirmed_at=datetime(2026, 5, 19, tzinfo=UTC),
        serving_snapshot={},
        intake_schedule={},
    )
    ingredient = UserSupplementIngredient(
        display_name="Vitamin-D",
        nutrient_code="vitamin_d",
        amount=Decimal("400"),
        unit="IU",
        confidence=Decimal("1"),
        source="user_confirmed",
        sort_order=0,
    )

    memory = asyncio.run(
        upsert_supplement_memory(session, _user(), _settings(), supplement, [ingredient])
    )

    assert memory is not None
    assert memory.memory_type == SUPPLEMENT_MEMORY_TYPE
    assert "repeated_nutrient_patterns" not in memory.summary_json
    assert "recommendations" not in memory.summary_json
    assert memory.summary_json["supplement_ingredients"]["vitamin d"] == {
        "count": 1,
        "nutrient_code": "vitamin_d",
        "unit": "mcg",
        "amount_total": 10.0,
    }

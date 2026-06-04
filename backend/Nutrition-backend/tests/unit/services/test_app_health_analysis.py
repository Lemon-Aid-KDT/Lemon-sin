"""App-context health analysis service tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Self, cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.db.analysis_result import AnalysisResult
from src.models.schemas.analysis_result import AnalysisType
from src.security.auth import AuthenticatedUser
from src.services.app_health_analysis import (
    APP_HEALTH_ANALYSIS_ALGORITHM_VERSION,
    build_analysis_run_confirmation,
    build_health_analysis_snapshot,
    build_today_analysis_snapshot,
    detect_analysis_run_intent,
    store_app_health_analysis_result,
)


class _TransactionContext:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None


class _FakeWriteSession:
    def __init__(self) -> None:
        self.added: AnalysisResult | None = None

    def begin(self) -> _TransactionContext:
        return _TransactionContext()

    def add(self, record: object) -> None:
        self.added = cast(AnalysisResult, record)

    async def refresh(self, record: object) -> None:
        analysis_result = cast(AnalysisResult, record)
        analysis_result.id = uuid4()
        analysis_result.created_at = datetime.now(UTC)
        analysis_result.updated_at = datetime.now(UTC)


async def _fake_session() -> AsyncIterator[object]:
    yield object()


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user_123",
        issuer="https://auth.example.com/",
        claims={"sub": "user_123", "iss": "https://auth.example.com/"},
    )


def _snapshot(
    *,
    foods: list[dict[str, object]] | None = None,
    supplements: list[dict[str, object]] | None = None,
    checked_today: list[dict[str, object]] | None = None,
    checklist_items: list[str] | None = None,
    chat_signals: list[dict[str, object]] | None = None,
    stale_reasons: list[str] | None = None,
    tracking_days: int | None = None,
) -> dict[str, object]:
    return {
        "user_profile_summary": {
            "health_axes": ["sodium", "blood_pressure"],
            "risk_flags": ["hypertension_context"],
        },
        "active_supplement_snapshot": {
            "registered_supplements": supplements or [],
            "checked_today": checked_today or [],
        },
        "recent_food_and_checklist_snapshot": {
            "recent_food_records": foods or [],
            "checklist_items": checklist_items or [],
            "stale_reasons": stale_reasons or [],
            **({"tracking_days": tracking_days} if tracking_days is not None else {}),
        },
        "chat_derived_health_signals": {"signals": chat_signals or []},
    }


def test_today_analysis_pending_without_minimum_food_record_and_no_score() -> None:
    snapshot = build_today_analysis_snapshot(_snapshot())

    assert snapshot["schema_version"] == "today-analysis-snapshot-v1"
    assert snapshot["status"] == "analysis_pending"
    assert snapshot["score"] is None
    assert snapshot["score_name"] == "오늘 현재 분석 점수"
    assert snapshot["score_description"] == "기록 기반 생활관리 점수"
    assert snapshot["analysis_scope"] == "current_records_so_far"
    assert snapshot["missing_records"] == ["food_records"]
    assert snapshot["ctas"] == ["complete_missing_record"]


def test_today_analysis_ready_with_food_only_when_no_registered_supplements() -> None:
    snapshot = build_today_analysis_snapshot(
        _snapshot(
            foods=[
                {
                    "display_items": ["ramen"],
                    "rough_nutrient_axes": ["sodium_high", "carbohydrate_high"],
                    "estimated_tags": ["sodium_high"],
                }
            ],
            checklist_items=["drink water"],
        )
    )

    assert snapshot["status"] == "ready_for_analysis"
    assert snapshot["score"] == 72
    assert snapshot["minimum_conditions"]["food_records"] is True
    assert snapshot["minimum_conditions"]["supplement_check_required"] is False
    assert snapshot["priority_adjustments"] == ["sodium_high", "carbohydrate_high"]
    assert snapshot["ctas"] == ["run_or_refresh_analysis", "ask_about_this_result"]


def test_today_analysis_requires_supplement_check_when_registered_supplements_exist() -> None:
    snapshot = build_today_analysis_snapshot(
        _snapshot(
            foods=[{"display_items": ["rice"], "rough_nutrient_axes": ["carbohydrate_high"]}],
            supplements=[{"display_name": "Vitamin D"}],
            checked_today=[],
        )
    )

    assert snapshot["status"] == "analysis_pending"
    assert snapshot["score"] is None
    assert snapshot["missing_records"] == ["supplement_check"]
    assert snapshot["minimum_conditions"]["supplement_check_required"] is True


def test_today_analysis_marks_stale_when_records_changed_after_snapshot() -> None:
    snapshot = build_today_analysis_snapshot(
        _snapshot(
            foods=[{"display_items": ["rice"], "rough_nutrient_axes": ["carbohydrate_high"]}],
            stale_reasons=["food_record_changed"],
        )
    )

    assert snapshot["stale"] is True
    assert snapshot["stale_reasons"] == ["food_record_changed"]
    assert snapshot["ctas"][0] == "run_or_refresh_analysis"


def test_health_analysis_snapshot_maturity_coverage_strengths_and_chat_signal_stages() -> None:
    snapshot = build_health_analysis_snapshot(
        _snapshot(
            foods=[{"display_items": ["ramen"], "rough_nutrient_axes": ["sodium_high"]}],
            supplements=[{"display_name": "Vitamin D"}],
            checklist_items=["drink water"],
            chat_signals=[
                {"name": "late_night_snack", "stage": "user_reported_signal"},
                {"name": "untrusted_free_text", "stage": "raw_transcript"},
            ],
        )
    )

    assert snapshot["schema_version"] == "health-analysis-snapshot-v1"
    assert snapshot["readiness_level"] == "level_2_recent_pattern"
    assert snapshot["coverage"] == {
        "food": True,
        "supplement": True,
        "checklist": True,
        "chat_signals": True,
    }
    assert snapshot["strengths"][:2] == ["food_records_available", "supplements_confirmed"]
    assert snapshot["chat_signal_stages"] == ["user_reported_signal"]
    assert snapshot["priority_adjustments"] == ["sodium_high"]


def test_health_analysis_readiness_levels_include_personal_baseline_and_long_term() -> None:
    assert build_health_analysis_snapshot(_snapshot())["readiness_level"] == "level_0_preparing"
    assert build_health_analysis_snapshot(
        _snapshot(foods=[{"display_items": ["rice"], "rough_nutrient_axes": []}])
    )["readiness_level"] == "level_1_initial"
    assert build_health_analysis_snapshot(
        _snapshot(
            foods=[{"display_items": ["rice"], "rough_nutrient_axes": []}],
            supplements=[{"display_name": "Vitamin D"}],
            tracking_days=14,
        )
    )["readiness_level"] == "level_3_personal_baseline"
    assert build_health_analysis_snapshot(
        _snapshot(
            foods=[{"display_items": ["rice"], "rough_nutrient_axes": []}],
            supplements=[{"display_name": "Vitamin D"}],
            checklist_items=["walk"],
            tracking_days=90,
        )
    )["readiness_level"] == "level_4_long_term"


def test_analysis_run_intent_requires_confirmation_and_limits_ctas() -> None:
    assert detect_analysis_run_intent("Run today's analysis") == "today_analysis"
    assert detect_analysis_run_intent("Can you run my health analysis?") == "health_analysis"

    confirmation = build_analysis_run_confirmation(
        "today_analysis",
        build_today_analysis_snapshot(
            _snapshot(foods=[{"display_items": ["rice"], "rough_nutrient_axes": []}])
        ),
    )

    assert confirmation["requires_user_confirmation"] is True
    assert confirmation["will_persist"] is False
    assert confirmation["ctas"] == ["run_or_refresh_analysis", "ask_about_this_result"]


@pytest.mark.asyncio
async def test_store_app_health_analysis_result_persists_snapshot_after_confirmation() -> None:
    fake_session = _FakeWriteSession()
    today_snapshot = build_today_analysis_snapshot(
        _snapshot(foods=[{"display_items": ["rice"], "rough_nutrient_axes": []}])
    )

    record = await store_app_health_analysis_result(
        cast(AsyncSession, fake_session),
        _user(),
        analysis_kind="today_analysis",
        input_snapshot={"context_sections": ["recent_food_and_checklist_snapshot"]},
        result_snapshot=today_snapshot,
        user_confirmed=True,
    )

    assert record is fake_session.added
    assert record.analysis_type == AnalysisType.NUTRITION_ANALYSIS.value
    assert record.algorithm_version == APP_HEALTH_ANALYSIS_ALGORITHM_VERSION
    assert record.result_snapshot["analysis_kind"] == "today_analysis"
    assert record.result_snapshot["snapshot"]["score_name"] == "오늘 현재 분석 점수"
    assert record.input_snapshot["user_confirmed"] is True

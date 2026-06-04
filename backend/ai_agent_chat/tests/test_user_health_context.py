"""User health context snapshot contract tests."""

from __future__ import annotations

from lemon_ai_agent.user_health_context import (
    ContextResolver,
    UserHealthContextSnapshot,
)


def test_user_health_context_snapshot_keeps_only_safe_structured_fields() -> None:
    """Snapshots must not carry raw prompts, OCR text, transcripts, or LLM output."""
    snapshot = UserHealthContextSnapshot.from_mapping(
        {
            "user_profile_summary": {
                "health_axes": ["sodium", "blood_pressure"],
                "raw_prompt": "나는 고혈압인데 어제 뭘 먹었는지 전부 말해줘",
            },
            "today_analysis_snapshot": {
                "status": "analysis_pending",
                "raw_llm_output": "hidden chain",
            },
            "health_analysis_snapshot": {"readiness_level": "level_1_initial"},
            "active_supplement_snapshot": {
                "registered_supplements": [
                    {
                        "display_name": "비타민 D",
                        "nutrient_codes": ["vitamin_d"],
                        "raw_ocr_text": "제품 라벨 원문",
                    }
                ]
            },
            "recent_food_and_checklist_snapshot": {
                "recent_food_records": [{"display_items": ["라면"], "meal_type": "lunch"}],
                "raw_chat_transcript": [{"role": "user", "content": "raw"}],
            },
            "chat_derived_health_signals": {
                "signals": [{"name": "late_night_snack", "confidence": "user_reported_signal"}]
            },
            "visible_analysis_context": {
                "last_visible_summary": "오늘 분석은 아직 대기 상태입니다.",
                "messages": [{"role": "assistant", "content": "raw"}],
            },
            "raw_ocr": "top-level raw",
            "raw_prompt": "top-level raw",
        }
    )

    safe_context = snapshot.to_safe_context()

    assert safe_context["user_profile_summary"]["health_axes"] == ["sodium", "blood_pressure"]
    assert safe_context["active_supplement_snapshot"]["registered_supplements"][0][
        "nutrient_codes"
    ] == ["vitamin_d"]
    assert "raw_prompt" not in str(safe_context)
    assert "raw_ocr_text" not in str(safe_context)
    assert "raw_chat_transcript" not in str(safe_context)
    assert "raw_llm_output" not in str(safe_context)
    assert "messages" not in str(safe_context)


def test_context_resolver_uses_snapshot_for_general_health_question() -> None:
    snapshot = UserHealthContextSnapshot.from_mapping(
        {
            "user_profile_summary": {
                "health_axes": ["sodium", "blood_pressure"],
                "risk_flags": ["hypertension_context"],
            },
            "recent_food_and_checklist_snapshot": {
                "recent_food_records": [{"display_items": ["라면"], "meal_type": "lunch"}]
            },
        }
    )

    result = ContextResolver().resolve(
        "오늘 저녁은 나트륨을 줄이려면 어떻게 먹는 게 좋아?",
        snapshot,
    )

    assert result.status == "sufficient"
    assert result.required_records == ()
    assert result.safe_context["user_profile_summary"]["health_axes"] == [
        "sodium",
        "blood_pressure",
    ]


def test_context_resolver_requests_targeted_food_lookup_for_specific_meal_query() -> None:
    snapshot = UserHealthContextSnapshot.from_mapping(
        {
            "user_profile_summary": {"health_axes": ["sodium"]},
            "recent_food_and_checklist_snapshot": {"recent_food_records": []},
        }
    )

    result = ContextResolver().resolve("어제 점심에 내가 뭐 먹었지?", snapshot)

    assert result.status == "needs_structured_lookup"
    assert result.required_records == ("food_records",)
    assert result.lookup_filters == {"date_scope": "specific_or_recent", "record_type": "food"}
    assert "recent_food_and_checklist_snapshot" not in result.safe_context


def test_context_resolver_treats_today_meal_plan_as_guidance_not_record_lookup() -> None:
    snapshot = UserHealthContextSnapshot.from_mapping(
        {
            "user_profile_summary": {
                "health_axes": ["blood_glucose"],
                "risk_flags": ["diabetes_context"],
            },
            "recent_food_and_checklist_snapshot": {"recent_food_records": []},
        }
    )

    result = ContextResolver().resolve(
        "당뇨 수치가 요즘 계속 오르네. 오늘 점심, 저녁 식단을 짜줘.",
        snapshot,
    )

    assert result.status == "sufficient"
    assert result.required_records == ()
    assert result.reason == "snapshot_sufficient"


def test_context_resolver_requires_more_info_when_snapshot_is_empty() -> None:
    result = ContextResolver().resolve(
        "내 건강 상태에 맞게 오늘 뭘 하면 좋아?",
        UserHealthContextSnapshot.empty(),
    )

    assert result.status == "needs_more_info"
    assert result.required_records == ()
    assert result.safe_context == {}

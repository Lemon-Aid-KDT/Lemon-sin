"""User health context snapshot service tests."""

from __future__ import annotations

from src.services.user_health_context_snapshot import build_user_health_context_snapshot


def test_build_user_health_context_snapshot_sanitizes_route_context() -> None:
    snapshot = build_user_health_context_snapshot(
        request_context={
            "profile": {
                "goals": ["meal_management"],
                "chronic_conditions": ["hypertension"],
                "raw_prompt": "raw user question",
            },
            "today_analysis_snapshot": {
                "status": "analysis_pending",
                "raw_llm_output": "hidden",
            },
            "latest_confirmed_entries": {
                "foods": [{"display_items": ["라면"], "meal_type": "lunch"}],
                "raw_ocr_text": "label text",
            },
            "visible_analysis_context": {
                "last_visible_summary": "오늘 분석 대기",
                "messages": [{"role": "assistant", "content": "raw"}],
            },
        },
        memory_context={
            "summaries": [
                {
                    "memory_type": "daily_coaching",
                    "source_counters": {"daily_coaching": 2},
                    "summary_json": {"repeated_nutrient_patterns": {"sodium": 2}},
                }
            ]
        },
        medication_context={
            "medications": ["amlodipine"],
            "medication_details": [{"display_name": "amlodipine"}],
        },
    )

    safe_context = snapshot.to_safe_context()

    assert safe_context["user_profile_summary"]["chronic_conditions"] == ["hypertension"]
    assert safe_context["user_profile_summary"]["medications"] == ["amlodipine"]
    assert safe_context["health_analysis_snapshot"]["memory_types"] == ["daily_coaching"]
    assert safe_context["recent_food_and_checklist_snapshot"]["recent_food_records"] == [
        {"display_items": ["라면"], "meal_type": "lunch"}
    ]
    assert "raw_prompt" not in str(safe_context)
    assert "raw_llm_output" not in str(safe_context)
    assert "raw_ocr_text" not in str(safe_context)
    assert "messages" not in str(safe_context)


def test_build_user_health_context_snapshot_prefers_db_food_record_snapshots() -> None:
    snapshot = build_user_health_context_snapshot(
        request_context={
            "latest_confirmed_entries": {
                "foods": [{"display_items": ["client preview food"], "meal_type": "snack"}],
                "raw_ocr_text": "raw preview OCR",
            },
        },
        memory_context={},
        medication_context={},
        food_record_context=[
            {
                "food_record_id": "record-1",
                "recorded_date": "2026-05-31",
                "meal_type": "lunch",
                "display_items": ["ramen"],
                "estimated_tags": ["sodium_high"],
                "rough_nutrient_axes": ["sodium_high"],
                "user_confirmed": True,
                "source": "manual",
                "raw_prompt": "hidden",
            }
        ],
    )

    safe_context = snapshot.to_safe_context()

    assert safe_context["recent_food_and_checklist_snapshot"]["recent_food_records"] == [
        {
            "food_record_id": "record-1",
            "recorded_date": "2026-05-31",
            "meal_type": "lunch",
            "display_items": ["ramen"],
            "estimated_tags": ["sodium_high"],
            "rough_nutrient_axes": ["sodium_high"],
            "user_confirmed": True,
            "source": "manual",
        }
    ]
    assert "client preview food" not in str(safe_context)
    assert "raw_ocr_text" not in str(safe_context)
    assert "raw_prompt" not in str(safe_context)


def test_build_user_health_context_snapshot_excludes_preview_candidate_context() -> None:
    snapshot = build_user_health_context_snapshot(
        request_context={
            "profile": {
                "goals": ["meal_management"],
                "medications": ["client_preview_med"],
            },
            "latest_confirmed_entries": {
                "foods": [
                    {
                        "display_items": ["client preview food"],
                        "meal_type": "snack",
                        "status": "preview",
                    }
                ],
            },
            "health_analysis_snapshot": {
                "result": "learning analysis candidate",
                "status": "candidate",
                "provider_payload": {"raw": "hidden"},
            },
        },
        memory_context={},
        medication_context={
            "medications": ["amlodipine", "preview medication"],
            "medication_details": [
                {
                    "display_name": "amlodipine",
                    "normalized_name": "amlodipine",
                    "medication_class": "calcium_channel_blocker",
                    "confirmation_status": "user_confirmed",
                    "is_active": True,
                },
                {
                    "display_name": "preview medication",
                    "normalized_name": "preview medication",
                    "confirmation_status": "requires_confirmation",
                    "is_active": True,
                    "raw_ocr_text": "hidden medication label",
                },
                {
                    "display_name": "inactive medication",
                    "confirmation_status": "user_confirmed",
                    "is_active": False,
                },
            ],
        },
        food_record_context=[
            {
                "food_record_id": "record-confirmed",
                "recorded_date": "2026-06-05",
                "meal_type": "lunch",
                "display_items": ["confirmed rice bowl"],
                "rough_nutrient_axes": ["carbohydrate_high"],
                "user_confirmed": True,
                "source": "manual",
            },
            {
                "food_record_id": "record-preview",
                "recorded_date": "2026-06-05",
                "meal_type": "dinner",
                "display_items": ["ocr preview noodles"],
                "rough_nutrient_axes": ["sodium_high"],
                "user_confirmed": False,
                "source": "ocr_preview",
                "raw_ocr_text": "hidden OCR",
            },
            {
                "food_record_id": "record-candidate",
                "recorded_date": "2026-06-05",
                "meal_type": "snack",
                "display_items": ["yolo candidate snack"],
                "status": "candidate",
                "needs_user_review": True,
                "source": "yolo_candidate",
            },
        ],
        active_supplement_context={
            "registered_supplements": [
                {
                    "supplement_id": "supplement-confirmed",
                    "display_name": "Vitamin D",
                    "user_confirmed": True,
                    "is_active": True,
                    "ingredients": [
                        {
                            "display_name": "Vitamin D",
                            "nutrient_code": "vitamin_d_ug",
                            "amount": 25,
                            "unit": "ug",
                            "provider_payload": {"raw": "hidden"},
                        },
                        {
                            "display_name": "Proprietary blend",
                            "nutrient_code": None,
                            "amount": 1,
                            "unit": "capsule",
                        },
                    ],
                },
                {
                    "supplement_id": "supplement-preview",
                    "display_name": "OCR preview supplement",
                    "status": "requires_confirmation",
                    "user_confirmed": False,
                    "is_active": True,
                    "raw_llm_output": "hidden preview",
                },
                {
                    "supplement_id": "supplement-inactive",
                    "display_name": "Inactive confirmed supplement",
                    "user_confirmed": True,
                    "is_active": False,
                },
            ],
            "checked_today": [
                {"supplement_id": "supplement-confirmed"},
                {"supplement_id": "supplement-preview", "status": "preview"},
            ],
            "policy": {"unconfirmed_preview_excluded": True},
        },
    )

    safe_context = snapshot.to_safe_context()
    safe_text = str(safe_context)

    assert safe_context["user_profile_summary"]["medications"] == ["amlodipine"]
    assert safe_context["user_profile_summary"]["medication_details"] == [
        {
            "display_name": "amlodipine",
            "normalized_name": "amlodipine",
            "medication_class": "calcium_channel_blocker",
            "confirmation_status": "user_confirmed",
            "is_active": True,
        }
    ]
    assert safe_context["recent_food_and_checklist_snapshot"]["recent_food_records"] == [
        {
            "food_record_id": "record-confirmed",
            "recorded_date": "2026-06-05",
            "meal_type": "lunch",
            "display_items": ["confirmed rice bowl"],
            "rough_nutrient_axes": ["carbohydrate_high"],
            "user_confirmed": True,
            "source": "manual",
        }
    ]
    supplements = safe_context["active_supplement_snapshot"]["registered_supplements"]
    assert [item["supplement_id"] for item in supplements] == ["supplement-confirmed"]
    assert supplements[0]["ingredients"] == [
        {
            "display_name": "Vitamin D",
            "nutrient_code": "vitamin_d_ug",
            "amount": 25,
            "unit": "ug",
            "analysis_use": "standard_nutrient",
        },
        {
            "display_name": "Proprietary blend",
            "nutrient_code": None,
            "amount": 1,
            "unit": "capsule",
            "analysis_use": "label_only",
        },
    ]
    assert safe_context["active_supplement_snapshot"]["checked_today"] == [
        {"supplement_id": "supplement-confirmed"}
    ]
    assert "client_preview_med" not in safe_text
    assert "client preview food" not in safe_text
    assert "ocr preview noodles" not in safe_text
    assert "yolo candidate snack" not in safe_text
    assert "OCR preview supplement" not in safe_text
    assert "Inactive confirmed supplement" not in safe_text
    assert "learning analysis candidate" not in safe_text
    assert "provider_payload" not in safe_text
    assert "raw_llm_output" not in safe_text
    assert "raw_ocr_text" not in safe_text


def test_visible_analysis_context_marks_stale_after_supplement_check_change() -> None:
    snapshot = build_user_health_context_snapshot(
        request_context={
            "visible_analysis_context": {
                "analysis_kind": "today_analysis",
                "checked_supplement_ids": ["supplement-1"],
            }
        },
        memory_context={},
        medication_context={},
        active_supplement_context={
            "registered_supplements": [],
            "checked_today": [
                {"supplement_id": "supplement-1", "display_name": "Vitamin D"},
                {"supplement_id": "supplement-2", "display_name": "Magnesium"},
            ],
        },
    )

    visible = snapshot.to_safe_context()["visible_analysis_context"]

    assert visible["stale"] is True
    assert visible["stale_reasons"] == [
        "supplement_check_changed_after_visible_analysis"
    ]
    assert visible["current_checked_supplement_ids"] == ["supplement-1", "supplement-2"]


def test_visible_analysis_context_marks_stale_after_checklist_change() -> None:
    snapshot = build_user_health_context_snapshot(
        request_context={
            "recent_food_and_checklist_snapshot": {
                "checklist_items": [
                    {"checklist_item_id": "checklist-1", "label": "drink water"},
                    {"checklist_item_id": "checklist-2", "label": "walk"},
                ]
            },
            "visible_analysis_context": {
                "analysis_kind": "health_analysis",
                "checklist_item_ids": ["checklist-1"],
            },
        },
        memory_context={},
        medication_context={},
    )

    visible = snapshot.to_safe_context()["visible_analysis_context"]

    assert visible["stale"] is True
    assert visible["stale_reasons"] == ["checklist_changed_after_visible_analysis"]
    assert visible["current_checklist_item_ids"] == ["checklist-1", "checklist-2"]

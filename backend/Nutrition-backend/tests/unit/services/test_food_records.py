"""Food record service and tagger tests."""

from __future__ import annotations

from src.models.schemas.food_record import FoodRecordCreate
from src.services.food_records import build_food_record_snapshot, estimate_food_tags


def test_estimate_food_tags_uses_korean_food_name_rules() -> None:
    ramen = estimate_food_tags(["라면"])
    rice = estimate_food_tags(["흰쌀밥"])
    chicken = estimate_food_tags(["닭가슴살"])

    assert ramen.estimated_tags == ["sodium_high", "refined_carb", "soup_or_stew"]
    assert ramen.rough_nutrient_axes == ["sodium_high", "carbohydrate_high"]
    assert rice.estimated_tags == ["carbohydrate_high"]
    assert rice.rough_nutrient_axes == ["carbohydrate_high"]
    assert chicken.estimated_tags == ["protein_food"]
    assert chicken.rough_nutrient_axes == ["protein_food"]


def test_food_record_snapshot_v1_keeps_future_food_db_fields_nullable() -> None:
    request = FoodRecordCreate(
        recorded_date="2026-05-31",
        meal_type="lunch",
        display_items=["라면"],
        amount_text="1그릇",
        source="manual",
    )

    snapshot = build_food_record_snapshot(request)

    assert snapshot["food_record_id"] is None
    assert snapshot["recorded_date"] == "2026-05-31"
    assert snapshot["meal_type"] == "lunch"
    assert snapshot["display_items"] == ["라면"]
    assert snapshot["estimated_tags"] == ["sodium_high", "refined_carb", "soup_or_stew"]
    assert snapshot["rough_nutrient_axes"] == ["sodium_high", "carbohydrate_high"]
    assert snapshot["food_db_match_id"] is None
    assert snapshot["match_confidence"] is None
    assert snapshot["nutrient_estimates"] is None

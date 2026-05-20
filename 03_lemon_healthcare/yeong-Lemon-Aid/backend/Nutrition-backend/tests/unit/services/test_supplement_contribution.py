"""Supplement contribution service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.models.db.supplement import UserSupplement, UserSupplementIngredient
from src.models.schemas.user import UserProfile
from src.services.supplement_contribution import (
    SupplementContributionSource,
    calculate_supplement_contributions,
)


def _supplement(*, daily_servings: float = 2) -> UserSupplement:
    """Return a confirmed supplement row fixture.

    Args:
        daily_servings: Daily serving count.

    Returns:
        User supplement ORM row.
    """
    now = datetime.now(UTC)
    return UserSupplement(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        display_name="Vitamin C",
        manufacturer="Sample Nutrition",
        serving_snapshot={"amount": 1, "unit": "tablet", "daily_servings": daily_servings},
        intake_schedule={"frequency": "daily"},
        user_confirmed_at=now,
        created_at=now,
        updated_at=now,
    )


def _ingredient(
    supplement: UserSupplement,
    *,
    amount: Decimal | None = Decimal("250"),
    unit: str | None = "mg",
    nutrient_code: str | None = "vitamin_c_mg",
    sort_order: int = 0,
) -> UserSupplementIngredient:
    """Return a confirmed supplement ingredient row fixture.

    Args:
        supplement: Parent supplement.
        amount: Ingredient amount per serving.
        unit: Ingredient unit.
        nutrient_code: Internal nutrient code.
        sort_order: Display sort order.

    Returns:
        Ingredient ORM row.
    """
    now = datetime.now(UTC)
    return UserSupplementIngredient(
        id=uuid4(),
        user_supplement_id=supplement.id,
        display_name="Vitamin C",
        nutrient_code=nutrient_code,
        amount=amount,
        unit=unit,
        confidence=Decimal("1"),
        source="user_confirmed",
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )


def test_calculate_supplement_contributions_multiplies_by_daily_servings() -> None:
    """Verify amount per serving is multiplied by confirmed daily servings."""
    supplement = _supplement(daily_servings=2)
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)

    result = calculate_supplement_contributions(
        [SupplementContributionSource(supplement, (_ingredient(supplement),))],
        profile=profile,
    )

    aggregate = result.aggregates[0]
    assert aggregate.nutrient_code == "vitamin_c_mg"
    assert aggregate.total_daily_amount == 500
    assert aggregate.original_unit_totals == {"mg": 500}
    assert aggregate.contribution_count == 1
    assert result.warnings == ()


def test_calculate_supplement_contributions_sums_duplicate_nutrient_codes() -> None:
    """Verify duplicate nutrient rows are summed by nutrient code."""
    supplement = _supplement(daily_servings=1)
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)
    first = _ingredient(supplement, amount=Decimal("100"), sort_order=0)
    second = _ingredient(supplement, amount=Decimal("50"), sort_order=1)

    result = calculate_supplement_contributions(
        [SupplementContributionSource(supplement, (first, second))],
        profile=profile,
    )

    aggregate = result.aggregates[0]
    assert aggregate.total_daily_amount == 150
    assert aggregate.contribution_count == 2
    assert aggregate.supplement_ids == [supplement.id]


def test_calculate_supplement_contributions_marks_unknown_unit_for_review() -> None:
    """Verify unsupported units do not get silently converted."""
    supplement = _supplement(daily_servings=1)
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)

    result = calculate_supplement_contributions(
        [
            SupplementContributionSource(
                supplement,
                (_ingredient(supplement, unit="tablet"),),
            )
        ],
        profile=profile,
    )

    aggregate = result.aggregates[0]
    assert aggregate.total_daily_amount is None
    assert aggregate.warnings == ["unit_conversion_failed:tablet->mg"]


def test_calculate_supplement_contributions_skips_missing_required_fields() -> None:
    """Verify missing confirmed ingredient facts are not inferred."""
    supplement = _supplement(daily_servings=1)

    result = calculate_supplement_contributions(
        [
            SupplementContributionSource(
                supplement,
                (_ingredient(supplement, amount=None),),
            )
        ],
        profile=None,
    )

    assert result.aggregates == ()
    assert len(result.warnings) == 1
    assert result.warnings[0].startswith("ingredient_amount_missing:")

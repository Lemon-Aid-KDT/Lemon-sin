"""Personalized supplement nutrition risk service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.models.db.analysis_result import AnalysisResult
from src.models.schemas.analysis_result import AnalysisType
from src.models.schemas.nutrition import NutrientAnalysisResult, NutrientStatus
from src.models.schemas.supplement_recommendation import (
    SupplementContributionAggregate,
    SupplementImpactDataStatus,
    SupplementRecommendationActionLabel,
)
from src.models.schemas.user import UserProfile
from src.services.personalized_nutrition_risk import classify_personalized_supplement_risks


def _analysis_result(*results: NutrientAnalysisResult) -> AnalysisResult:
    """Return a nutrition analysis result fixture.

    Args:
        *results: Nutrient analysis rows.

    Returns:
        Analysis result ORM row.
    """
    now = datetime.now(UTC)
    return AnalysisResult(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        analysis_type=AnalysisType.NUTRITION_ANALYSIS.value,
        algorithm_version="nutrition-v1.0.0",
        kdris_source_manifest_version="2.0",
        input_snapshot={
            "profile": {
                "age": 30,
                "sex": "male",
                "height_cm": 170,
                "weight_kg": 70,
            }
        },
        result_snapshot={"results": [result.model_dump(mode="json") for result in results]},
        created_at=now,
        updated_at=now,
    )


def _nutrient_result(
    *,
    nutrient_code: str = "vitamin_c_mg",
    actual_amount: float = 30,
    status: NutrientStatus = NutrientStatus.DEFICIENT,
    reference_amount: float = 100,
    reference_unit: str = "mg",
    ul_amount: float | None = 2000,
) -> NutrientAnalysisResult:
    """Return a nutrient analysis fixture.

    Args:
        nutrient_code: Internal nutrient code.
        actual_amount: Actual amount in reference unit.
        status: Nutrient status.
        reference_amount: KDRI reference amount.
        reference_unit: KDRI reference unit.
        ul_amount: Upper intake amount.

    Returns:
        Nutrient analysis result.
    """
    return NutrientAnalysisResult(
        nutrient_code=nutrient_code,
        nutrient_name=nutrient_code,
        reference_amount=reference_amount,
        reference_type="RNI",
        source_id="kns_2025_kdris_publication",
        errata_version="f4",
        review_status="approved",
        reference_unit=reference_unit,
        actual_amount=actual_amount,
        ratio=actual_amount / reference_amount,
        ul_amount=ul_amount,
        status=status,
        priority=1 if status in (NutrientStatus.DEFICIENT, NutrientStatus.LOW) else 0,
        user_message="섭취량 확인이 필요합니다.",
    )


def _aggregate(
    *,
    nutrient_code: str = "vitamin_c_mg",
    total_daily_amount: float | None = 50,
    reference_unit: str | None = "mg",
    contribution_count: int = 1,
) -> SupplementContributionAggregate:
    """Return a supplement contribution aggregate fixture.

    Args:
        nutrient_code: Internal nutrient code.
        total_daily_amount: Supplement daily amount in reference unit.
        reference_unit: Reference unit.
        contribution_count: Number of ingredient contributions.

    Returns:
        Supplement contribution aggregate.
    """
    return SupplementContributionAggregate(
        nutrient_code=nutrient_code,
        nutrient_name=nutrient_code,
        reference_unit=reference_unit,
        total_daily_amount=total_daily_amount,
        original_unit_totals={reference_unit or "unknown": total_daily_amount or 0},
        contribution_count=contribution_count,
        supplement_ids=[uuid4() for _ in range(contribution_count)],
        warnings=[],
    )


def test_classify_personalized_risks_marks_deficiency_support_candidate() -> None:
    """Verify supplements overlapping low intake become support candidates."""
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)
    latest = _analysis_result(_nutrient_result())

    result = classify_personalized_supplement_risks(
        profile=profile,
        latest_nutrition_result=latest,
        contributions=(_aggregate(),),
    )

    assert result.data_status == SupplementImpactDataStatus.READY
    assert result.deficiency_support_candidates[0].nutrient_code == "vitamin_c_mg"
    assert result.deficiency_support_candidates[0].action_label == (
        SupplementRecommendationActionLabel.INSIGHT
    )
    assert result.excess_or_duplicate_risks == ()


def test_classify_personalized_risks_marks_duplicate_and_ul_risk() -> None:
    """Verify duplicate nutrients and UL excess are surfaced separately."""
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)
    latest = _analysis_result(
        _nutrient_result(
            nutrient_code="vitamin_a_ug",
            actual_amount=1000,
            status=NutrientStatus.ADEQUATE,
            reference_amount=700,
            reference_unit="ug",
            ul_amount=3000,
        )
    )

    result = classify_personalized_supplement_risks(
        profile=profile,
        latest_nutrition_result=latest,
        contributions=(
            _aggregate(
                nutrient_code="vitamin_a_ug",
                total_daily_amount=2500,
                reference_unit="ug",
                contribution_count=2,
            ),
        ),
    )

    reason_codes = {insight.reason_code for insight in result.excess_or_duplicate_risks}
    assert reason_codes == {"above_upper_intake_level", "duplicate_supplement_nutrient"}


def test_classify_personalized_risks_escalates_pregnancy_to_professional_discussion() -> None:
    """Verify pregnancy context does not produce casual supplement guidance."""
    profile = UserProfile(
        age=30,
        sex="female",
        height_cm=165,
        weight_kg=60,
        pregnancy_status="pregnant",
    )
    latest = _analysis_result(_nutrient_result())

    result = classify_personalized_supplement_risks(
        profile=profile,
        latest_nutrition_result=latest,
        contributions=(_aggregate(),),
    )

    assert result.deficiency_support_candidates[0].action_label == (
        SupplementRecommendationActionLabel.DISCUSS_WITH_PROFESSIONAL
    )


def test_classify_personalized_risks_is_partial_without_profile_or_latest_analysis() -> None:
    """Verify missing personalization inputs produce partial review state."""
    result = classify_personalized_supplement_risks(
        profile=None,
        latest_nutrition_result=None,
        contributions=(_aggregate(total_daily_amount=None, reference_unit=None),),
    )

    assert result.data_status == SupplementImpactDataStatus.PARTIAL
    assert "profile.age" in result.missing_profile_fields
    assert result.excess_or_duplicate_risks[0].action_label == (
        SupplementRecommendationActionLabel.REVIEW_NEEDED
    )

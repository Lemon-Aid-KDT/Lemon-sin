"""KDRIs 기준 섭취 상태 분석."""

from __future__ import annotations

from src.models.schemas.nutrition import (
    NutrientAnalysisResult,
    NutrientIntake,
    NutrientStatus,
    NutritionAnalysisResponse,
)
from src.models.schemas.user import UserProfile
from src.nutrition.chronic_priority import get_chronic_priority_match
from src.nutrition.kdris import get_kdris_dataset_context, lookup_kdris_reference
from src.nutrition.unit_converter import convert_amount

DEFICIENT_THRESHOLD = 0.35
LOW_THRESHOLD = 0.70
EXCESSIVE_THRESHOLD = 1.30
RATIO_DECIMALS = 2
AMOUNT_DECIMALS = 3
FORBIDDEN_TERMS = ("진단", "치료", "처방", "복용량 변경")
NUTRITION_ANALYSIS_ALGORITHM_VERSION = "nutrition-v1.0.0"


def _message_for_status(status: NutrientStatus) -> str:
    """섭취 상태에 맞는 안전 문구를 반환한다.

    Args:
        status: 영양소 섭취 상태.

    Returns:
        사용자 노출용 문구.
    """
    messages = {
        NutrientStatus.DEFICIENT: "부족 가능성이 높아 섭취량 확인이 필요합니다.",
        NutrientStatus.LOW: "섭취량이 낮을 가능성이 있어 우선 확인 대상입니다.",
        NutrientStatus.ADEQUATE: "현재 입력 기준으로 적정 범위에 가깝습니다.",
        NutrientStatus.EXCESSIVE: "섭취량이 기준보다 많아 조정 여부 확인이 필요합니다.",
        NutrientStatus.RISKY: "상한 섭취량을 초과할 수 있어 전문가 상담 권장 대상입니다.",
    }
    return messages[status]


def _classify_status(
    actual_amount: float,
    reference_amount: float,
    ul_amount: float | None,
) -> NutrientStatus:
    """실제 섭취량을 기준값과 비교해 상태를 분류한다.

    Args:
        actual_amount: 기준 단위로 환산된 실제 섭취량.
        reference_amount: 기준 섭취량.
        ul_amount: 상한 섭취량.

    Returns:
        섭취 상태.
    """
    ratio = actual_amount / reference_amount
    if ul_amount is not None and actual_amount > ul_amount:
        return NutrientStatus.RISKY
    if ratio > EXCESSIVE_THRESHOLD:
        return NutrientStatus.EXCESSIVE
    if ratio < DEFICIENT_THRESHOLD:
        return NutrientStatus.DEFICIENT
    if ratio < LOW_THRESHOLD:
        return NutrientStatus.LOW
    return NutrientStatus.ADEQUATE


def contains_forbidden_terms(messages: list[str]) -> bool:
    """사용자 노출 문구에 금지 표현이 있는지 확인한다.

    Args:
        messages: 사용자 노출 문구 목록.

    Returns:
        금지 표현 포함 여부.
    """
    return any(term in message for message in messages for term in FORBIDDEN_TERMS)


def analyze_nutrient_intakes(
    profile: UserProfile,
    intakes: list[NutrientIntake],
) -> NutritionAnalysisResponse:
    """KDRIs 샘플 기준값과 섭취량을 비교한다.

    Args:
        profile: 사용자 프로필.
        intakes: 영양소 섭취량 목록.

    Returns:
        영양소별 섭취 상태 분석 응답.

    Raises:
        ValueError: 기준값이 없거나 단위 환산이 불가능한 영양소가 포함된 경우.
    """
    results: list[NutrientAnalysisResult] = []

    for intake in intakes:
        reference = lookup_kdris_reference(
            nutrient_code=intake.nutrient_code,
            age=profile.age,
            sex=profile.sex,
            pregnancy_status=profile.pregnancy_status,
        )
        if reference is None:
            raise ValueError(f"KDRIs reference not found: {intake.nutrient_code}")
        if reference.reference_amount is None:
            raise ValueError(
                f"KDRIs scalar reference not available for analysis: {intake.nutrient_code}"
            )

        actual_amount = convert_amount(
            amount=intake.amount,
            from_unit=intake.unit,
            to_unit=reference.reference_unit,
            nutrient_code=intake.nutrient_code,
        )
        ul_amount = reference.ul_amount
        if reference.ul_amount is not None and reference.ul_unit is not None:
            ul_amount = convert_amount(
                amount=reference.ul_amount,
                from_unit=reference.ul_unit,
                to_unit=reference.reference_unit,
                nutrient_code=intake.nutrient_code,
            )
        status = _classify_status(
            actual_amount=actual_amount,
            reference_amount=reference.reference_amount,
            ul_amount=ul_amount,
        )
        ratio = actual_amount / reference.reference_amount
        results.append(
            NutrientAnalysisResult(
                nutrient_code=reference.nutrient_code,
                nutrient_name=reference.nutrient_name,
                reference_amount=reference.reference_amount,
                reference_type=reference.reference_type,
                source_id=reference.source_id,
                errata_version=reference.errata_version,
                review_status=reference.review_status,
                reference_unit=reference.reference_unit,
                actual_amount=round(actual_amount, AMOUNT_DECIMALS),
                ratio=round(ratio, RATIO_DECIMALS),
                ul_amount=ul_amount,
                status=status,
                priority=0,
                user_message=_message_for_status(status),
            )
        )

    low_results = [
        result
        for result in results
        if result.status in (NutrientStatus.DEFICIENT, NutrientStatus.LOW)
    ]
    priority_boosts: dict[str, int] = {}
    for result in low_results:
        priority_match = get_chronic_priority_match(
            nutrient_code=result.nutrient_code,
            chronic_diseases=profile.chronic_diseases,
        )
        if priority_match is None:
            continue
        priority_boosts[result.nutrient_code] = priority_match.boost_score
        result.priority_context = list(priority_match.condition_codes)
        result.priority_source_ids = list(priority_match.source_ids)
        result.user_message = priority_match.message

    low_results.sort(
        key=lambda result: (
            -priority_boosts.get(result.nutrient_code, 0),
            result.ratio,
            result.nutrient_code,
        )
    )
    for index, result in enumerate(low_results, start=1):
        result.priority = index

    dataset_context = get_kdris_dataset_context()
    return NutritionAnalysisResponse(
        results=results,
        dataset_status=dataset_context["dataset_status"],
        dataset_version=dataset_context["dataset_version"],
        source_manifest_version=dataset_context["source_manifest_version"],
    )

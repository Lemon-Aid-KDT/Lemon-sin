"""통합 건강 요약 서비스.

사용자 프로필 + 하루 섭취 영양소 + 활동(걸음수)를 입력으로, 기업 과제 Output을
한 번에 산출한다(여러 도메인 조합 흐름이므로 services 계층에 둔다):

    ① 부족 영양소 추천 + ② 영양소 섭취량 권고 (KDRIs 대조 + 기여도/충족률)
    ③ 체중 변화 예측 (1주/1개월/3개월)
    ④ 활동(운동) 권고 (권장 걸음수 + v1 점수)

순수 계산만 수행하며 외부 I/O는 없다. 사용자 노출 문구에는 의료적 단정
표현(진단/처방/치료/보장/확실히)을 넣지 않는다.

Reference:
    backend/CLAUDE.md §서비스 계층
    docs/dev-guides/01·03·04 (BMI·BMR·체중예측), 05·06 (KDRIs)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from src.algorithms.activity import calculate_recommended_steps, calculate_v1_score
from src.algorithms.bmi import calculate_bmi, classify_bmi
from src.models.schemas.algorithm import BMICategory
from src.models.schemas.health_summary import (
    ActivityAdvice,
    HealthSummary,
    NutrientContribution,
)
from src.models.schemas.nutrition import (
    NutrientEvaluation,
    NutrientStatus,
    UserKDRIsContext,
)
from src.models.schemas.user import UserProfile
from src.nutrition.kdris_evaluation import evaluate_intake_against_kdris
from src.prediction.weight import predict_weight_periods

_ENERGY_CODE: Final[str] = "energy_kcal"
_SHORT_STATUSES: Final[frozenset[NutrientStatus]] = frozenset(
    {NutrientStatus.DEFICIENT, NutrientStatus.LOW}
)

# 부족 영양소별 보충 추천 식품 (정보 제공 수준 — 특정 제품·효능 주장 없음).
FOOD_SUGGESTIONS: Final[dict[str, str]] = {
    "energy_kcal": "균형 잡힌 한 끼 추가",
    "protein_g": "닭가슴살·달걀·두부·생선",
    "fiber_g": "채소·통곡물·콩류",
    "calcium_mg": "우유·요거트·멸치·두부",
    "iron_mg": "소고기·시금치·콩류",
    "vitamin_a_ug": "당근·시금치·달걀노른자",
    "vitamin_c_mg": "감귤·딸기·파프리카·브로콜리",
}


def _to_contribution(evaluation: NutrientEvaluation) -> NutrientContribution:
    """KDRIs 평가 결과를 기여도(충족률) 관점의 권고로 변환한다.

    Args:
        evaluation: `evaluate_intake_against_kdris`의 단일 영양소 결과.

    Returns:
        기여도·부족분·추천 식품·문구를 담은 NutrientContribution.
    """
    pct = round(evaluation.ratio_pct)
    is_short = evaluation.status in _SHORT_STATUSES
    shortfall = 0.0
    food = ""
    if evaluation.status is NutrientStatus.RISKY:
        message = evaluation.message_ko
    elif is_short:
        if evaluation.reference_amount is not None:
            shortfall = round(max(0.0, evaluation.reference_amount - evaluation.intake_amount), 1)
        food = FOOD_SUGGESTIONS.get(evaluation.code, "")
        suffix = (
            f" 부족분 약 {shortfall}{evaluation.unit}은 {food}(으)로 보충을 권장해요."
            if food
            else ""
        )
        message = f"하루 권장량의 {pct}%를 채웠어요.{suffix}"
    elif evaluation.status is NutrientStatus.EXCESSIVE:
        message = f"하루 권장량의 {pct}%로 다소 많아요. 양 조절을 권장해요."
    else:  # ADEQUATE
        message = f"하루 권장량의 {pct}%로 적정 범위예요."

    return NutrientContribution(
        code=evaluation.code,
        name_ko=evaluation.name_ko,
        intake_amount=evaluation.intake_amount,
        reference_amount=evaluation.reference_amount,
        unit=evaluation.unit,
        fulfillment_pct=evaluation.ratio_pct,
        status=evaluation.status,
        shortfall_amount=shortfall,
        food_suggestion=food,
        message_ko=message,
    )


def _build_activity_advice(
    user: UserProfile, daily_steps: int, bmi_category: BMICategory
) -> ActivityAdvice:
    """권장 걸음수·v1 점수 기반 활동 권고를 만든다."""
    recommended = calculate_recommended_steps(user.sex, user.age, bmi_category)
    v1 = calculate_v1_score(daily_steps, recommended)
    gap = max(0, recommended - daily_steps)
    if gap == 0:
        message = f"권장 걸음수({recommended:,}보)를 달성했어요. v1 활동점수 {v1}점."
    else:
        message = (
            f"권장 {recommended:,}보 중 {daily_steps:,}보 — 하루 약 {gap:,}보를 더 걸으면 좋아요. "
            f"v1 활동점수 {v1}점."
        )
    return ActivityAdvice(
        actual_steps=daily_steps,
        recommended_steps=recommended,
        step_gap=gap,
        v1_score=v1,
        message_ko=message,
    )


def build_health_summary(
    user: UserProfile,
    daily_steps: int,
    daily_intake: Mapping[str, float],
    kdris_rows: list[dict[str, str]] | None = None,
) -> HealthSummary:
    """사용자·하루 섭취·활동으로 통합 건강 요약(Output)을 산출한다.

    Args:
        user: 사용자 프로필 (성별·나이·키·몸무게 등).
        daily_steps: 하루 평균 걸음수.
        daily_intake: 하루 섭취 영양소 매핑(키는 rda_matcher 영양소 키, "kcal" 포함).
        kdris_rows: 미리 로드한 KDRIs 행. None이면 기본 경로에서 로드.

    Returns:
        HealthSummary — 부족 영양소·섭취량 권고·체중 예측·활동 권고.

    Raises:
        ValueError: BMI/체중예측/활동 계산의 입력이 허용 범위를 벗어난 경우.

    Examples:
        >>> profile = UserProfile(age=52, sex="male", height_cm=168, weight_kg=78)
        >>> summary = build_health_summary(profile, 7200, {"kcal": 1700.0, "calcium_mg": 400.0})
        >>> summary.bmi_category.value
        'obese_1'
    """
    bmi = calculate_bmi(user.weight_kg, user.height_cm)
    bmi_category = classify_bmi(bmi)

    # ①② 영양: KDRIs 대조 → 기여도/부족 권고
    kdris_context = UserKDRIsContext(age=user.age, sex=user.sex)
    evaluation = evaluate_intake_against_kdris(daily_intake, kdris_context, rows=kdris_rows)
    contributions = [_to_contribution(e) for e in evaluation.evaluations]
    deficient = [c for c in contributions if c.status in _SHORT_STATUSES]

    # ③ 체중 변화 예측 (1주/1개월/3개월)
    daily_intake_kcal = float(daily_intake.get("kcal", 0.0))
    weight_predictions = predict_weight_periods(
        weight_kg=user.weight_kg,
        height_cm=user.height_cm,
        age=user.age,
        sex=user.sex,
        daily_steps=daily_steps,
        daily_intake_kcal=daily_intake_kcal,
    )

    # ④ 활동 권고
    activity = _build_activity_advice(user, daily_steps, bmi_category)

    summary_message = _build_summary_message(
        bmi, bmi_category.value, len(deficient), weight_predictions.month_1.predicted_weight
    )
    return HealthSummary(
        bmi=bmi,
        bmi_category=bmi_category,
        daily_intake_kcal=daily_intake_kcal,
        nutrient_contributions=contributions,
        deficient_recommendations=deficient,
        weight_predictions=weight_predictions,
        activity=activity,
        summary_message_ko=summary_message,
    )


def _build_summary_message(
    bmi: float,
    bmi_category: str,
    deficient_count: int,
    month_1_weight: float,
) -> str:
    """전체 요약 문구를 만든다."""
    labels = {
        "underweight": "저체중",
        "normal": "정상",
        "overweight": "과체중",
        "obese_1": "비만 1단계",
        "obese_2": "비만 2단계",
    }
    label = labels.get(bmi_category, bmi_category)
    return (
        f"BMI {bmi}({label}), 보충이 필요한 영양소 {deficient_count}종, "
        f"한 달 뒤 예상 체중 {month_1_weight}kg입니다."
    )

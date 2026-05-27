"""활동점수 v1-v4 산출식."""

from __future__ import annotations

from src.algorithms.bmi import evaluate_bmi
from src.models.schemas.algorithm import (
    ActivityScoreRequest,
    ActivityScoreResponse,
    BMICategory,
    HRMaxFormula,
    TargetHeartRateRange,
)

BASE_STEPS = 8000
FEMALE_STEP_FACTOR = 0.95
MALE_STEP_FACTOR = 1.0
AGE_40_CUTOFF = 40
AGE_60_CUTOFF = 60
AGE_75_CUTOFF = 75
AGE_BASE_STEPS_UNDER_40 = 9000
AGE_BASE_STEPS_40_TO_59 = 8000
AGE_BASE_STEPS_60_TO_74 = 7000
AGE_BASE_STEPS_75_PLUS = 6000
ACHIEVEMENT_CAP = 1.2
MAX_V1_SCORE_AT_CAP = 83.33
GUIDE_HR_MAX_BASE = 220.0
TANAKA_HR_MAX_BASE = 208.0
TANAKA_AGE_COEFFICIENT = 0.7
GELLISH_HR_MAX_BASE = 207.0
GELLISH_AGE_COEFFICIENT = 0.7
NES_HR_MAX_BASE = 211.0
NES_AGE_COEFFICIENT = 0.64
TARGET_HR_LOW_RATIO = 0.64
TARGET_HR_HIGH_RATIO = 0.76
TARGET_HR_FULL_CREDIT_MINUTES = 30.0
NO_WEARABLE_HR_FACTOR = 0.7
V2_BASE_MULTIPLIER = 0.7
V2_HR_MULTIPLIER_WEIGHT = 0.3
MIN_PERCENTILE_SAMPLE_SIZE = 30
TOP_10_PERCENT = 10.0
TOP_20_PERCENT = 20.0
TOP_30_PERCENT = 30.0
BONUS_TOP_10 = 10
BONUS_TOP_20 = 5
BONUS_TOP_30 = 3
MAX_SCORE = 100.0
MAX_DISEASE_MULTIPLIER = 1.3
ACTIVITY_ALGORITHM_VERSION = "activity-v1.0.0"

BMI_STEP_FACTORS = {
    BMICategory.UNDERWEIGHT: 1.0,
    BMICategory.NORMAL: 1.0,
    BMICategory.OVERWEIGHT: 1.05,
    BMICategory.OBESE_1: 1.05,
    BMICategory.OBESE_2: 1.05,
    BMICategory.OBESE_3: 1.05,
}

DISEASE_WEIGHTS = {
    "diabetes": 0.10,
    "diabetes_t2": 0.10,
    "t2dm": 0.10,
    "hypertension": 0.10,
    "htn": 0.10,
    "cardiovascular": 0.15,
    "cad": 0.15,
    "joint": 0.15,
    "osteoarthritis": 0.15,
    "oa": 0.15,
    "respiratory": 0.10,
    "copd": 0.10,
}
CONDITION_RECOMMENDED_STEPS = {
    "diabetes": 7500,
    "diabetes_t2": 7500,
    "t2dm": 7500,
    "hypertension": 7500,
    "htn": 7500,
    "cardiovascular": 6500,
    "cad": 6500,
    "joint": 6000,
    "osteoarthritis": 6000,
    "oa": 6000,
    "respiratory": 5000,
    "copd": 5000,
}
MAX_DISEASE_WEIGHT_SUM = 0.30
SMOKING_MULTIPLIERS = {
    "former_lt_1y": 1.05,
    "current_light": 1.05,
    "current_heavy": 1.10,
}


def get_sex_factor(sex: str) -> float:
    """권장 걸음수 성별 계수를 반환한다.

    Args:
        sex: "male" 또는 "female".

    Returns:
        성별 계수.
    """
    return FEMALE_STEP_FACTOR if sex == "female" else MALE_STEP_FACTOR


def get_age_base_steps(age: int) -> int:
    """연령대별 권장 걸음수 기준값을 반환한다.

    Args:
        age: 만 나이.

    Returns:
        연령대별 기준 걸음수.
    """
    if age < AGE_40_CUTOFF:
        return AGE_BASE_STEPS_UNDER_40
    if age < AGE_60_CUTOFF:
        return AGE_BASE_STEPS_40_TO_59
    if age < AGE_75_CUTOFF:
        return AGE_BASE_STEPS_60_TO_74
    return AGE_BASE_STEPS_75_PLUS


def calculate_recommended_steps(
    sex: str,
    age: int,
    bmi_category: BMICategory,
    chronic_diseases: list[str] | None = None,
) -> int:
    """사용자별 권장 걸음수를 계산한다.

    Args:
        sex: "male" 또는 "female".
        age: 만 나이.
        bmi_category: BMI 기준 분류.
        chronic_diseases: 질환별 안전 권장량을 적용할 코드 목록.

    Returns:
        반올림한 권장 걸음수.
    """
    condition_steps = [
        CONDITION_RECOMMENDED_STEPS[disease.casefold()]
        for disease in chronic_diseases or []
        if disease.casefold() in CONDITION_RECOMMENDED_STEPS
    ]
    if condition_steps:
        return min(condition_steps)
    return round(get_age_base_steps(age) * get_sex_factor(sex) * BMI_STEP_FACTORS[bmi_category])


def calculate_v1_score(actual_steps: int, recommended_steps: int) -> float:
    """권장 걸음수 대비 v1 기본 활동점수를 계산한다.

    Args:
        actual_steps: 실제 일일 걸음수.
        recommended_steps: 사용자별 권장 걸음수.

    Returns:
        v1 점수.

    Raises:
        ValueError: 권장 걸음수가 0 이하인 경우.
    """
    if recommended_steps <= 0:
        raise ValueError("recommended_steps must be greater than 0")
    achievement = min(actual_steps / recommended_steps, ACHIEVEMENT_CAP)
    return round(achievement * MAX_V1_SCORE_AT_CAP, 2)


def calculate_estimated_hr_max(age: int, formula: HRMaxFormula = "tanaka_2001") -> float:
    """HRmax 추정값을 계산한다.

    Args:
        age: 만 나이.
        formula: 회사 가이드 호환식 또는 Tanaka 2001 식.

    Returns:
        HRmax 추정값.
    """
    if formula == "tanaka_2001":
        return TANAKA_HR_MAX_BASE - TANAKA_AGE_COEFFICIENT * age
    if formula == "gellish_2007":
        return GELLISH_HR_MAX_BASE - GELLISH_AGE_COEFFICIENT * age
    if formula == "nes_2013":
        return NES_HR_MAX_BASE - NES_AGE_COEFFICIENT * age
    return GUIDE_HR_MAX_BASE - age


def calculate_target_hr_range(
    age: int,
    formula: HRMaxFormula = "tanaka_2001",
) -> TargetHeartRateRange:
    """목표 심박 구간을 계산한다.

    Args:
        age: 만 나이.
        formula: HRmax 추정식.

    Returns:
        목표 심박 하한/상한.
    """
    hr_max = calculate_estimated_hr_max(age=age, formula=formula)
    return TargetHeartRateRange(
        low_bpm=round(hr_max * TARGET_HR_LOW_RATIO),
        high_bpm=round(hr_max * TARGET_HR_HIGH_RATIO),
        formula=formula,
    )


def calculate_hr_factor(target_hr_minutes: float | None) -> float:
    """심박수 가중 계수를 계산한다.

    Args:
        target_hr_minutes: 목표 심박 구간 유지 시간. None이면 웨어러블 미착용 fallback.

    Returns:
        0.0-1.0 범위의 심박수 가중 계수.
    """
    if target_hr_minutes is None:
        return NO_WEARABLE_HR_FACTOR
    return min(target_hr_minutes / TARGET_HR_FULL_CREDIT_MINUTES, 1.0)


def calculate_v2_score(v1_score: float, hr_factor: float) -> float:
    """심박수 가중 v2 점수를 계산한다.

    Args:
        v1_score: v1 기본 활동점수.
        hr_factor: 심박수 가중 계수.

    Returns:
        v2 점수.
    """
    multiplier = V2_BASE_MULTIPLIER + V2_HR_MULTIPLIER_WEIGHT * hr_factor
    return round(v1_score * multiplier, 2)


def calculate_percentile_bonus(user_v2: float, group_v2_scores: list[float]) -> int:
    """동일 그룹 내 백분위 보너스를 계산한다.

    Args:
        user_v2: 사용자 v2 점수.
        group_v2_scores: 비교군 v2 점수 목록.

    Returns:
        백분위 보너스. 표본이 부족하면 0.
    """
    if len(group_v2_scores) < MIN_PERCENTILE_SAMPLE_SIZE:
        return 0

    higher_count = sum(1 for score in group_v2_scores if score > user_v2)
    percentile_rank = (higher_count / len(group_v2_scores)) * MAX_SCORE

    if percentile_rank <= TOP_10_PERCENT:
        return BONUS_TOP_10
    if percentile_rank <= TOP_20_PERCENT:
        return BONUS_TOP_20
    if percentile_rank <= TOP_30_PERCENT:
        return BONUS_TOP_30
    return 0


def calculate_v3_score(v2_score: float, bonus: int) -> float:
    """백분위 보너스를 반영한 v3 점수를 계산한다.

    Args:
        v2_score: v2 점수.
        bonus: 백분위 보너스.

    Returns:
        100점 상한이 적용된 v3 점수.
    """
    return round(min(MAX_SCORE, v2_score + bonus), 2)


def calculate_disease_multiplier(diseases: list[str], smoking_status: str = "never") -> float:
    """활동 동기 점수 가중치를 계산한다.

    Args:
        diseases: 만성질환 코드 목록.
        smoking_status: 흡연 상태. 만성질환 가중과 중복하지 않고 max 규칙을 적용한다.

    Returns:
        1.0-1.3 범위의 가중치.
    """
    total_addon = sum(DISEASE_WEIGHTS.get(disease.casefold(), 0.0) for disease in diseases)
    chronic_multiplier = min(1.0 + min(total_addon, MAX_DISEASE_WEIGHT_SUM), MAX_DISEASE_MULTIPLIER)
    smoking_multiplier = SMOKING_MULTIPLIERS.get(smoking_status, 1.0)
    return round(max(chronic_multiplier, smoking_multiplier), 3)


def calculate_v4_score(v3_score: float, multiplier: float) -> float:
    """만성질환 프로젝트 가중치를 반영한 v4 점수를 계산한다.

    Args:
        v3_score: v3 점수.
        multiplier: 만성질환 프로젝트 가중치.

    Returns:
        100점 상한이 적용된 v4 점수.
    """
    return round(min(MAX_SCORE, v3_score * multiplier), 2)


def calculate_activity_score(request: ActivityScoreRequest) -> ActivityScoreResponse:
    """활동점수 v1-v4 전체 결과를 계산한다.

    Args:
        request: 활동점수 요청 모델.

    Returns:
        BMI, 권장 걸음수, v1-v4 점수를 포함한 응답 모델.
    """
    bmi = evaluate_bmi(
        weight_kg=request.profile.weight_kg,
        height_cm=request.profile.height_cm,
        age=request.profile.age,
        sex=request.profile.sex,
        waist_cm=request.profile.waist_cm,
        body_fat_pct=request.profile.body_fat_pct,
        chronic_diseases=request.profile.chronic_diseases,
    )
    recommended_steps = calculate_recommended_steps(
        sex=request.profile.sex,
        age=request.profile.age,
        bmi_category=bmi.category,
        chronic_diseases=request.profile.chronic_diseases,
    )
    v1_score = calculate_v1_score(
        actual_steps=request.daily_steps,
        recommended_steps=recommended_steps,
    )
    target_hr_range = calculate_target_hr_range(
        age=request.profile.age,
        formula=request.hrmax_formula,
    )
    hr_factor = calculate_hr_factor(request.target_hr_minutes)
    v2_score = calculate_v2_score(v1_score=v1_score, hr_factor=hr_factor)
    percentile_bonus = calculate_percentile_bonus(
        user_v2=v2_score,
        group_v2_scores=request.group_v2_scores,
    )
    v3_score = calculate_v3_score(v2_score=v2_score, bonus=percentile_bonus)
    disease_multiplier = calculate_disease_multiplier(
        request.profile.chronic_diseases,
        smoking_status=request.profile.smoking_status,
    )
    v4_score = calculate_v4_score(v3_score=v3_score, multiplier=disease_multiplier)

    return ActivityScoreResponse(
        bmi=bmi,
        recommended_steps=recommended_steps,
        target_hr_range=target_hr_range,
        hr_factor=round(hr_factor, 3),
        percentile_bonus=percentile_bonus,
        disease_multiplier=disease_multiplier,
        v1_score=v1_score,
        v2_score=v2_score,
        v3_score=v3_score,
        v4_score=v4_score,
    )

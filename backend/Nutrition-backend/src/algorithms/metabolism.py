"""BMR/TDEE 산출식."""

from __future__ import annotations

from src.models.schemas.user import Sex

BMR_WEIGHT_COEFFICIENT = 10.0
BMR_HEIGHT_COEFFICIENT = 6.25
BMR_AGE_COEFFICIENT = 5.0
MALE_BMR_CONSTANT = 5.0
FEMALE_BMR_CONSTANT = -161.0
STEPS_LIGHT_ACTIVITY_CUTOFF = 5000
STEPS_MODERATE_ACTIVITY_CUTOFF = 7500
STEPS_ACTIVE_CUTOFF = 10000
STEPS_VERY_ACTIVE_CUTOFF = 12500
SEDENTARY_FACTOR = 1.200
LIGHT_FACTOR = 1.375
MODERATE_FACTOR = 1.550
ACTIVE_FACTOR = 1.725
VERY_ACTIVE_FACTOR = 1.900
ENERGY_DECIMALS = 0


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
    """Mifflin-St Jeor 공식으로 예상 BMR을 계산한다.

    Args:
        weight_kg: 체중(kg).
        height_cm: 키(cm).
        age: 만 나이.
        sex: "male" 또는 "female".

    Returns:
        예상 BMR(kcal/day).
    """
    base = (
        BMR_WEIGHT_COEFFICIENT * weight_kg
        + BMR_HEIGHT_COEFFICIENT * height_cm
        - BMR_AGE_COEFFICIENT * age
    )
    sex_constant = MALE_BMR_CONSTANT if sex == "male" else FEMALE_BMR_CONSTANT
    return round(base + sex_constant, ENERGY_DECIMALS)


def get_activity_factor(daily_steps: int) -> float:
    """일일 걸음수 기반 활동계수를 반환한다.

    Args:
        daily_steps: 일일 걸음수.

    Returns:
        프로젝트 가이드 활동계수.
    """
    if daily_steps < STEPS_LIGHT_ACTIVITY_CUTOFF:
        return SEDENTARY_FACTOR
    if daily_steps < STEPS_MODERATE_ACTIVITY_CUTOFF:
        return LIGHT_FACTOR
    if daily_steps < STEPS_ACTIVE_CUTOFF:
        return MODERATE_FACTOR
    if daily_steps < STEPS_VERY_ACTIVE_CUTOFF:
        return ACTIVE_FACTOR
    return VERY_ACTIVE_FACTOR


def calculate_tdee(estimated_bmr: float, daily_steps: int) -> float:
    """예상 BMR과 활동계수로 예상 TDEE를 계산한다.

    Args:
        estimated_bmr: 예상 BMR(kcal/day).
        daily_steps: 일일 걸음수.

    Returns:
        예상 TDEE(kcal/day).
    """
    return round(estimated_bmr * get_activity_factor(daily_steps), ENERGY_DECIMALS)

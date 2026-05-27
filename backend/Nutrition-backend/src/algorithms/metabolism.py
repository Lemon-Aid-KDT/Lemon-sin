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
KATCH_MCARDLE_BASE = 370.0
KATCH_MCARDLE_LBM_COEFFICIENT = 21.6
MIN_BODY_FAT_PERCENT = 10.0
MAX_BODY_FAT_PERCENT = 55.0


def calculate_mifflin_bmr(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
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


def calculate_katch_mcardle_bmr(weight_kg: float, body_fat_pct: float) -> float:
    """Katch-McArdle 공식으로 체지방률 기반 예상 BMR을 계산한다.

    Args:
        weight_kg: 체중(kg).
        body_fat_pct: 체지방률(%).

    Returns:
        예상 BMR(kcal/day).

    Raises:
        ValueError: 체지방률이 적용 가능한 범위를 벗어난 경우.
    """
    if not MIN_BODY_FAT_PERCENT <= body_fat_pct <= MAX_BODY_FAT_PERCENT:
        raise ValueError("body_fat_pct must be between 10 and 55")
    lean_body_mass = weight_kg * (1 - (body_fat_pct / 100))
    return round(
        KATCH_MCARDLE_BASE + KATCH_MCARDLE_LBM_COEFFICIENT * lean_body_mass,
        ENERGY_DECIMALS,
    )


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    body_fat_pct: float | None = None,
) -> float:
    """예상 BMR을 계산한다.

    체지방률이 신뢰 가능한 범위로 입력되면 Katch-McArdle 공식을 우선하고,
    그렇지 않으면 Mifflin-St Jeor 공식을 사용한다.

    Args:
        weight_kg: 체중(kg).
        height_cm: 키(cm).
        age: 만 나이.
        sex: "male" 또는 "female".
        body_fat_pct: 체지방률(%). 10~55 범위에서만 Katch-McArdle 적용.

    Returns:
        예상 BMR(kcal/day).
    """
    if body_fat_pct is not None and MIN_BODY_FAT_PERCENT <= body_fat_pct <= MAX_BODY_FAT_PERCENT:
        return calculate_katch_mcardle_bmr(weight_kg=weight_kg, body_fat_pct=body_fat_pct)
    return calculate_mifflin_bmr(weight_kg=weight_kg, height_cm=height_cm, age=age, sex=sex)


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


def calculate_exercise_kcal_from_mets(mets: float, weight_kg: float, minutes: float) -> float:
    """METs와 운동 시간으로 의도 운동 열량을 계산한다.

    Args:
        mets: 운동 METs 값.
        weight_kg: 체중(kg).
        minutes: 운동 시간(분).

    Returns:
        운동 소비 열량(kcal).

    Raises:
        ValueError: 입력값이 음수인 경우.
    """
    if mets < 0 or weight_kg < 0 or minutes < 0:
        raise ValueError("mets, weight_kg and minutes must be non-negative")
    return mets * 3.5 * weight_kg / 200 * minutes


def calculate_tdee(
    estimated_bmr: float,
    daily_steps: int,
    *,
    weight_kg: float | None = None,
    intentional_exercises: list[tuple[float, float]] | None = None,
) -> float:
    """예상 BMR과 활동계수로 예상 TDEE를 계산한다.

    Args:
        estimated_bmr: 예상 BMR(kcal/day).
        daily_steps: 일일 걸음수.
        weight_kg: METs 기반 운동 열량 계산용 체중.
        intentional_exercises: (METs, minutes) 목록.

    Returns:
        예상 TDEE(kcal/day).

    Raises:
        ValueError: 의도 운동 목록이 있으나 체중이 없는 경우.
    """
    exercise_kcal = 0.0
    if intentional_exercises:
        if weight_kg is None:
            raise ValueError("weight_kg is required when intentional_exercises are provided")
        exercise_kcal = sum(
            calculate_exercise_kcal_from_mets(mets=mets, weight_kg=weight_kg, minutes=minutes)
            for mets, minutes in intentional_exercises
        )
    return round(estimated_bmr * get_activity_factor(daily_steps) + exercise_kcal, ENERGY_DECIMALS)

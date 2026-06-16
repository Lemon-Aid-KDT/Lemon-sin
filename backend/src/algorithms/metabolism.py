"""기초대사량(BMR) 및 총에너지소비량(TDEE) 계산 모듈.

회사 가이드의 Mifflin-St Jeor 공식과 걸음수 기반 활동계수 테이블을 구현한다.

Reference:
    docs/dev-guides/03-bmr-tdee.md
"""

from __future__ import annotations

from typing import Final

_WEIGHT_MIN_KG: Final[float] = 10.0
_WEIGHT_MAX_KG: Final[float] = 300.0
_HEIGHT_MIN_CM: Final[float] = 50.0
_HEIGHT_MAX_CM: Final[float] = 250.0
_AGE_MIN: Final[int] = 1
_AGE_MAX: Final[int] = 120

BMR_WEIGHT_COEF: Final[float] = 10.0
BMR_HEIGHT_COEF: Final[float] = 6.25
BMR_AGE_COEF: Final[float] = 5.0
BMR_MALE_CONSTANT: Final[float] = 5.0
BMR_FEMALE_CONSTANT: Final[float] = -161.0
"""Mifflin-St Jeor 공식 상수."""

ACTIVITY_FACTORS: Final[list[tuple[int, float]]] = [
    (5000, 1.200),  # < 5,000 보
    (7500, 1.375),  # < 7,500 보
    (10000, 1.550),  # < 10,000 보
    (12500, 1.725),  # < 12,500 보
]
"""(걸음수 상한, 활동계수) 정렬된 리스트."""

ACTIVITY_FACTOR_MAX: Final[float] = 1.900
"""12,500보 이상의 매우 활발한 활동계수."""


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor 공식으로 기초대사량(BMR)을 계산한다.

    Args:
        weight_kg: 체중 (kg, 10~300).
        height_cm: 키 (cm, 50~250).
        age: 만 나이 (1~120).
        sex: 성별 ("male" | "female").

    Returns:
        기초대사량 (kcal/일, 소수점 1자리).

    Raises:
        ValueError: 입력값이 허용 범위를 벗어나거나 sex가 잘못된 경우.

    Examples:
        >>> calculate_bmr(68.0, 160, 50, "female")
        1269.0
        >>> calculate_bmr(82.0, 175, 45, "male")
        1694.0
    """
    if not _WEIGHT_MIN_KG <= weight_kg <= _WEIGHT_MAX_KG:
        raise ValueError(f"weight_kg must be {_WEIGHT_MIN_KG}-{_WEIGHT_MAX_KG}, got {weight_kg}")
    if not _HEIGHT_MIN_CM <= height_cm <= _HEIGHT_MAX_CM:
        raise ValueError(f"height_cm must be {_HEIGHT_MIN_CM}-{_HEIGHT_MAX_CM}, got {height_cm}")
    if not _AGE_MIN <= age <= _AGE_MAX:
        raise ValueError(f"age must be {_AGE_MIN}-{_AGE_MAX}, got {age}")
    if sex == "male":
        constant = BMR_MALE_CONSTANT
    elif sex == "female":
        constant = BMR_FEMALE_CONSTANT
    else:
        raise ValueError(f"sex must be 'male' or 'female', got {sex!r}")
    bmr = BMR_WEIGHT_COEF * weight_kg + BMR_HEIGHT_COEF * height_cm - BMR_AGE_COEF * age + constant
    # 가이드 골드값(여 1269.0 / 남 1694.0)은 정수 kcal 기준 — 정수로 반올림한다.
    return round(bmr, 0)


def get_activity_factor(daily_steps: int) -> float:
    """일일 걸음수에 따른 활동계수를 반환한다.

    Args:
        daily_steps: 일일 걸음수 (0 이상).

    Returns:
        활동계수 (1.200 ~ 1.900).

    Raises:
        ValueError: daily_steps < 0인 경우.

    Examples:
        >>> get_activity_factor(3000)
        1.2
        >>> get_activity_factor(8000)
        1.55
        >>> get_activity_factor(15000)
        1.9
    """
    if daily_steps < 0:
        raise ValueError(f"daily_steps must be non-negative, got {daily_steps}")
    for upper_bound, factor in ACTIVITY_FACTORS:
        if daily_steps < upper_bound:
            return factor
    return ACTIVITY_FACTOR_MAX


def calculate_tdee(bmr: float, daily_steps: int) -> float:
    """총 에너지 소비량(TDEE)을 계산한다.

    Args:
        bmr: 기초대사량 (kcal/일, 0 이상).
        daily_steps: 일일 걸음수 (0 이상).

    Returns:
        총 에너지 소비량 (kcal/일, 소수점 1자리).

    Raises:
        ValueError: bmr < 0 또는 daily_steps < 0인 경우.

    Examples:
        >>> calculate_tdee(1269.0, 6500)
        1744.9
    """
    if bmr < 0:
        raise ValueError(f"bmr must be non-negative, got {bmr}")
    factor = get_activity_factor(daily_steps)
    return round(bmr * factor, 1)

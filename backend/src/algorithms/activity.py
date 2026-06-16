"""v1 활동점수 산출 알고리즘.

회사 가이드의 v1 정의(권장 걸음수 + 기본점수)를 구현한 순수 함수 모듈.

Reference:
    docs/dev-guides/01-bmi-and-v1-algorithm.md §v1 권장 걸음수, §v1 기본점수
"""

from __future__ import annotations

from typing import Final

from src.models.schemas.algorithm import BMICategory

_BASE_STEPS: Final[int] = 8000
"""기준 권장 걸음수 (성별·나이·BMI 보정 전)."""

_AGE_MAX: Final[int] = 120
_MIDDLE_AGE_LOWER: Final[int] = 40
_SENIOR_AGE_LOWER: Final[int] = 60
"""연령 계수 구간 경계 (만 나이)."""

SEX_FACTORS: Final[dict[str, float]] = {"male": 1.0, "female": 0.95}
"""성별 계수 (가이드 기준)."""

BMI_FACTORS: Final[dict[BMICategory, float]] = {
    BMICategory.UNDERWEIGHT: 0.9,
    BMICategory.NORMAL: 1.0,
    BMICategory.OVERWEIGHT: 1.05,
    BMICategory.OBESE_1: 1.1,
    BMICategory.OBESE_2: 1.15,
}
"""BMI 카테고리별 권장 걸음수 보정 계수 (가이드 기준)."""

V1_BASE_MAX: Final[float] = 83.33
"""달성률 1.0일 때 기본점수 (1.2 x 83.33 = 100점 설계)."""

V1_ACHIEVEMENT_CAP: Final[float] = 1.2
"""달성률 상한 (120%에서 100점)."""


def get_age_factor(age: int) -> float:
    """연령에 따른 권장 걸음수 보정 계수를 반환한다.

    Args:
        age: 만 나이 (1~120 범위).

    Returns:
        연령 계수 (40세 미만 1.0 / 40~59세 0.9 / 60세 이상 0.8).

    Raises:
        ValueError: age가 1~120 범위를 벗어난 경우.

    Examples:
        >>> get_age_factor(30)
        1.0
        >>> get_age_factor(50)
        0.9
        >>> get_age_factor(65)
        0.8
    """
    if not 1 <= age <= _AGE_MAX:
        raise ValueError(f"age must be 1-{_AGE_MAX}, got {age}")
    if age < _MIDDLE_AGE_LOWER:
        return 1.0
    if age < _SENIOR_AGE_LOWER:
        return 0.9
    return 0.8


def calculate_recommended_steps(sex: str, age: int, bmi_category: BMICategory) -> int:
    """성별·연령·BMI로 권장 걸음수를 계산한다.

    Args:
        sex: 성별 ("male" | "female").
        age: 만 나이.
        bmi_category: BMI 분류.

    Returns:
        권장 걸음수 (정수, round 적용).

    Raises:
        ValueError: sex가 잘못되었거나 age가 범위를 벗어난 경우.

    Examples:
        >>> calculate_recommended_steps("female", 50, BMICategory.OBESE_1)
        7524
        >>> calculate_recommended_steps("male", 30, BMICategory.NORMAL)
        8000
    """
    if sex not in SEX_FACTORS:
        raise ValueError(f"sex must be 'male' or 'female', got {sex!r}")
    sex_factor = SEX_FACTORS[sex]
    age_factor = get_age_factor(age)
    bmi_factor = BMI_FACTORS[bmi_category]
    return round(_BASE_STEPS * sex_factor * age_factor * bmi_factor)


def calculate_v1_score(actual_steps: int, recommended_steps: int) -> float:
    """실제 걸음수 대비 권장 걸음수로 v1 기본점수를 계산한다.

    Args:
        actual_steps: 실제 걸음수 (0 이상).
        recommended_steps: 권장 걸음수 (양수).

    Returns:
        v1 기본점수 (0~100, 소수점 1자리). 달성률 120%에서 100점.

    Raises:
        ValueError: actual_steps < 0 또는 recommended_steps <= 0인 경우.

    Examples:
        >>> calculate_v1_score(7000, 7524)
        77.5
        >>> calculate_v1_score(9028, 7524)
        100.0
    """
    if actual_steps < 0:
        raise ValueError(f"actual_steps must be non-negative, got {actual_steps}")
    if recommended_steps <= 0:
        raise ValueError(f"recommended_steps must be positive, got {recommended_steps}")
    achievement = min(actual_steps / recommended_steps, V1_ACHIEVEMENT_CAP)
    return round(achievement * V1_BASE_MAX, 1)

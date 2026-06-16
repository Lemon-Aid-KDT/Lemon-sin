"""BMI 계산 및 한국·아시아 기준 분류.

회사 가이드의 BMI 산식과 한국·아시아 분류 경계를 구현한 순수 함수 모듈.

Reference:
    docs/dev-guides/01-bmi-and-v1-algorithm.md §BMI 분류
"""

from __future__ import annotations

from typing import Final

from src.models.schemas.algorithm import BMICategory

_WEIGHT_MIN_KG: Final[float] = 10.0
_WEIGHT_MAX_KG: Final[float] = 300.0
_HEIGHT_MIN_CM: Final[float] = 50.0
_HEIGHT_MAX_CM: Final[float] = 250.0

_NORMAL_LOWER: Final[float] = 18.5
_OVERWEIGHT_LOWER: Final[float] = 23.0
_OBESE_1_LOWER: Final[float] = 25.0
_OBESE_2_LOWER: Final[float] = 30.0
"""한국·아시아 BMI 분류 경계값 (kg/m²)."""


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """체중과 키로 BMI를 계산한다.

    Args:
        weight_kg: 체중 (kg, 10~300 범위).
        height_cm: 키 (cm, 50~250 범위).

    Returns:
        BMI 값 (소수점 1자리, kg/m²).

    Raises:
        ValueError: 입력값이 허용 범위를 벗어난 경우.

    Examples:
        >>> calculate_bmi(68.0, 160)
        26.6
        >>> calculate_bmi(60.0, 170)
        20.8
    """
    if not _WEIGHT_MIN_KG <= weight_kg <= _WEIGHT_MAX_KG:
        raise ValueError(f"weight_kg must be {_WEIGHT_MIN_KG}-{_WEIGHT_MAX_KG}, got {weight_kg}")
    if not _HEIGHT_MIN_CM <= height_cm <= _HEIGHT_MAX_CM:
        raise ValueError(f"height_cm must be {_HEIGHT_MIN_CM}-{_HEIGHT_MAX_CM}, got {height_cm}")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m**2), 1)


def classify_bmi(bmi: float) -> BMICategory:
    """BMI 값을 한국·아시아 기준으로 분류한다.

    Args:
        bmi: BMI 값 (kg/m²).

    Returns:
        BMICategory 분류 결과.

    Raises:
        ValueError: bmi가 0 이하인 경우.

    Examples:
        >>> classify_bmi(20.8)
        <BMICategory.NORMAL: 'normal'>
        >>> classify_bmi(26.6)
        <BMICategory.OBESE_1: 'obese_1'>
    """
    if bmi <= 0:
        raise ValueError(f"bmi must be positive, got {bmi}")
    if bmi < _NORMAL_LOWER:
        return BMICategory.UNDERWEIGHT
    if bmi < _OVERWEIGHT_LOWER:
        return BMICategory.NORMAL
    if bmi < _OBESE_1_LOWER:
        return BMICategory.OVERWEIGHT
    if bmi < _OBESE_2_LOWER:
        return BMICategory.OBESE_1
    return BMICategory.OBESE_2

"""한국·아시아 BMI 산출식."""

from __future__ import annotations

from src.models.schemas.algorithm import BMICategory, BMIResult

UNDERWEIGHT_CUTOFF = 18.5
OVERWEIGHT_CUTOFF = 23.0
OBESE_1_CUTOFF = 25.0
OBESE_2_CUTOFF = 30.0
CM_PER_METER = 100
BMI_DECIMALS = 1


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI를 계산한다.

    Args:
        weight_kg: 체중(kg).
        height_cm: 키(cm).

    Returns:
        소수점 1자리로 반올림한 BMI.

    Raises:
        ValueError: 키 또는 체중이 0 이하인 경우.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be greater than 0")
    if height_cm <= 0:
        raise ValueError("height_cm must be greater than 0")

    height_m = height_cm / CM_PER_METER
    return round(weight_kg / (height_m**2), BMI_DECIMALS)


def classify_bmi(bmi: float) -> BMICategory:
    """한국·아시아 기준으로 BMI를 분류한다.

    Args:
        bmi: BMI 값.

    Returns:
        BMI 기준 분류.
    """
    if bmi < UNDERWEIGHT_CUTOFF:
        return BMICategory.UNDERWEIGHT
    if bmi < OVERWEIGHT_CUTOFF:
        return BMICategory.NORMAL
    if bmi < OBESE_1_CUTOFF:
        return BMICategory.OVERWEIGHT
    if bmi < OBESE_2_CUTOFF:
        return BMICategory.OBESE_1
    return BMICategory.OBESE_2


def evaluate_bmi(weight_kg: float, height_cm: float) -> BMIResult:
    """BMI 값과 분류를 함께 반환한다.

    Args:
        weight_kg: 체중(kg).
        height_cm: 키(cm).

    Returns:
        BMI 계산 결과.

    Raises:
        ValueError: 키 또는 체중이 0 이하인 경우.
    """
    bmi = calculate_bmi(weight_kg=weight_kg, height_cm=height_cm)
    return BMIResult(bmi=bmi, category=classify_bmi(bmi))

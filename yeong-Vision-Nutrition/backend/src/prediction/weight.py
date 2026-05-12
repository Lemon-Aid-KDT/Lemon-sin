"""7-step 체중 예측 산출식."""

from __future__ import annotations

from src.algorithms.metabolism import calculate_bmr, calculate_tdee
from src.models.schemas.algorithm import WeightPredictionResponse, WeightPredictionStep
from src.models.schemas.user import Sex

KCAL_PER_KG_FAT = 7700.0
LOSS_CORRECTION = 0.85
GAIN_CORRECTION = 0.95
LONG_TERM_WARNING_DAYS = 90
ROUND_KCAL_DECIMALS = 1
ROUND_CHANGE_DECIMALS = 3
ROUND_WEIGHT_DECIMALS = 2
WEIGHT_PREDICTION_ALGORITHM_VERSION = "weight-v1.0.0"


def predict_weight_n_days(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    daily_steps: int,
    daily_intake_kcal: float,
    days: int,
) -> WeightPredictionStep:
    """N일 후 체중을 7-step 정적 근사로 예측한다.

    Args:
        weight_kg: 현재 체중(kg).
        height_cm: 키(cm).
        age: 만 나이.
        sex: "male" 또는 "female".
        daily_steps: 일일 걸음수.
        daily_intake_kcal: 일일 섭취 열량.
        days: 예측 기간(일).

    Returns:
        기간별 체중 예측 결과.

    Raises:
        ValueError: 예측 기간이 1일 미만인 경우.
    """
    if days < 1:
        raise ValueError("days must be greater than or equal to 1")

    estimated_bmr = calculate_bmr(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        sex=sex,
    )
    estimated_tdee = calculate_tdee(estimated_bmr=estimated_bmr, daily_steps=daily_steps)
    daily_balance = daily_intake_kcal - estimated_tdee
    cumulative_balance = daily_balance * days
    theoretical_change = cumulative_balance / KCAL_PER_KG_FAT

    if daily_balance < 0:
        corrected_change = theoretical_change * LOSS_CORRECTION
    elif daily_balance > 0:
        corrected_change = theoretical_change * GAIN_CORRECTION
    else:
        corrected_change = theoretical_change

    warning = (
        "90일 이상 예측은 대사 적응을 반영하는 동적 모델 검토가 필요합니다."
        if days >= LONG_TERM_WARNING_DAYS
        else None
    )

    return WeightPredictionStep(
        days=days,
        estimated_bmr=estimated_bmr,
        estimated_tdee=estimated_tdee,
        daily_balance_kcal=round(daily_balance, ROUND_KCAL_DECIMALS),
        cumulative_balance_kcal=round(cumulative_balance, ROUND_KCAL_DECIMALS),
        theoretical_change_kg=round(theoretical_change, ROUND_CHANGE_DECIMALS),
        corrected_change_kg=round(corrected_change, ROUND_CHANGE_DECIMALS),
        predicted_weight_kg=round(weight_kg + corrected_change, ROUND_WEIGHT_DECIMALS),
        warning=warning,
    )


def predict_weight_periods(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    daily_steps: int,
    daily_intake_kcal: float,
    periods_days: list[int],
) -> WeightPredictionResponse:
    """여러 기간에 대한 체중 예측을 일괄 계산한다.

    Args:
        weight_kg: 현재 체중(kg).
        height_cm: 키(cm).
        age: 만 나이.
        sex: "male" 또는 "female".
        daily_steps: 일일 걸음수.
        daily_intake_kcal: 일일 섭취 열량.
        periods_days: 예측 기간 목록.

    Returns:
        기간별 체중 예측 API 응답.

    Raises:
        ValueError: 예측 기간 중 1일 미만 값이 있는 경우.
    """
    predictions = [
        predict_weight_n_days(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            daily_steps=daily_steps,
            daily_intake_kcal=daily_intake_kcal,
            days=days,
        )
        for days in periods_days
    ]
    return WeightPredictionResponse(predictions=predictions)

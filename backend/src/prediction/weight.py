"""7-step 체중 예측 알고리즘.

회사 가이드의 7단계 산출식을 구현한다. 체지방 1kg당 7,700 kcal 환산을 기준으로
N일 후 체중을 예측하며, 감량/증량 시 현실 보정 계수를 적용한다.

Reference:
    docs/dev-guides/04-weight-prediction-7step.md
"""

from __future__ import annotations

from typing import Final

from src.algorithms.metabolism import calculate_bmr, calculate_tdee
from src.models.schemas.prediction import WeightPeriodPredictions, WeightPrediction

KCAL_PER_KG_FAT: Final[float] = 7700.0
"""체지방 1kg에 해당하는 에너지 (kcal)."""

LOSS_CORRECTION: Final[float] = 0.85
"""감량 시 현실 보정 계수 (체수분 손실·대사 적응 등 반영)."""

GAIN_CORRECTION: Final[float] = 0.95
"""증량 시 현실 보정 계수."""

STANDARD_PERIODS: Final[tuple[int, int, int]] = (7, 30, 90)
"""표준 예측 기간 (일): 1주, 1개월, 3개월."""

_MAX_PERIOD_DAYS: Final[int] = 365


def predict_weight_n_days(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    daily_steps: int,
    daily_intake_kcal: float,
    n_days: int,
) -> WeightPrediction:
    """N일 후 체중을 7-step 알고리즘으로 예측한다.

    Args:
        weight_kg: 시작 체중 (kg).
        height_cm: 키 (cm).
        age: 만 나이.
        sex: "male" | "female".
        daily_steps: 일일 평균 걸음수.
        daily_intake_kcal: 일일 평균 섭취 칼로리.
        n_days: 예측 기간 (일, 1~365).

    Returns:
        WeightPrediction — 7단계 중간 결과 + 최종 체중.

    Raises:
        ValueError: 입력값이 허용 범위를 벗어난 경우.

    Examples:
        >>> pred = predict_weight_n_days(
        ...     weight_kg=68.0, height_cm=160, age=50, sex="female",
        ...     daily_steps=6500, daily_intake_kcal=1500, n_days=30,
        ... )
        >>> pred.predicted_weight
        67.19
    """
    if not 1 <= n_days <= _MAX_PERIOD_DAYS:
        raise ValueError(f"n_days must be 1-{_MAX_PERIOD_DAYS}, got {n_days}")
    if daily_intake_kcal < 0:
        raise ValueError(f"daily_intake_kcal must be non-negative, got {daily_intake_kcal}")

    bmr = calculate_bmr(weight_kg, height_cm, age, sex)  # Step 1
    tdee = calculate_tdee(bmr, daily_steps)  # Step 2
    daily_balance = daily_intake_kcal - tdee  # Step 3
    cumulative = daily_balance * n_days  # Step 4
    theoretical = cumulative / KCAL_PER_KG_FAT  # Step 5
    if daily_balance < 0:  # Step 6
        corrected = theoretical * LOSS_CORRECTION
    elif daily_balance > 0:
        corrected = theoretical * GAIN_CORRECTION
    else:
        corrected = 0.0
    predicted = weight_kg + corrected  # Step 7

    return WeightPrediction(
        period_days=n_days,
        bmr=bmr,
        tdee=tdee,
        daily_balance=round(daily_balance, 1),
        cumulative_balance=round(cumulative, 1),
        theoretical_change=round(theoretical, 3),
        corrected_change=round(corrected, 3),
        starting_weight=weight_kg,
        predicted_weight=round(predicted, 2),
    )


def predict_weight_periods(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    daily_steps: int,
    daily_intake_kcal: float,
) -> WeightPeriodPredictions:
    """1주/1개월/3개월 일괄 예측.

    Args:
        weight_kg: 시작 체중 (kg).
        height_cm: 키 (cm).
        age: 만 나이.
        sex: "male" | "female".
        daily_steps: 일일 평균 걸음수.
        daily_intake_kcal: 일일 평균 섭취 칼로리.

    Returns:
        WeightPeriodPredictions — 1주/1개월/3개월 예측 묶음.

    Examples:
        >>> preds = predict_weight_periods(
        ...     weight_kg=68.0, height_cm=160, age=50, sex="female",
        ...     daily_steps=6500, daily_intake_kcal=1500,
        ... )
        >>> preds.month_1.predicted_weight
        67.19
    """
    week, month, quarter = (
        predict_weight_n_days(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            daily_steps=daily_steps,
            daily_intake_kcal=daily_intake_kcal,
            n_days=days,
        )
        for days in STANDARD_PERIODS
    )
    return WeightPeriodPredictions(week_1=week, month_1=month, month_3=quarter)

"""체중 예측 결과 스키마.

Reference:
    docs/dev-guides/04-weight-prediction-7step.md
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WeightPrediction(BaseModel):
    """N일 후 체중 예측 결과 (단일 기간).

    Attributes:
        period_days: 예측 기간 (일).
        bmr: 기초대사량 (kcal/일).
        tdee: 총 에너지 소비량 (kcal/일).
        daily_balance: 일일 에너지 수지 (kcal/일, 음수면 적자).
        cumulative_balance: N일 누적 수지 (kcal).
        theoretical_change: 이론 체중 변화 (kg, 보정 전).
        corrected_change: 보정된 체중 변화 (kg).
        starting_weight: 시작 체중 (kg).
        predicted_weight: 예측 체중 (kg).
    """

    model_config = ConfigDict(frozen=True)

    period_days: int = Field(..., ge=1, le=365)
    bmr: float
    tdee: float
    daily_balance: float
    cumulative_balance: float
    theoretical_change: float
    corrected_change: float
    starting_weight: float
    predicted_weight: float


class WeightPeriodPredictions(BaseModel):
    """표준 3 기간(1주/1개월/3개월) 일괄 예측.

    Attributes:
        week_1: 1주(7일) 후 예측.
        month_1: 1개월(30일) 후 예측.
        month_3: 3개월(90일) 후 예측.
    """

    model_config = ConfigDict(frozen=True)

    week_1: WeightPrediction
    month_1: WeightPrediction
    month_3: WeightPrediction

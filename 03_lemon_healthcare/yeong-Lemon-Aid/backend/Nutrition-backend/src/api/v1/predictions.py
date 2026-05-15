"""예측 API 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.v1.examples import (
    UNPROCESSABLE_ENTITY_EXAMPLE,
    WEIGHT_PREDICTION_REQUEST_EXAMPLES,
    WEIGHT_PREDICTION_RESPONSE_EXAMPLES,
)
from src.config import Settings, get_settings
from src.models.schemas.algorithm import WeightPredictionRequest, WeightPredictionResponse
from src.prediction.selector import predict_weight_periods_selected

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post(
    "/weight",
    response_model=WeightPredictionResponse,
    responses={
        200: {"content": {"application/json": {"examples": WEIGHT_PREDICTION_RESPONSE_EXAMPLES}}},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
)
async def predict_weight(
    request: Annotated[
        WeightPredictionRequest,
        Body(openapi_examples=WEIGHT_PREDICTION_REQUEST_EXAMPLES),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WeightPredictionResponse:
    """1주/1개월/3개월 등 기간별 체중 변화를 예측한다.

    Args:
        request: 체중 예측 요청.

    Returns:
        기간별 체중 예측 결과.
    """
    return predict_weight_periods_selected(
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        age=request.age,
        sex=request.sex,
        daily_steps=request.daily_steps,
        daily_intake_kcal=request.daily_intake_kcal,
        periods_days=request.periods_days,
        feature_hall_lite_weight_prediction=settings.feature_hall_lite_weight_prediction,
        weight_prediction_engine=settings.weight_prediction_engine,
    )

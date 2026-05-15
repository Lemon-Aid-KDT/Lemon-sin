"""활동점수 API 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body

from src.algorithms.activity import calculate_activity_score
from src.api.v1.examples import (
    ACTIVITY_SCORE_REQUEST_EXAMPLES,
    ACTIVITY_SCORE_RESPONSE_EXAMPLES,
    UNPROCESSABLE_ENTITY_EXAMPLE,
)
from src.models.schemas.algorithm import ActivityScoreRequest, ActivityScoreResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.post(
    "/score",
    response_model=ActivityScoreResponse,
    responses={
        200: {"content": {"application/json": {"examples": ACTIVITY_SCORE_RESPONSE_EXAMPLES}}},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
)
async def score_activity(
    request: Annotated[
        ActivityScoreRequest,
        Body(openapi_examples=ACTIVITY_SCORE_REQUEST_EXAMPLES),
    ],
) -> ActivityScoreResponse:
    """활동점수 v1-v4를 계산한다.

    Args:
        request: 활동점수 계산 요청.

    Returns:
        활동점수 계산 결과.
    """
    return calculate_activity_score(request)

"""통합 건강 요약 결과 스키마.

사용자 프로필 + 하루 섭취 영양소 + 활동 정보를 입력으로, 기업 과제 Output
(부족 영양소 추천 / 영양소 섭취량 권고 / 체중 변화 예측 / 활동 권고)을 담는
DTO를 정의한다. 사용자 노출 문구에는 의료적 단정 표현을 포함하지 않는다.

Reference:
    docs/dev-guides/04-weight-prediction-7step.md (체중 예측)
    docs/dev-guides/05·06 (KDRIs 대조)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.models.schemas.algorithm import BMICategory
from src.models.schemas.nutrition import NutrientStatus
from src.models.schemas.prediction import WeightPeriodPredictions


class NutrientContribution(BaseModel):
    """영양소별 기여도(충족률) + 부족 시 보충 권고.

    Attributes:
        code: 영양소 표준 코드.
        name_ko: 한국어 영양소명.
        intake_amount: 하루 섭취량 (표준 단위).
        reference_amount: 권장 기준값 (RDA 또는 AI). 없으면 None.
        unit: 표준 단위.
        fulfillment_pct: 기여도(충족률) — 권장 기준 대비 섭취 비율(%).
        status: 섭취 상태 분류.
        shortfall_amount: 권장까지 부족분 (충분/과잉/한도형이면 0).
        food_suggestion: 부족 시 보충 추천 식품 (그 외 빈 문자열).
        message_ko: 사용자 노출 문구 (의료적 단정 표현 제외).
    """

    model_config = ConfigDict(frozen=True)

    code: str
    name_ko: str
    intake_amount: float
    reference_amount: float | None
    unit: str
    fulfillment_pct: float = Field(..., ge=0)
    status: NutrientStatus
    shortfall_amount: float = Field(..., ge=0)
    food_suggestion: str
    message_ko: str


class ActivityAdvice(BaseModel):
    """활동(운동) 권고.

    Attributes:
        actual_steps: 실제 일일 걸음수.
        recommended_steps: 권장 걸음수 (성별·연령·BMI 보정).
        step_gap: 권장 대비 부족 걸음수 (이미 충족 시 0).
        v1_score: v1 활동점수 (0~100).
        message_ko: 사용자 노출 문구.
    """

    model_config = ConfigDict(frozen=True)

    actual_steps: int = Field(..., ge=0)
    recommended_steps: int = Field(..., ge=0)
    step_gap: int = Field(..., ge=0)
    v1_score: float = Field(..., ge=0, le=100)
    message_ko: str


class HealthSummary(BaseModel):
    """통합 건강 요약 (기업 과제 Output).

    Attributes:
        bmi: 체질량지수 (kg/m²).
        bmi_category: 한국·아시아 기준 BMI 분류.
        daily_intake_kcal: 하루 섭취 칼로리.
        nutrient_contributions: 영양소별 기여도(충족률) 전체.
        deficient_recommendations: 부족 영양소만 추린 보충 권고.
        weight_predictions: 1주/1개월/3개월 체중 변화 예측.
        activity: 활동(운동) 권고.
        summary_message_ko: 전체 요약 문구.
    """

    model_config = ConfigDict(frozen=True)

    bmi: float
    bmi_category: BMICategory
    daily_intake_kcal: float
    nutrient_contributions: list[NutrientContribution]
    deficient_recommendations: list[NutrientContribution]
    weight_predictions: WeightPeriodPredictions
    activity: ActivityAdvice
    summary_message_ko: str

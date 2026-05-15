"""핵심 산출식 알고리즘 요청/응답 스키마."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.models.schemas.user import Sex, UserProfile


class EvidenceLevel(StrEnum):
    """알고리즘 근거 수준.

    Attributes:
        A: 논문 또는 공식 기준에서 직접 확인되는 수식/기준값.
        B: 방향성 근거는 있으나 프로젝트 계수까지 직접 검증되지는 않은 값.
        C: 제품 UX 또는 팀 가정에 가까운 휴리스틱.
    """

    A = "A"
    B = "B"
    C = "C"


class BMICategory(StrEnum):
    """한국·아시아 사용자 대상 BMI 기준 분류."""

    UNDERWEIGHT = "underweight"
    NORMAL = "normal"
    OVERWEIGHT = "overweight"
    OBESE_1 = "obese_1"
    OBESE_2 = "obese_2"


HRMaxFormula = Literal["guide_220_age", "tanaka_2001"]
ActivityPeerScore = Annotated[float, Field(ge=0, le=100)]
PredictionPeriodDays = Annotated[int, Field(ge=1, le=365)]


class BMIResult(BaseModel):
    """BMI 계산 결과.

    Attributes:
        bmi: BMI 값(kg/m^2).
        category: 한국·아시아 기준 BMI 분류.
        evidence_level: 기준값 근거 수준.
        note: 사용자 노출 시 확정 표현을 피하기 위한 설명.
    """

    bmi: float
    category: BMICategory
    evidence_level: EvidenceLevel = EvidenceLevel.A
    note: str = "BMI 기준 분류이며 체성분이나 질환 상태를 확정하지 않습니다."


class TargetHeartRateRange(BaseModel):
    """목표 심박 구간.

    Attributes:
        low_bpm: 목표 심박 하한.
        high_bpm: 목표 심박 상한.
        formula: HRmax 계산식.
    """

    low_bpm: int
    high_bpm: int
    formula: HRMaxFormula


class ActivityScoreRequest(BaseModel):
    """활동점수 API 요청.

    Attributes:
        profile: 사용자 프로필.
        daily_steps: 일일 걸음수.
        target_hr_minutes: 목표 심박 구간 유지 시간. 웨어러블 없음이면 None.
        group_v2_scores: 동일 성별/연령대 비교군 v2 점수.
        hrmax_formula: HRmax 계산 방식.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "profile": {
                        "age": 50,
                        "sex": "female",
                        "height_cm": 160,
                        "weight_kg": 68,
                        "chronic_diseases": ["diabetes", "hypertension"],
                    },
                    "daily_steps": 7000,
                    "target_hr_minutes": 20,
                    "group_v2_scores": [60.0, 62.0, 64.0],
                    "hrmax_formula": "guide_220_age",
                }
            ]
        }
    )

    profile: UserProfile
    daily_steps: int = Field(ge=0)
    target_hr_minutes: float | None = Field(default=None, ge=0)
    group_v2_scores: list[ActivityPeerScore] = Field(default_factory=list, max_length=500)
    hrmax_formula: HRMaxFormula = "guide_220_age"


class ActivityScoreResponse(BaseModel):
    """활동점수 API 응답.

    Attributes:
        bmi: BMI 계산 결과.
        recommended_steps: 사용자별 권장 걸음수.
        target_hr_range: 목표 심박 구간.
        hr_factor: 심박 가중 계수.
        percentile_bonus: 비교군 백분위 보너스.
        disease_multiplier: 만성질환 프로젝트 가중치.
        v1_score: 기본 걸음수 점수.
        v2_score: 심박 가중 점수.
        v3_score: 백분위 보너스 반영 점수.
        v4_score: 만성질환 가중 반영 점수.
        note: 의료 확정 표현을 피하기 위한 안내.
    """

    bmi: BMIResult
    recommended_steps: int
    target_hr_range: TargetHeartRateRange
    hr_factor: float
    percentile_bonus: int
    disease_multiplier: float
    v1_score: float
    v2_score: float
    v3_score: float
    v4_score: float
    note: str = "활동점수는 건강 행동 참고 지표이며 질환 개선 효과를 의미하지 않습니다."


class WeightPredictionStep(BaseModel):
    """7-step 체중 예측 결과.

    Attributes:
        days: 예측 기간(일).
        estimated_bmr: 예상 BMR.
        estimated_tdee: 예상 TDEE.
        daily_balance_kcal: 일일 에너지 수지.
        cumulative_balance_kcal: 누적 에너지 수지.
        theoretical_change_kg: 7,700 kcal/kg 기준 이론 변화량.
        corrected_change_kg: 프로젝트 보정계수 적용 변화량.
        predicted_weight_kg: 예측 체중.
        warning: 장기 예측 한계 안내.
    """

    days: int
    estimated_bmr: float
    estimated_tdee: float
    daily_balance_kcal: float
    cumulative_balance_kcal: float
    theoretical_change_kg: float
    corrected_change_kg: float
    predicted_weight_kg: float
    warning: str | None = None


class WeightPredictionRequest(BaseModel):
    """체중 예측 API 요청.

    Attributes:
        age: 만 나이.
        sex: 생물학적 성별 기반 계산 입력.
        height_cm: 키(cm).
        weight_kg: 현재 체중(kg).
        daily_steps: 일일 걸음수.
        daily_intake_kcal: 일일 섭취 열량.
        periods_days: 예측 기간 목록.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "age": 50,
                    "sex": "female",
                    "height_cm": 160,
                    "weight_kg": 68,
                    "daily_steps": 6500,
                    "daily_intake_kcal": 1500,
                    "periods_days": [7, 30, 90],
                }
            ]
        }
    )

    age: int = Field(ge=1, le=120)
    sex: Sex
    height_cm: float = Field(ge=50, le=250)
    weight_kg: float = Field(ge=10, le=300)
    daily_steps: int = Field(ge=0)
    daily_intake_kcal: float = Field(ge=0)
    periods_days: list[PredictionPeriodDays] = Field(
        default_factory=lambda: [7, 30, 90],
        min_length=1,
        max_length=12,
    )


class WeightPredictionResponse(BaseModel):
    """체중 예측 API 응답.

    Attributes:
        predictions: 기간별 예측 결과.
        evidence_level: 7,700 kcal/kg 정적 근사와 프로젝트 보정계수의 근거 수준.
        note: 장기 예측 한계 안내.
    """

    predictions: list[WeightPredictionStep]
    evidence_level: EvidenceLevel = EvidenceLevel.B
    note: str = (
        "체중 예측은 단순 에너지 수지 기반 참고값이며 장기 대사 적응을 완전히 반영하지 않습니다."
    )

"""영양 분석 관련 스키마.

KDRIs(한국인 영양소 섭취기준) 룩업과 섭취량 대조 평가에 사용하는 Pydantic v2
모델을 정의한다. 본 모듈은 사용자에게 노출되는 표현에 의료적 단정(진단/처방/
치료/보장)을 포함하지 않는다.

Reference:
    docs/dev-guides/05-kdris-lookup.md
    docs/dev-guides/06-deficient-nutrient-diagnosis.md
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

_NUTRIENT_CODE_PATTERN = r"^[a-z_]+_[a-z]+$"
"""영양소 표준 코드 정규식. 예: ``vitamin_c_mg``, ``energy_kcal``."""


class NutrientStatus(StrEnum):
    """영양소 섭취 상태 분류.

    섭취량 ÷ 기준값(권장량 또는 충분섭취량) 비율에 따라 분류한다. 본 라벨은
    정보 제공 수준의 분류이며, 의료적 진단이 아니다.

    Reference:
        docs/dev-guides/06-deficient-nutrient-diagnosis.md §알고리즘 명세
    """

    DEFICIENT = "deficient"  # 35% 미만
    LOW = "low"  # 35~70%
    ADEQUATE = "adequate"  # 70~130%
    EXCESSIVE = "excessive"  # 130% 초과 (UL 이하)
    RISKY = "risky"  # UL(또는 과잉 경계) 초과


class KDRIsValue(BaseModel):
    """단일 영양소의 KDRIs 권장값.

    Attributes:
        code: 영양소 표준 코드.
        name_ko: 한국어 영양소명.
        name_en: 영어 영양소명.
        unit: 단위 (mg, ug, g, kcal 등).
        rda: 권장 섭취량 (있으면 기준값으로 우선).
        ai: 충분 섭취량 (RDA가 없을 때 기준값으로 사용).
        ear: 평균 필요량 (참고용, 비교에는 사용하지 않음).
        ul: 상한 섭취량. None이면 미설정.
    """

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., pattern=_NUTRIENT_CODE_PATTERN)
    name_ko: str = Field(..., min_length=1)
    name_en: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    rda: float | None = Field(default=None, ge=0)
    ai: float | None = Field(default=None, ge=0)
    ear: float | None = Field(default=None, ge=0)
    ul: float | None = Field(default=None, ge=0)

    @property
    def reference_value(self) -> float | None:
        """비교 기준값. RDA가 있으면 RDA, 없으면 AI.

        Returns:
            기준값. RDA·AI가 모두 없으면 None.
        """
        return self.rda if self.rda is not None else self.ai


class UserKDRIsContext(BaseModel):
    """KDRIs 룩업을 위한 사용자 컨텍스트.

    Attributes:
        age: 만 나이 (1~120).
        sex: 성별 ("male" | "female").
        is_pregnant: 임신부 여부 (여성에만 의미 있음).
        is_lactating: 수유부 여부 (여성에만 의미 있음).
    """

    model_config = ConfigDict(frozen=True)

    age: int = Field(..., ge=1, le=120)
    sex: str = Field(..., pattern=r"^(male|female)$")
    is_pregnant: bool = False
    is_lactating: bool = False


class NutrientEvaluation(BaseModel):
    """단일 영양소의 KDRIs 대조 평가 결과.

    Attributes:
        code: 영양소 표준 코드.
        name_ko: 한국어 영양소명.
        status: 섭취 상태 분류.
        intake_amount: 평가에 사용된 섭취량 (표준 단위).
        reference_amount: 비교 기준값 (RDA 또는 AI). 없으면 None.
        ratio_pct: 기준값 대비 비율 (%). 기준값이 없으면 0.0.
        unit: 표준 단위.
        upper_limit: 상한(또는 과잉 경계) 값. 없으면 None.
        message_ko: 사용자 노출 정보 문구 (의료적 단정 표현 제외).
    """

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., pattern=_NUTRIENT_CODE_PATTERN)
    name_ko: str = Field(..., min_length=1)
    status: NutrientStatus
    intake_amount: float = Field(..., ge=0)
    reference_amount: float | None = Field(default=None, ge=0)
    ratio_pct: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1)
    upper_limit: float | None = Field(default=None, ge=0)
    message_ko: str = Field(..., min_length=1)


class MealNutritionEvaluation(BaseModel):
    """섭취 영양소 묶음의 KDRIs 대조 평가 결과.

    음식 인식 → 영양소 조회로 얻은 섭취 영양소를 사용자별 KDRIs 권장 기준과
    대조한 결과를 담는다. 단발 식사에 적용하면 각 비율은 "하루 권장량 대비
    이 섭취의 비중"으로, 하루 합산 섭취에 적용하면 "부족/적정/과잉"의 토대로
    해석한다.

    Attributes:
        evaluations: 영양소별 평가 (상태 우선순위로 정렬됨).
        evaluated_count: 기준값이 있어 평가된 영양소 수.
        skipped_codes: KDRIs 기준이 없어 평가에서 제외된 입력 영양소 코드.
        summary_message_ko: 전체 요약 문구 (의료적 단정 표현 제외).
    """

    model_config = ConfigDict(frozen=True)

    evaluations: list[NutrientEvaluation] = Field(default_factory=list)
    evaluated_count: int = Field(..., ge=0)
    skipped_codes: list[str] = Field(default_factory=list)
    summary_message_ko: str = Field(..., min_length=1)

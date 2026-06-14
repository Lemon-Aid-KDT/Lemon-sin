"""사용자 프로필 공통 스키마."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Sex = Literal["male", "female"]
PregnancyStatus = Literal["none", "pregnant", "lactating"]
DiseaseCode = Annotated[str, Field(min_length=1, max_length=64)]


class UserProfile(BaseModel):
    """계산 알고리즘에 필요한 최소 사용자 프로필.

    Attributes:
        age: 만 나이.
        sex: 생물학적 성별 기반 계산 입력.
        height_cm: 키(cm).
        weight_kg: 체중(kg).
        pregnancy_status: KDRIs 룩업용 임신/수유 상태.
        chronic_diseases: 활동점수 v4 계산에 사용할 만성질환 코드 목록.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "age": 50,
                    "sex": "female",
                    "height_cm": 160,
                    "weight_kg": 68,
                    "pregnancy_status": "none",
                    "chronic_diseases": ["diabetes", "hypertension"],
                }
            ]
        }
    )

    age: int = Field(ge=1, le=120)
    sex: Sex
    height_cm: float = Field(gt=0, ge=50, le=250)
    weight_kg: float = Field(gt=0, ge=10, le=300)
    pregnancy_status: PregnancyStatus = "none"
    chronic_diseases: list[DiseaseCode] = Field(default_factory=list, max_length=10)

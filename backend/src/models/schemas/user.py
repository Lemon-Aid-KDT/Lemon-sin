"""사용자 프로필 스키마.

Reference:
    docs/dev-guides/01-bmi-and-v1-algorithm.md
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    """건강 분석을 위한 사용자 프로필 입력.

    Attributes:
        age: 만 나이 (1~120).
        sex: 성별 ("male" | "female").
        height_cm: 키 (cm, 50~250).
        weight_kg: 체중 (kg, 10~300).
        diseases: 만성질환 코드 리스트 (없으면 빈 리스트).
        is_smoker: 흡연자 여부 (목적별 분석에 사용).
    """

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    age: int = Field(..., ge=1, le=120, description="만 나이")
    sex: Literal["male", "female"] = Field(..., description="성별")
    height_cm: float = Field(..., ge=50, le=250, description="키 (cm)")
    weight_kg: float = Field(..., ge=10, le=300, description="체중 (kg)")
    diseases: list[str] = Field(default_factory=list, description="만성질환 코드")
    is_smoker: bool = Field(default=False, description="흡연자 여부")

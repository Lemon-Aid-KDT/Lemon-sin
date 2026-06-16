"""알고리즘 관련 공통 스키마.

Reference:
    docs/dev-guides/01-bmi-and-v1-algorithm.md
"""

from __future__ import annotations

from enum import StrEnum


class BMICategory(StrEnum):
    """BMI 분류 (한국·아시아 기준).

    Reference:
        CLAUDE.md Rule 8 (한국·아시아 BMI 기준)
    """

    UNDERWEIGHT = "underweight"  # < 18.5
    NORMAL = "normal"  # 18.5 ~ 22.9
    OVERWEIGHT = "overweight"  # 23.0 ~ 24.9
    OBESE_1 = "obese_1"  # 25.0 ~ 29.9
    OBESE_2 = "obese_2"  # >= 30.0

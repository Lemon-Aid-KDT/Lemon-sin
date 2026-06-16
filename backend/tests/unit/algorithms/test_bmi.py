"""BMI 계산·분류 단위 테스트 (한국·아시아 기준 + 회사 가이드 예시)."""

from __future__ import annotations

import pytest

from src.algorithms.bmi import calculate_bmi, classify_bmi
from src.models.schemas.algorithm import BMICategory


class TestCalculateBmi:
    """BMI 계산."""

    @pytest.mark.parametrize(
        ("weight", "height", "expected"),
        [
            (50.0, 170, 17.3),
            (60.0, 170, 20.8),
            (70.0, 170, 24.2),
            (80.0, 170, 27.7),
            (90.0, 170, 31.1),
        ],
    )
    def test_bmi_values(self, weight: float, height: float, expected: float) -> None:
        """대표 체중·키 조합의 BMI."""
        assert calculate_bmi(weight, height) == expected

    def test_50f_obese1_guide_example(self) -> None:
        """[가이드 예시] 50대 여성 160cm 68kg → BMI 26.6, OBESE_1."""
        bmi = calculate_bmi(68.0, 160)
        assert bmi == 26.6
        assert classify_bmi(bmi) is BMICategory.OBESE_1

    @pytest.mark.parametrize("weight", [-10.0, 5.0, 400.0])
    def test_invalid_weight_raises(self, weight: float) -> None:
        """체중 범위 밖은 ValueError."""
        with pytest.raises(ValueError):
            calculate_bmi(weight, 170)

    @pytest.mark.parametrize("height", [0.0, 30.0, 300.0])
    def test_invalid_height_raises(self, height: float) -> None:
        """키 범위 밖은 ValueError."""
        with pytest.raises(ValueError):
            calculate_bmi(70.0, height)


class TestClassifyBmi:
    """BMI 분류 (한국·아시아 경계)."""

    @pytest.mark.parametrize(
        ("bmi", "expected"),
        [
            (18.4, BMICategory.UNDERWEIGHT),
            (18.5, BMICategory.NORMAL),
            (22.9, BMICategory.NORMAL),
            (23.0, BMICategory.OVERWEIGHT),
            (24.9, BMICategory.OVERWEIGHT),
            (25.0, BMICategory.OBESE_1),
            (29.9, BMICategory.OBESE_1),
            (30.0, BMICategory.OBESE_2),
        ],
    )
    def test_boundaries(self, bmi: float, expected: BMICategory) -> None:
        """분류 경계값."""
        assert classify_bmi(bmi) is expected

    def test_non_positive_raises(self) -> None:
        """0 이하 BMI는 ValueError."""
        with pytest.raises(ValueError):
            classify_bmi(0.0)

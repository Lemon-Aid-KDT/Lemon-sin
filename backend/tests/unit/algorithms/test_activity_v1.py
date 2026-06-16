"""v1 활동점수 단위 테스트 (회사 가이드 예시 포함)."""

from __future__ import annotations

import pytest

from src.algorithms.activity import (
    calculate_recommended_steps,
    calculate_v1_score,
    get_age_factor,
)
from src.models.schemas.algorithm import BMICategory


class TestAgeFactor:
    """연령 계수."""

    @pytest.mark.parametrize(
        ("age", "expected"),
        [(20, 1.0), (39, 1.0), (40, 0.9), (50, 0.9), (59, 0.9), (60, 0.8), (75, 0.8)],
    )
    def test_age_factor(self, age: int, expected: float) -> None:
        """연령 구간별 계수."""
        assert get_age_factor(age) == expected

    @pytest.mark.parametrize("age", [0, 121])
    def test_invalid_age_raises(self, age: int) -> None:
        """범위 밖 나이는 ValueError."""
        with pytest.raises(ValueError):
            get_age_factor(age)


class TestRecommendedSteps:
    """권장 걸음수."""

    def test_50f_obese1_guide_example(self) -> None:
        """[가이드 예시] 50대 여성 비만1단계 → 7,524보."""
        assert calculate_recommended_steps("female", 50, BMICategory.OBESE_1) == 7524

    @pytest.mark.parametrize(
        ("sex", "age", "expected"),
        [("male", 30, 8000), ("female", 30, 7600), ("male", 50, 7200), ("male", 65, 6400)],
    )
    def test_normal_bmi_factors(self, sex: str, age: int, expected: int) -> None:
        """정상 BMI에서 성별·연령 계수 곱."""
        assert calculate_recommended_steps(sex, age, BMICategory.NORMAL) == expected

    def test_invalid_sex_raises(self) -> None:
        """잘못된 성별은 ValueError."""
        with pytest.raises(ValueError):
            calculate_recommended_steps("other", 30, BMICategory.NORMAL)


class TestV1Score:
    """v1 기본점수."""

    def test_50f_obese1_7000_guide_example(self) -> None:
        """[가이드 예시] 7000 / 7524 → 약 77.5점."""
        assert calculate_v1_score(7000, 7524) == pytest.approx(77.5, abs=0.1)

    def test_at_recommended_is_about_8333(self) -> None:
        """권장 달성 시 약 83.33점."""
        assert calculate_v1_score(7524, 7524) == pytest.approx(83.33, abs=0.1)

    def test_120_pct_caps_at_100(self) -> None:
        """달성률 120%에서 100점."""
        assert calculate_v1_score(9029, 7524) == pytest.approx(100.0, abs=0.1)

    def test_above_cap_remains_100(self) -> None:
        """200%여도 캡으로 100점."""
        assert calculate_v1_score(15048, 7524) == pytest.approx(100.0, abs=0.1)

    def test_zero_steps_is_zero(self) -> None:
        """0보는 0점."""
        assert calculate_v1_score(0, 7524) == 0.0

    def test_non_positive_recommended_raises(self) -> None:
        """권장 걸음수 0 이하는 ValueError."""
        with pytest.raises(ValueError):
            calculate_v1_score(5000, 0)

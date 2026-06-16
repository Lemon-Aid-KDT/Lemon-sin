"""BMR·활동계수·TDEE 단위 테스트 (회사 가이드 예시 포함)."""

from __future__ import annotations

import pytest

from src.algorithms.metabolism import (
    calculate_bmr,
    calculate_tdee,
    get_activity_factor,
)


class TestBmr:
    """기초대사량 (Mifflin-St Jeor)."""

    def test_50f_guide_example(self) -> None:
        """[가이드 예시] 68kg 160cm 50세 여성 → 1,269.0."""
        assert calculate_bmr(68.0, 160, 50, "female") == 1269.0

    def test_45m_guide_example(self) -> None:
        """[가이드 예시] 82kg 175cm 45세 남성 → 1,694.0."""
        assert calculate_bmr(82.0, 175, 45, "male") == 1694.0

    def test_male_female_constant_diff(self) -> None:
        """동일 신체에서 남녀 차이는 상수항 차(166)."""
        male = calculate_bmr(70.0, 170, 30, "male")
        female = calculate_bmr(70.0, 170, 30, "female")
        assert male - female == 166.0

    def test_invalid_sex_raises(self) -> None:
        """잘못된 성별은 ValueError."""
        with pytest.raises(ValueError):
            calculate_bmr(70.0, 170, 30, "other")

    @pytest.mark.parametrize(("weight", "age"), [(5.0, 30), (70.0, 0)])
    def test_invalid_range_raises(self, weight: float, age: int) -> None:
        """체중·나이 범위 밖은 ValueError."""
        with pytest.raises(ValueError):
            calculate_bmr(weight, 170, age, "male")


class TestActivityFactor:
    """걸음수 기반 활동계수."""

    @pytest.mark.parametrize(
        ("steps", "expected"),
        [
            (0, 1.2),
            (4999, 1.2),
            (5000, 1.375),
            (7499, 1.375),
            (7500, 1.55),
            (9999, 1.55),
            (10000, 1.725),
            (12499, 1.725),
            (12500, 1.9),
            (20000, 1.9),
        ],
    )
    def test_boundaries(self, steps: int, expected: float) -> None:
        """활동계수 경계값."""
        assert get_activity_factor(steps) == expected

    def test_negative_raises(self) -> None:
        """음수 걸음수는 ValueError."""
        with pytest.raises(ValueError):
            get_activity_factor(-1)


class TestTdee:
    """총에너지소비량."""

    def test_50f_guide_example(self) -> None:
        """[가이드 예시] BMR 1269 x 1.375 = 약 1,745."""
        assert calculate_tdee(1269.0, 6500) == pytest.approx(1745.0, abs=0.5)

    def test_45m_guide_example(self) -> None:
        """[가이드 예시] BMR 1694 x 1.55 = 약 2,625."""
        assert calculate_tdee(1694.0, 8000) == pytest.approx(2625.0, abs=1.0)

    def test_zero_steps_uses_sedentary(self) -> None:
        """0보는 좌식 계수 1.2."""
        assert calculate_tdee(1500.0, 0) == 1800.0

    def test_negative_bmr_raises(self) -> None:
        """음수 BMR은 ValueError."""
        with pytest.raises(ValueError):
            calculate_tdee(-100.0, 5000)

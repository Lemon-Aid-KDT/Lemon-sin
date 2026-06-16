"""7-step 체중 예측 단위 테스트 (회사 가이드 예시 포함)."""

from __future__ import annotations

import pytest

from src.prediction.weight import (
    GAIN_CORRECTION,
    predict_weight_n_days,
    predict_weight_periods,
)


class TestPredictNDays:
    """단일 기간 예측."""

    def test_50f_30days_guide_example(self) -> None:
        """[가이드 예시 1] 50대 여성 30일 → 67.19kg (감량)."""
        pred = predict_weight_n_days(
            weight_kg=68.0,
            height_cm=160,
            age=50,
            sex="female",
            daily_steps=6500,
            daily_intake_kcal=1500,
            n_days=30,
        )
        assert pred.bmr == 1269.0
        assert pred.tdee == pytest.approx(1745.0, abs=0.5)
        assert pred.daily_balance < 0
        assert pred.predicted_weight == pytest.approx(67.19, abs=0.05)

    def test_45m_60days_guide_example(self) -> None:
        """[가이드 예시 2] 45세 남성 60일 → 79.39kg (감량)."""
        pred = predict_weight_n_days(
            weight_kg=82.0,
            height_cm=175,
            age=45,
            sex="male",
            daily_steps=8000,
            daily_intake_kcal=2231,
            n_days=60,
        )
        assert pred.bmr == 1694.0
        assert pred.predicted_weight == pytest.approx(79.39, abs=0.1)

    def test_maintenance_no_change(self) -> None:
        """섭취 = TDEE면 체중 변화 없음."""
        pred = predict_weight_n_days(
            weight_kg=70.0,
            height_cm=170,
            age=40,
            sex="male",
            daily_steps=8000,
            daily_intake_kcal=0,
            n_days=30,
        )
        balanced = predict_weight_n_days(
            weight_kg=70.0,
            height_cm=170,
            age=40,
            sex="male",
            daily_steps=8000,
            daily_intake_kcal=pred.tdee,
            n_days=30,
        )
        assert balanced.corrected_change == 0.0
        assert balanced.predicted_weight == 70.0

    def test_gain_uses_095_correction(self) -> None:
        """증량 시 0.95 보정 계수."""
        pred = predict_weight_n_days(
            weight_kg=60.0,
            height_cm=170,
            age=30,
            sex="male",
            daily_steps=3000,
            daily_intake_kcal=4000,
            n_days=10,
        )
        assert pred.daily_balance > 0
        assert pred.corrected_change == pytest.approx(
            pred.theoretical_change * GAIN_CORRECTION, abs=0.001
        )

    @pytest.mark.parametrize("n_days", [0, 366])
    def test_invalid_n_days_raises(self, n_days: int) -> None:
        """예측 기간 범위 밖은 ValueError."""
        with pytest.raises(ValueError):
            predict_weight_n_days(70.0, 170, 30, "male", 8000, 2000, n_days)

    def test_negative_intake_raises(self) -> None:
        """음수 섭취 칼로리는 ValueError."""
        with pytest.raises(ValueError):
            predict_weight_n_days(70.0, 170, 30, "male", 8000, -100, 30)


class TestPredictPeriods:
    """1주/1개월/3개월 일괄 예측."""

    def test_periods_present_and_ordered(self) -> None:
        """감량 시 기간이 길수록 체중 더 감소, period_days 7/30/90."""
        preds = predict_weight_periods(
            weight_kg=68.0,
            height_cm=160,
            age=50,
            sex="female",
            daily_steps=6500,
            daily_intake_kcal=1500,
        )
        assert preds.week_1.period_days == 7
        assert preds.month_1.period_days == 30
        assert preds.month_3.period_days == 90
        assert preds.month_3.predicted_weight < preds.month_1.predicted_weight
        assert preds.month_1.predicted_weight < preds.week_1.predicted_weight

    def test_month_1_matches_guide(self) -> None:
        """[가이드 예시] 1개월 예측은 67.19kg."""
        preds = predict_weight_periods(
            weight_kg=68.0,
            height_cm=160,
            age=50,
            sex="female",
            daily_steps=6500,
            daily_intake_kcal=1500,
        )
        assert preds.month_1.predicted_weight == pytest.approx(67.19, abs=0.05)

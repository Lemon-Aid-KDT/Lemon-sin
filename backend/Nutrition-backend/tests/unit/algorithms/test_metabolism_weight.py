"""BMR/TDEE와 체중 예측 테스트."""

from __future__ import annotations

import pytest
from src.algorithms.metabolism import (
    calculate_bmr,
    calculate_exercise_kcal_from_mets,
    calculate_katch_mcardle_bmr,
    calculate_tdee,
    get_activity_factor,
)
from src.prediction.weight import predict_weight_n_days, predict_weight_periods


def test_bmr_50f_example() -> None:
    """50세 여성 160cm 68kg BMR 예시를 재현한다."""
    bmr = calculate_bmr(weight_kg=68.0, height_cm=160, age=50, sex="female")

    assert bmr == 1269.0


def test_bmr_45m_example() -> None:
    """45세 남성 175cm 82kg BMR 예시를 재현한다."""
    bmr = calculate_bmr(weight_kg=82.0, height_cm=175, age=45, sex="male")

    assert bmr == 1694.0


def test_bmr_male_female_constant_difference() -> None:
    """동일 체격에서 남녀 BMR 상수 차이는 166kcal이다."""
    male_bmr = calculate_bmr(weight_kg=70.0, height_cm=170, age=30, sex="male")
    female_bmr = calculate_bmr(weight_kg=70.0, height_cm=170, age=30, sex="female")

    assert male_bmr - female_bmr == 166.0


def test_katch_mcardle_bmr_used_when_body_fat_is_available() -> None:
    """체지방률이 유효하면 제지방량 기반 BMR을 계산한다."""
    assert calculate_katch_mcardle_bmr(weight_kg=68.0, body_fat_pct=30.0) == 1398.0
    assert (
        calculate_bmr(
            weight_kg=68.0,
            height_cm=160,
            age=50,
            sex="female",
            body_fat_pct=30.0,
        )
        == 1398.0
    )


@pytest.mark.parametrize(
    ("steps", "expected_factor"),
    [
        (3000, 1.200),
        (6500, 1.375),
        (8000, 1.550),
        (11000, 1.725),
        (15000, 1.900),
        (4999, 1.200),
        (5000, 1.375),
        (12500, 1.900),
    ],
)
def test_activity_factor_boundaries(steps: int, expected_factor: float) -> None:
    """걸음수 기반 활동계수 경계값을 검증한다."""
    assert get_activity_factor(steps) == expected_factor


def test_tdee_50f_example() -> None:
    """BMR 1269와 6500보 활동계수로 TDEE 예시를 재현한다."""
    tdee = calculate_tdee(estimated_bmr=1269.0, daily_steps=6500)

    assert tdee == pytest.approx(1745.0, abs=0.5)


def test_tdee_adds_mets_based_intentional_exercise() -> None:
    """METs와 운동 분 입력이 있으면 의도 운동 열량을 TDEE에 더한다."""
    exercise_kcal = calculate_exercise_kcal_from_mets(mets=7.0, weight_kg=50.0, minutes=30.0)

    assert exercise_kcal == pytest.approx(183.75, abs=0.01)
    assert calculate_tdee(
        estimated_bmr=1269.0,
        daily_steps=6500,
        weight_kg=50.0,
        intentional_exercises=[(7.0, 30.0)],
    ) == pytest.approx(1929.0, abs=0.5)


def test_weight_prediction_50f_30days() -> None:
    """50세 여성 30일 체중 예측 예시를 검증한다."""
    prediction = predict_weight_n_days(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        days=30,
    )

    assert prediction.estimated_bmr == 1269.0
    assert prediction.estimated_tdee == pytest.approx(1745.0, abs=0.5)
    assert prediction.daily_balance_kcal == pytest.approx(-245, abs=0.5)
    assert prediction.cumulative_balance_kcal == pytest.approx(-7350, abs=2)
    assert prediction.theoretical_change_kg == pytest.approx(-0.955, abs=0.01)
    assert prediction.corrected_change_kg == pytest.approx(-1.123, abs=0.01)
    assert prediction.predicted_weight_kg == pytest.approx(66.88, abs=0.05)
    assert prediction.expected_weight_range_kg == pytest.approx((66.77, 66.99), abs=0.01)


def test_weight_prediction_periods_includes_long_term_warning() -> None:
    """90일 예측에는 장기 예측 한계 경고를 포함한다."""
    response = predict_weight_periods(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        periods_days=[7, 30, 90],
    )

    assert [prediction.days for prediction in response.predictions] == [7, 30, 90]
    assert response.predictions[-1].warning is not None
    assert response.predictions[-1].confidence == "low"


def test_weight_prediction_alcohol_kcal_uses_storage_factor() -> None:
    """별도 알코올 kcal은 지방 저장 보정 계수를 적용해 balance에 반영한다."""
    prediction = predict_weight_n_days(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        alcohol_kcal=100,
        days=7,
    )

    assert prediction.daily_balance_kcal == pytest.approx(-115, abs=0.5)
    assert prediction.corrected_change_kg == pytest.approx(-0.19, abs=0.01)


def test_weight_prediction_disables_high_risk_conditions() -> None:
    """갑상선·CKD 등 고위험 조건에서는 자동 체중 예측을 보류한다."""
    response = predict_weight_periods(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        periods_days=[7, 30],
        chronic_diseases=["hyperthyroidism"],
    )

    assert response.prediction_status == "disabled"
    assert response.predictions == []
    assert response.safety_warnings

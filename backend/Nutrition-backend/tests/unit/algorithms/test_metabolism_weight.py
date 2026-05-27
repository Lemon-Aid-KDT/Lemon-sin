"""BMR/TDEE와 체중 예측 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.algorithms.metabolism import (
    calculate_bmr,
    calculate_cunningham_bmr,
    calculate_exercise_kcal_from_activity,
    calculate_exercise_kcal_from_mets,
    calculate_exercise_kcal_from_walking_cadence,
    calculate_katch_mcardle_bmr,
    calculate_lean_body_mass_from_body_fat,
    calculate_tdee,
    calculate_tdee_with_activity_codes,
    get_activity_factor,
    lookup_exercise_activity_mets,
    lookup_walking_cadence_mets,
)
from src.models.schemas.algorithm import WeightPredictionRequest
from src.prediction.weight import (
    calculate_alcohol_kcal_from_volume,
    predict_weight_n_days,
    predict_weight_periods,
)


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


def test_cunningham_bmr_matches_body_fat_based_lbm_path() -> None:
    """Cunningham 1991 제지방량 공식은 체지방률 기반 BMR 경로와 같은 값을 낸다."""
    lean_body_mass = calculate_lean_body_mass_from_body_fat(weight_kg=68.0, body_fat_pct=30.0)

    assert lean_body_mass == pytest.approx(47.6, abs=0.01)
    assert calculate_cunningham_bmr(lean_body_mass_kg=lean_body_mass) == 1398.0
    assert calculate_cunningham_bmr(
        lean_body_mass_kg=lean_body_mass
    ) == calculate_katch_mcardle_bmr(
        weight_kg=68.0,
        body_fat_pct=30.0,
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


@pytest.mark.parametrize(
    ("cadence_steps_per_min", "expected_mets"),
    [
        (0.0, 0.0),
        (80.0, 2.0),
        (100.0, 3.0),
        (110.0, 4.0),
        (120.0, 5.0),
        (130.0, 6.0),
    ],
)
def test_walking_cadence_lookup_uses_tudor_locke_thresholds(
    cadence_steps_per_min: float,
    expected_mets: float,
) -> None:
    """보행 cadence를 Tudor-Locke 2018 휴리스틱 METs 구간으로 매핑한다."""
    assert lookup_walking_cadence_mets(cadence_steps_per_min) == expected_mets


def test_tdee_adds_walking_cadence_based_exercise() -> None:
    """보행 cadence와 시간이 있으면 wearable 기반 보행 열량을 TDEE에 더한다."""
    cadence_kcal = calculate_exercise_kcal_from_walking_cadence(
        cadence_steps_per_min=120.0,
        weight_kg=50.0,
        minutes=30.0,
    )

    assert cadence_kcal == pytest.approx(131.25, abs=0.01)
    assert calculate_tdee(
        estimated_bmr=1269.0,
        daily_steps=6500,
        weight_kg=50.0,
        walking_cadence_steps_per_min=120.0,
        walking_cadence_minutes=30.0,
    ) == pytest.approx(1876.0, abs=0.5)


@pytest.mark.parametrize(
    ("activity_code", "expected_mets"),
    [
        ("walking_moderate", 3.5),
        ("walking_very_brisk", 5.0),
        ("jogging_general", 7.0),
        ("running_6mph", 9.8),
        ("cycling_commute_self_selected", 6.8),
        ("resistance_training_squats", 5.0),
        ("yoga_hatha", 2.5),
    ],
)
def test_exercise_activity_lookup_uses_compendium_values(
    activity_code: str,
    expected_mets: float,
) -> None:
    """지원 운동 코드를 Compendium 2011 METs 값으로 매핑한다."""
    assert lookup_exercise_activity_mets(activity_code) == expected_mets  # type: ignore[arg-type]


def test_tdee_adds_activity_code_based_intentional_exercise() -> None:
    """운동 코드와 시간을 입력하면 METs 변환 후 TDEE에 더한다."""
    activity_kcal = calculate_exercise_kcal_from_activity(
        activity_code="jogging_general",
        weight_kg=50.0,
        minutes=30.0,
    )

    assert activity_kcal == pytest.approx(183.75, abs=0.01)
    assert calculate_tdee_with_activity_codes(
        estimated_bmr=1269.0,
        daily_steps=6500,
        weight_kg=50.0,
        intentional_activities=[("jogging_general", 30.0)],
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


def test_weight_prediction_walking_cadence_increases_tdee() -> None:
    """보행 cadence 입력은 예측 TDEE에 wearable 기반 운동 열량을 반영한다."""
    baseline = predict_weight_n_days(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        days=7,
    )
    with_cadence = predict_weight_n_days(
        weight_kg=68.0,
        height_cm=160,
        age=50,
        sex="female",
        daily_steps=6500,
        daily_intake_kcal=1500,
        walking_cadence_steps_per_min=120.0,
        walking_cadence_minutes=30.0,
        days=7,
    )

    assert with_cadence.estimated_tdee > baseline.estimated_tdee
    assert with_cadence.estimated_tdee - baseline.estimated_tdee == pytest.approx(
        178.0,
        abs=0.5,
    )


def test_alcohol_kcal_conversion_uses_volume_and_abv() -> None:
    """주류 용량과 ABV로 알코올 유래 kcal을 계산한다."""
    assert calculate_alcohol_kcal_from_volume(volume_ml=500, abv_percent=5) == pytest.approx(
        138.1,
        abs=0.1,
    )


def test_weight_prediction_request_requires_abv_when_alcohol_volume_is_set() -> None:
    """주류 용량이 있으면 ABV도 함께 입력해야 자동 kcal 산입이 가능하다."""
    with pytest.raises(ValidationError, match="alcohol_abv_percent is required"):
        WeightPredictionRequest(
            age=50,
            sex="female",
            height_cm=160,
            weight_kg=68,
            daily_steps=6500,
            daily_intake_kcal=1500,
            alcohol_volume_ml=360,
        )


def test_weight_prediction_request_requires_cadence_and_minutes_pair() -> None:
    """보행 cadence와 시간은 함께 입력해야 wearable 보정에 사용할 수 있다."""
    with pytest.raises(ValidationError, match="walking_cadence_steps_per_min is required"):
        WeightPredictionRequest(
            age=50,
            sex="female",
            height_cm=160,
            weight_kg=68,
            daily_steps=6500,
            daily_intake_kcal=1500,
            walking_cadence_minutes=30,
        )

    with pytest.raises(ValidationError, match="walking_cadence_minutes must be positive"):
        WeightPredictionRequest(
            age=50,
            sex="female",
            height_cm=160,
            weight_kg=68,
            daily_steps=6500,
            daily_intake_kcal=1500,
            walking_cadence_steps_per_min=120,
        )


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

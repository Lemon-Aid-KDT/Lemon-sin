"""Request size and value limit tests."""

from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from src.main import create_app


def test_activity_rejects_too_many_peer_scores() -> None:
    """Verify activity score requests cap peer score payload size."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/activity/score",
        json={
            "profile": {"age": 50, "sex": "female", "height_cm": 160, "weight_kg": 68},
            "daily_steps": 7000,
            "group_v2_scores": [50.0] * 501,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_activity_rejects_too_many_chronic_disease_codes() -> None:
    """Verify profile disease-code list size is bounded."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/activity/score",
        json={
            "profile": {
                "age": 50,
                "sex": "female",
                "height_cm": 160,
                "weight_kg": 68,
                "chronic_diseases": [f"condition_{index}" for index in range(11)],
            },
            "daily_steps": 7000,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_weight_prediction_rejects_period_over_one_year() -> None:
    """Verify prediction periods are capped at one year."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/predictions/weight",
        json={
            "age": 50,
            "sex": "female",
            "height_cm": 160,
            "weight_kg": 68,
            "daily_steps": 6500,
            "daily_intake_kcal": 1500,
            "periods_days": [366],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_weight_prediction_rejects_too_many_periods() -> None:
    """Verify period list size is bounded."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/predictions/weight",
        json={
            "age": 50,
            "sex": "female",
            "height_cm": 160,
            "weight_kg": 68,
            "daily_steps": 6500,
            "daily_intake_kcal": 1500,
            "periods_days": list(range(1, 14)),
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_nutrition_analysis_rejects_too_many_intakes() -> None:
    """Verify nutrition analysis caps intake list size."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/nutrition/analyze",
        json={
            "profile": {"age": 30, "sex": "male", "height_cm": 170, "weight_kg": 70},
            "intakes": [
                {"nutrient_code": "vitamin_c_mg", "amount": 30, "unit": "mg"} for _ in range(101)
            ],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_nutrition_analysis_rejects_long_code_and_unit() -> None:
    """Verify nutrient code and unit string lengths are bounded."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/nutrition/analyze",
        json={
            "profile": {"age": 30, "sex": "male", "height_cm": 170, "weight_kg": 70},
            "intakes": [
                {
                    "nutrient_code": "x" * 65,
                    "amount": 30,
                    "unit": "milligrams_per_day",
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

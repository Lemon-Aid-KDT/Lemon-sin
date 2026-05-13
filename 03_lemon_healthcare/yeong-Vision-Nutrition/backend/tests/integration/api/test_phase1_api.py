"""Phase 1 기본 API 통합 테스트."""

from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from src.config import Settings, get_settings
from src.main import create_app
from src.prediction.selector import HALL_LITE_WARNING


def test_activity_score_api() -> None:
    """활동점수 API가 v1-v4 결과를 반환하는지 검증한다."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/activity/score",
        json={
            "profile": {
                "age": 50,
                "sex": "female",
                "height_cm": 160,
                "weight_kg": 68,
                "chronic_diseases": ["diabetes", "hypertension"],
            },
            "daily_steps": 7000,
            "target_hr_minutes": 20,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["bmi"]["category"] == "obese_1"
    assert body["recommended_steps"] == 7524
    assert body["v4_score"] > body["v3_score"]


def test_weight_prediction_api() -> None:
    """체중 예측 API가 기본 기간별 결과를 반환하는지 검증한다."""
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
            "periods_days": [7, 30, 90],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [prediction["days"] for prediction in body["predictions"]] == [7, 30, 90]
    assert body["predictions"][1]["predicted_weight_kg"] == 67.19


def test_weight_prediction_api_can_route_hall_lite_when_enabled() -> None:
    """체중 예측 API가 설정 주입 시 Hall-lite selector를 통과하는지 검증한다."""

    def hall_lite_settings() -> Settings:
        """Return Hall-lite enabled settings for dependency override.

        Returns:
            Settings configured to enable auto Hall-lite selection.
        """
        return Settings(
            feature_hall_lite_weight_prediction=True,
            weight_prediction_engine="auto",
        )

    app = create_app()
    app.dependency_overrides[get_settings] = hall_lite_settings
    client = TestClient(app)

    response = client.post(
        "/api/v1/predictions/weight",
        json={
            "age": 50,
            "sex": "female",
            "height_cm": 160,
            "weight_kg": 68,
            "daily_steps": 6500,
            "daily_intake_kcal": 1500,
            "periods_days": [30, 90],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["predictions"][0]["predicted_weight_kg"] == 67.19
    assert body["predictions"][1]["warning"] == HALL_LITE_WARNING


def test_kdris_lookup_api() -> None:
    """KDRIs 샘플 룩업 API가 30종 기준값을 반환하는지 검증한다."""
    client = TestClient(create_app())

    response = client.get("/api/v1/nutrition/kdris?age=30&sex=male")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["query"]["age"] == 30
    assert len(body["references"]) == 30
    assert body["dataset_version"] == "2020-sample"
    assert body["source_manifest_version"] == "2.0"


def test_nutrition_analysis_api() -> None:
    """영양 분석 API가 부족 가능성과 UL 초과 가능성을 반환하는지 검증한다."""
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/nutrition/analyze",
        json={
            "profile": {
                "age": 30,
                "sex": "male",
                "height_cm": 170,
                "weight_kg": 70,
            },
            "intakes": [
                {"nutrient_code": "vitamin_c_mg", "amount": 30, "unit": "mg"},
                {"nutrient_code": "vitamin_a_ug", "amount": 5000, "unit": "ug"},
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    statuses = {result["nutrient_code"]: result["status"] for result in body["results"]}
    assert statuses["vitamin_c_mg"] == "deficient"
    assert statuses["vitamin_a_ug"] == "risky"
    assert body["dataset_version"] == "2020-sample"
    assert body["source_manifest_version"] == "2.0"

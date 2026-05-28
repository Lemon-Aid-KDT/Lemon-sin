"""헬스 체크 엔드포인트 테스트."""

from __future__ import annotations

from fastapi.testclient import TestClient
from src.config import Settings
from src.main import create_app

HTTP_OK = 200


def test_health_check_returns_ok() -> None:
    """`/health`가 서비스 상태와 버전을 반환하는지 검증한다."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == HTTP_OK
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_readiness_check_returns_sanitized_ocr_status() -> None:
    """Verify `/ready` exposes OCR/parser flags without secrets or payloads."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="clova",
        allow_external_ocr=True,
        enable_clova_ocr=True,
        clova_ocr_api_url="https://example.test/ocr",
        clova_ocr_secret="placeholder-value",  # pragma: allowlist secret
        google_vision_auth_mode="api_key",
        google_cloud_api_key="placeholder-key",  # pragma: allowlist secret
        allow_google_api_key_auth=True,
        enable_food_yolo_detector=True,
        meal_yolo_model_path="/app/runs/food_yolo/example/weights/best.pt",
        meal_yolo_model_label="food_yolo_local",
        meal_yolo_min_confidence=0.35,
        meal_yolo_max_detections=12,
        enable_multimodal_llm=True,
        multimodal_ocr_assist_policy="ocr_empty_only",
    )
    client = TestClient(create_app(settings=settings))

    response = client.get("/ready")

    assert response.status_code == HTTP_OK
    body = response.json()
    assert body["status"] == "ok"
    assert body["ocr"]["primary_provider"] == "clova"
    assert body["ocr"]["live_provider_auth_checked"] is False
    assert body["vision"]["classifier_enabled"] is False
    assert body["vision"]["food_yolo_enabled"] is True
    assert body["vision"]["food_yolo_model_configured"] is True
    assert body["vision"]["food_yolo_model_label"] == "food_yolo_local"
    assert body["vision"]["food_yolo_min_confidence"] == 0.35
    assert body["vision"]["food_yolo_max_detections"] == 12
    assert body["vision"]["multimodal_llm_enabled"] is True
    assert body["vision"]["multimodal_ocr_assist_policy"] == "ocr_empty_only"
    assert body["parser"]["live_model_checked"] is False
    provider_rows = {row["selector"]: row for row in body["ocr"]["providers"]}
    assert provider_rows["configured"]["provider_label"] == "clova_ocr"
    assert provider_rows["configured"]["status"] == "degraded"
    assert provider_rows["configured"]["status_reason"] == "live_auth_not_checked"
    assert provider_rows["paddleocr"]["provider_label"] == "paddleocr_local"
    assert provider_rows["paddleocr"]["status"] == "ready"
    assert provider_rows["paddleocr"]["status_reason"] is None
    assert provider_rows["google_vision"]["provider_label"] == "google_vision_document"
    assert provider_rows["google_vision"]["status"] == "degraded"
    assert provider_rows["google_vision"]["status_reason"] == "live_auth_not_checked"
    assert provider_rows["clova"]["provider_label"] == "clova_ocr"
    assert provider_rows["clova"]["status"] == "degraded"
    assert provider_rows["clova"]["status_reason"] == "live_auth_not_checked"
    response_text = response.text
    assert "placeholder-value" not in response_text
    assert "placeholder-key" not in response_text
    assert "example.test" not in response_text
    assert "/app/runs/food_yolo/example/weights/best.pt" not in response_text

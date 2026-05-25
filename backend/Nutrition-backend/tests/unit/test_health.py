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
    )
    client = TestClient(create_app(settings=settings))

    response = client.get("/ready")

    assert response.status_code == HTTP_OK
    body = response.json()
    assert body["status"] == "ok"
    assert body["ocr"]["primary_provider"] == "clova"
    assert body["ocr"]["live_provider_auth_checked"] is False
    assert body["parser"]["live_model_checked"] is False
    provider_rows = {row["selector"]: row for row in body["ocr"]["providers"]}
    assert provider_rows["configured"]["provider_label"] == "clova_ocr"
    assert provider_rows["paddleocr"]["provider_label"] == "paddleocr_local"
    assert provider_rows["google_vision"]["provider_label"] == "google_vision_document"
    assert provider_rows["clova"]["provider_label"] == "clova_ocr"
    response_text = response.text
    assert "placeholder-value" not in response_text
    assert "placeholder-key" not in response_text
    assert "example.test" not in response_text

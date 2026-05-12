"""헬스 체크 엔드포인트 테스트."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import create_app

HTTP_OK = 200


def test_health_check_returns_ok() -> None:
    """`/health`가 서비스 상태와 버전을 반환하는지 검증한다."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == HTTP_OK
    assert response.json() == {"status": "ok", "version": "0.1.0"}

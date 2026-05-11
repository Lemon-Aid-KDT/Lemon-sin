"""Health endpoint smoke tests."""

from fastapi.testclient import TestClient

from src.main import create_app

HTTP_OK = 200


def test_health_check_returns_ok() -> None:
    """The health endpoint returns the baseline service status."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == HTTP_OK
    assert response.json() == {"status": "ok", "version": "0.1.0"}

"""HTTP security middleware tests."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr
from src.config import Settings
from src.main import create_app
from src.middleware.security_headers import SECURITY_HEADERS


def _assert_security_headers(response_headers: Mapping[str, str]) -> None:
    """Assert baseline security headers are present.

    Args:
        response_headers: HTTP response headers mapping from TestClient.

    Returns:
        None.
    """
    headers = response_headers
    for name, expected_value in SECURITY_HEADERS.items():
        assert headers[name] == expected_value


def test_trusted_host_allows_configured_host() -> None:
    """Verify configured hosts can access the app."""
    app = create_app(settings=Settings(allowed_hosts=["testserver"]))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK


def test_security_headers_are_added_to_health_ready_and_api_responses() -> None:
    """Verify security headers are applied consistently across route families."""
    app = create_app(settings=Settings(allowed_hosts=["testserver"]))
    client = TestClient(app)

    for path in ("/health", "/ready", "/api/v1/does-not-exist"):
        response = client.get(path)
        _assert_security_headers(response.headers)


def test_trusted_host_blocks_unconfigured_host() -> None:
    """Verify unknown Host headers are rejected."""
    app = create_app(settings=Settings(allowed_hosts=["api.example.com"]))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_cors_preflight_allows_configured_origin() -> None:
    """Verify CORS preflight succeeds for an explicitly allowed origin."""
    app = create_app(
        settings=Settings(
            allowed_origins=["http://localhost:3000"],
            allowed_hosts=["testserver"],
        )
    )
    client = TestClient(app)

    response = client.options(
        "/api/v1/nutrition/kdris",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_allows_ngrok_skip_browser_warning_header() -> None:
    """Verify ngrok mobile API calls can send the interstitial bypass header."""
    app = create_app(
        settings=Settings(
            allowed_origins=["https://frontend.ngrok-free.app"],
            allowed_hosts=["testserver"],
        )
    )
    client = TestClient(app)

    response = client.options(
        "/api/v1/supplements/analyze",
        headers={
            "Origin": "https://frontend.ngrok-free.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,ngrok-skip-browser-warning",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "https://frontend.ngrok-free.app"
    assert "ngrok-skip-browser-warning" in response.headers["access-control-allow-headers"]


def test_cors_preflight_rejects_unconfigured_origin() -> None:
    """Verify CORS preflight rejects an unconfigured origin."""
    app = create_app(
        settings=Settings(
            allowed_origins=["http://localhost:3000"],
            allowed_hosts=["testserver"],
        )
    )
    client = TestClient(app)

    response = client.options(
        "/api/v1/nutrition/kdris",
        headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_rate_limit_blocks_default_bucket_after_threshold() -> None:
    """Verify enabled rate limiting returns a sanitized 429 response."""
    app = create_app(
        settings=Settings(
            allowed_hosts=["testserver"],
            rate_limit_enabled=True,
            rate_limit_default_per_minute=1,
        )
    )
    client = TestClient(app)

    first_response = client.get("/api/v1/does-not-exist")
    second_response = client.get("/api/v1/does-not-exist")

    assert first_response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["detail"]["code"] == "rate_limit_exceeded"
    assert second_response.json()["detail"]["bucket"] == "default"


def test_rate_limit_exempts_health_and_readiness() -> None:
    """Verify release health endpoints remain callable during rate-limit incidents."""
    app = create_app(
        settings=Settings(
            allowed_hosts=["testserver"],
            rate_limit_enabled=True,
            rate_limit_default_per_minute=1,
        )
    )
    client = TestClient(app)

    assert client.get("/health").status_code == status.HTTP_200_OK
    assert client.get("/health").status_code == status.HTTP_200_OK
    assert client.get("/ready").status_code == status.HTTP_200_OK
    assert client.get("/ready").status_code == status.HTTP_200_OK


def test_rate_limit_uses_supplement_image_upload_bucket() -> None:
    """Verify supplement image upload routes use the stricter upload bucket."""
    app = create_app(
        settings=Settings(
            allowed_hosts=["testserver"],
            rate_limit_enabled=True,
            rate_limit_image_upload_per_minute=1,
        )
    )
    client = TestClient(app)

    first_response = client.post("/api/v1/supplements/analyze")
    second_response = client.post("/api/v1/supplements/analyze")

    assert first_response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["detail"]["bucket"] == "supplement_image_upload"


def test_ready_returns_sanitized_component_statuses() -> None:
    """Verify readiness exposes provider status without credentials."""
    app = create_app(
        settings=Settings(
            allowed_hosts=["testserver"],
            google_cloud_api_key=SecretStr("secret-google-key"),
            clova_ocr_secret=SecretStr("secret-clova-key"),
        )
    )
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["environment"] == "development"
    assert body["deployment_exposure"] == "local"
    assert {component["name"] for component in body["components"]} >= {
        "auth",
        "rate_limit",
        "google_vision_ocr",
        "clova_ocr",
        "local_ocr",
        "ollama",
        "governance",
    }
    assert "secret-google-key" not in response.text
    assert "secret-clova-key" not in response.text
    assert "raw_ocr_text" not in response.text
    assert "raw_provider_payload" not in response.text


def test_ready_marks_disabled_rate_limit_as_degraded() -> None:
    """Verify disabled rate limiting is visible before release promotion."""
    app = create_app(
        settings=Settings(
            environment="development",
            allowed_hosts=["testserver"],
            rate_limit_enabled=False,
        )
    )
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    rate_limit_component = next(
        component for component in body["components"] if component["name"] == "rate_limit"
    )
    assert body["status"] == "degraded"
    assert rate_limit_component["status"] == "not_configured"

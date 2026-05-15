"""P1 API and security contract tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.v1 import dashboard
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.schemas.dashboard import (
    DashboardActivitySummary,
    DashboardNutrientSummary,
    DashboardSummaryResponse,
    DashboardSupplementSummary,
    DashboardWeightSummary,
)


def _openapi_schema() -> dict[str, Any]:
    """Return the generated OpenAPI schema.

    Returns:
        OpenAPI schema dictionary from the FastAPI app.
    """
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    return cast(dict[str, Any], response.json())


def _jwt_settings() -> Settings:
    """Return JWT-enabled settings for authentication contract tests.

    Returns:
        Settings configured for JWT auth.
    """
    return Settings(
        auth_mode="jwt",
        jwt_issuer="https://auth.example.com/",
        jwt_audience="lemon-api",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
    )


async def _fake_session_dependency() -> AsyncIterator[object]:
    """Yield a fake session for route tests.

    Yields:
        Fake session object.
    """
    yield object()


async def _allow_consent(*_args: object, **_kwargs: object) -> None:
    """No-op consent service for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


async def _record_noop_audit(*_args: object, **_kwargs: object) -> None:
    """No-op audit service for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


def _dashboard_response() -> DashboardSummaryResponse:
    """Return a dashboard response fixture.

    Returns:
        Dashboard summary response.
    """
    return DashboardSummaryResponse(
        as_of=datetime.now(UTC),
        nutrition=DashboardNutrientSummary(
            data_status="not_ready",
            low_count=0,
            high_count=0,
            source_manifest_version=None,
        ),
        activity=DashboardActivitySummary(),
        weight=DashboardWeightSummary(),
        supplements=DashboardSupplementSummary(registered_count=0, requires_review_count=0),
        disclaimers=["결과는 건강관리 참고 정보이며 개인 건강 상태를 확정하지 않습니다."],
        algorithm_version="dashboard-v1.0.0",
    )


def test_openapi_exposes_bearer_auth_security_scheme() -> None:
    """Verify OpenAPI documents the JWT BearerAuth contract."""
    schema = _openapi_schema()

    security_scheme = schema["components"]["securitySchemes"]["BearerAuth"]
    assert security_scheme["type"] == "http"
    assert security_scheme["scheme"] == "bearer"
    assert security_scheme["bearerFormat"] == "JWT"
    assert "OAuth/OIDC Bearer access token" in security_scheme["description"]


def test_p1_contract_endpoints_are_registered_with_required_scopes() -> None:
    """Verify P1 endpoints expose frozen route-level scope contracts."""
    schema = _openapi_schema()

    expected = {
        ("/api/v1/supplements/analyze", "post"): (
            "p1_2_intake_ready",
            ["supplement:write"],
        ),
        ("/api/v1/supplements/analyses/{analysis_id}/ocr-text", "post"): (
            "p1_2_intake_ready",
            ["supplement:write"],
        ),
        ("/api/v1/supplements", "post"): ("p1_4_registration_ready", ["supplement:write"]),
        ("/api/v1/supplements", "get"): ("p1_4_registration_ready", ["supplement:read"]),
        ("/api/v1/supplements/{supplement_id}", "get"): (
            "p1_4_registration_ready",
            ["supplement:read"],
        ),
        ("/api/v1/supplements/{supplement_id}", "delete"): (
            "p1_4_registration_ready",
            ["supplement:delete"],
        ),
        ("/api/v1/health/sync", "post"): ("p1_6_health_sync_ready", ["health:write"]),
        ("/api/v1/dashboard/summary", "get"): (
            "p1_5_deficiency_dashboard_ready",
            ["dashboard:read"],
        ),
        ("/api/v1/nutrition/diagnosis/latest", "get"): (
            "p1_5_deficiency_dashboard_ready",
            ["analysis:read"],
        ),
    }

    for (path, method), (contract_status, required_scopes) in expected.items():
        operation = schema["paths"][path][method]
        assert operation["x-contract-status"] == contract_status
        assert operation["x-required-scopes"] == required_scopes
        assert operation["security"] == [{"BearerAuth": []}]


def test_p1_contract_endpoints_expose_required_consents() -> None:
    """Verify P1 endpoints document consent gates before implementation starts."""
    schema = _openapi_schema()

    assert schema["paths"]["/api/v1/supplements/analyze"]["post"]["x-required-consents"] == [
        "ocr_image_processing"
    ]
    assert schema["paths"]["/api/v1/supplements/analyses/{analysis_id}/ocr-text"]["post"][
        "x-required-consents"
    ] == ["ocr_image_processing"]
    assert schema["paths"]["/api/v1/supplements"]["post"]["x-required-consents"] == [
        "sensitive_health_analysis"
    ]
    assert schema["paths"]["/api/v1/health/sync"]["post"]["x-required-consents"] == [
        "health_device_data"
    ]
    assert schema["paths"]["/api/v1/dashboard/summary"]["get"]["x-required-consents"] == [
        "sensitive_health_analysis"
    ]
    assert schema["paths"]["/api/v1/nutrition/diagnosis/latest"]["get"]["x-required-consents"] == [
        "sensitive_health_analysis"
    ]


def test_p1_dashboard_endpoint_returns_summary_after_auth_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implemented dashboard route is callable after auth in development."""

    async def fake_build_dashboard_summary(
        *_args: object,
        **_kwargs: object,
    ) -> DashboardSummaryResponse:
        """Return a fake dashboard response.

        Args:
            *_args: Positional call arguments.
            **_kwargs: Keyword call arguments.

        Returns:
            Dashboard summary response.
        """
        return _dashboard_response()

    monkeypatch.setattr(dashboard, "require_user_consent", _allow_consent)
    monkeypatch.setattr(dashboard, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(dashboard, "build_dashboard_summary", fake_build_dashboard_summary)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["algorithm_version"] == "dashboard-v1.0.0"


def test_p1_contract_endpoints_reject_missing_jwt_credentials() -> None:
    """Verify P1 route contracts keep JWT auth in production-style mode."""
    app = create_app(settings=_jwt_settings())
    app.dependency_overrides[get_settings] = _jwt_settings
    client = TestClient(app)

    response = client.get("/api/v1/supplements")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == 'Bearer realm="lemon-healthcare"'


def test_p1_openapi_contains_contract_error_examples() -> None:
    """Verify P1 endpoints expose expected error response contracts."""
    schema = _openapi_schema()
    supplement_analyze = schema["paths"]["/api/v1/supplements/analyze"]["post"]["responses"]
    supplement_create = schema["paths"]["/api/v1/supplements"]["post"]["responses"]
    health_sync = schema["paths"]["/api/v1/health/sync"]["post"]["responses"]

    assert "501" not in supplement_analyze
    assert "501" not in supplement_create
    assert "501" not in health_sync
    assert "idempotency_conflict" in health_sync["409"]["content"]["application/json"]["examples"]
    assert (
        "payload_too_large" in supplement_analyze["413"]["content"]["application/json"]["examples"]
    )
    assert (
        "unsupported_media_type"
        in supplement_analyze["415"]["content"]["application/json"]["examples"]
    )

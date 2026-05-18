"""AI Agent daily coaching API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from src.api.v1 import ai_agent
from src.db.dependencies import get_async_session
from src.main import create_app
from src.services.privacy import ConsentRequiredError


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


async def _deny_consent(*_args: object, **_kwargs: object) -> None:
    """Raise a missing-consent service error.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.

    Raises:
        ConsentRequiredError: Always raised for this test.
    """
    raise ConsentRequiredError("Consent is required.")


async def _record_noop_audit(*_args: object, **_kwargs: object) -> None:
    """No-op audit service for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


def _client() -> TestClient:
    """Return a TestClient with the DB session dependency replaced.

    Returns:
        FastAPI test client.
    """
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    return TestClient(app)


def _payload(*, user_confirmed: bool = True, unsafe_trend: bool = False) -> dict[str, object]:
    """Return a daily coaching request payload.

    Args:
        user_confirmed: Whether the OCR source has user confirmation.
        unsafe_trend: Whether to include unsafe trend text for sanitization.

    Returns:
        JSON request payload.
    """
    trend_summary = (
        "diabetes. purchase this supplement."
        if unsafe_trend
        else "Meal score has dropped for 7 days."
    )
    return {
        "request_id": "daily-coaching-route-test",
        "user_id": "client-supplied-user",
        "context": {
            "profile": {
                "age": 52,
                "gender": "male",
                "goals": ["meal_management"],
                "chronic_conditions": ["hypertension"],
                "medications": ["blood_pressure_medication"],
            }
        },
        "payload": {
            "date": "2026-05-18",
            "sources": [
                {
                    "source_type": "food_ocr",
                    "image_id": "meal-image-1",
                    "raw_ocr_text": "instant noodles sodium 2600mg",
                    "user_confirmed": user_confirmed,
                }
            ],
            "foods": [
                {
                    "name": "instant noodles",
                    "meal_type": "lunch",
                    "serving_label": "1 bowl",
                    "nutrients": [
                        {"name": "sodium", "amount": 2600, "unit": "mg"},
                        {"name": "protein", "amount": 25, "unit": "g"},
                    ],
                }
            ],
            "supplements": [],
            "health_trends": [
                {
                    "metric": "meal_score",
                    "direction": "down",
                    "severity": "watch",
                    "summary": trend_summary,
                }
            ],
        },
    }


def test_daily_coaching_returns_completed_result_for_confirmed_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the route runs deterministic coaching for confirmed input."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=_payload())

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["user_id"] == "local-dev-user"
    assert body["status"] == "completed"
    assert body["approval_status"] == "confirmed"
    assert body["provider"] == "deterministic"
    assert body["debug_trace"] == []
    levels = {finding["nutrient"]: finding["level"] for finding in body["findings"]}
    assert levels["sodium"] == "risky"
    assert levels["protein"] == "low"
    assert "raw_ocr_text" not in str(body)


def test_daily_coaching_returns_preview_for_unconfirmed_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unconfirmed OCR source records stop at preview state."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(user_confirmed=False),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "preview"
    assert body["approval_status"] == "requires_confirmation"
    assert body["requires_user_approval"] is True
    assert body["findings"] == []
    assert body["recommendations"] == []
    assert body["actions"] == []


def test_daily_coaching_requires_sensitive_health_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the route fails closed without sensitive-health consent."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _deny_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=_payload())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"


def test_daily_coaching_sanitizes_unsafe_trend_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unsafe trace text is not returned from the API response."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(unsafe_trend=True),
    )

    assert response.status_code == status.HTTP_200_OK
    body_text = str(response.json())
    assert "Trace text blocked" in body_text
    assert "diabetes" not in body_text
    assert "purchase this supplement" not in body_text

"""User supplement registration API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from src.api.v1 import supplements
from src.config import Settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.db.supplement import UserSupplement, UserSupplementIngredient
from src.models.schemas.supplement import (
    UserSupplementCreate,
    UserSupplementListResponse,
)
from src.security.auth import AuthenticatedUser
from src.services.privacy import ConsentRequiredError
from src.services.supplement_registration import UserSupplementStoreResult


async def _fake_session_dependency() -> AsyncIterator[object]:
    """Yield a fake session for route tests.

    Yields:
        Fake session object.
    """
    yield object()


async def _allow_consent(*_args: object, **_kwargs: object) -> None:
    """No-op consent dependency for route tests.

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
    """No-op audit writer for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


def _payload() -> dict[str, object]:
    """Return a valid user supplement confirmation payload.

    Returns:
        JSON payload dictionary.
    """
    return {
        "analysis_id": "11111111-1111-4111-8111-111111111111",
        "display_name": "Vitamin D 1000 IU",
        "manufacturer": "Sample Nutrition",
        "ingredients": [
            {
                "display_name": "Vitamin D",
                "nutrient_code": "vitamin_d_ug",
                "amount": 25,
                "unit": "ug",
                "confidence": 1,
                "source": "user_confirmed",
            }
        ],
        "serving": {"amount": 1, "unit": "capsule", "daily_servings": 1},
        "intake_schedule": {"frequency": "daily", "time_of_day": ["morning"]},
        "user_confirmed": True,
    }


def _stored_supplement() -> UserSupplement:
    """Return a stored supplement row fixture.

    Returns:
        User supplement row.
    """
    now = datetime.now(UTC)
    return UserSupplement(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        display_name="Vitamin D 1000 IU",
        manufacturer="Sample Nutrition",
        serving_snapshot={"amount": 1, "unit": "capsule", "daily_servings": 1},
        intake_schedule={"frequency": "daily", "time_of_day": ["morning"]},
        user_confirmed_at=now,
        created_at=now,
        updated_at=now,
    )


def _stored_ingredient(supplement_id: object) -> UserSupplementIngredient:
    """Return a stored supplement ingredient row fixture.

    Args:
        supplement_id: Parent supplement id.

    Returns:
        User supplement ingredient row.
    """
    return UserSupplementIngredient(
        id=uuid4(),
        user_supplement_id=supplement_id,
        display_name="Vitamin D",
        nutrient_code="vitamin_d_ug",
        amount=Decimal("25"),
        unit="ug",
        confidence=Decimal("1"),
        source="user_confirmed",
        sort_order=0,
    )


def test_create_user_supplement_uses_current_user_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify registration route stores a current-user confirmed supplement."""
    captured: dict[str, object] = {}
    supplement = _stored_supplement()
    ingredient = _stored_ingredient(supplement.id)

    async def fake_store(
        _session: object,
        user: AuthenticatedUser,
        request: UserSupplementCreate,
        _settings: Settings,
    ) -> UserSupplementStoreResult:
        """Capture route inputs and return a stored row.

        Args:
            _session: Fake session dependency.
            user: Authenticated user passed by the route.
            request: Validated request payload.
            _settings: Runtime settings passed by the route.

        Returns:
            Fake persisted supplement result.
        """
        captured["subject"] = user.subject
        captured["analysis_id"] = request.analysis_id
        return UserSupplementStoreResult(supplement=supplement, ingredients=[ingredient])

    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(supplements, "create_user_supplement_from_confirmation", fake_store)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)

    response = client.post("/api/v1/supplements", json=_payload())

    assert response.status_code == status.HTTP_201_CREATED
    assert captured["subject"] == "local-dev-user"
    assert str(captured["analysis_id"]) == "11111111-1111-4111-8111-111111111111"
    body = response.json()
    assert body["display_name"] == "Vitamin D 1000 IU"
    assert "owner_subject" not in body


def test_create_user_supplement_rejects_mass_assignment_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify owner and server-owned fields are not accepted in request bodies."""
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)
    payload = {
        **_payload(),
        "owner_subject": "attacker",
        "matched_product_id": "22222222-2222-4222-8222-222222222222",
    }

    response = client.post("/api/v1/supplements", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_user_supplement_requires_sensitive_health_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement registration fails closed without sensitive-health consent."""
    monkeypatch.setattr(supplements, "require_user_consent", _deny_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)

    response = client.post("/api/v1/supplements", json=_payload())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"


def test_list_user_supplements_returns_owner_scoped_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify list route returns stored current-user supplement records."""
    supplement = _stored_supplement()
    ingredient = _stored_ingredient(supplement.id)
    response_model = supplements.user_supplement_to_response(supplement, [ingredient])

    async def fake_list(
        _session: object,
        _user: AuthenticatedUser,
        limit: int,
        offset: int,
    ) -> UserSupplementListResponse:
        """Return a fake list response.

        Args:
            _session: Fake session dependency.
            _user: Authenticated user passed by the route.
            limit: Requested limit.
            offset: Requested offset.

        Returns:
            Fake list response.
        """
        return UserSupplementListResponse(results=[response_model], limit=limit, offset=offset)

    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(supplements, "list_user_supplement_records", fake_list)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)

    response = client.get("/api/v1/supplements")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["ingredients"][0]["nutrient_code"] == "vitamin_d_ug"


def test_get_user_supplement_returns_404_for_inaccessible_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify detail route hides non-owner or missing supplement records."""

    async def fake_get(*_args: object, **_kwargs: object) -> None:
        """Return no supplement row.

        Args:
            *_args: Positional call arguments.
            **_kwargs: Keyword call arguments.

        Returns:
            None.
        """

    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(supplements, "get_user_supplement_record", fake_get)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)

    response = client.get(f"/api/v1/supplements/{uuid4()}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_user_supplement_returns_204_when_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify delete route delegates owner-scoped soft deletion."""
    captured: dict[str, object] = {}

    async def fake_delete(
        _session: object,
        user: AuthenticatedUser,
        supplement_id: object,
    ) -> bool:
        """Capture delete inputs and simulate a successful delete.

        Args:
            _session: Fake session dependency.
            user: Authenticated user passed by the route.
            supplement_id: Requested supplement id.

        Returns:
            True to simulate a deleted row.
        """
        captured["subject"] = user.subject
        captured["supplement_id"] = supplement_id
        return True

    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(supplements, "soft_delete_user_supplement", fake_delete)
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    client = TestClient(app)
    supplement_id = uuid4()

    response = client.delete(f"/api/v1/supplements/{supplement_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert captured["subject"] == "local-dev-user"
    assert captured["supplement_id"] == supplement_id

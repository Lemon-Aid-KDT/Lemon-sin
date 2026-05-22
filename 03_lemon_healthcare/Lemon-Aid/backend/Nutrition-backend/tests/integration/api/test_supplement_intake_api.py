"""Supplement image intake API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Self, cast
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image
from src.api.v1 import supplements
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.db.privacy import AuditLog
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.services.privacy import ConsentRequiredError
from src.services.supplement_image_analysis import SupplementImageAnalysisAdapters


class _TransactionContext:
    """Async context manager used by the fake session transaction."""

    async def __aenter__(self) -> Self:
        """Enter the fake transaction.

        Returns:
            Context manager instance.
        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Exit the fake transaction.

        Args:
            *_exc_info: Exception information ignored by the fake context.

        Returns:
            None.
        """


class _FakeSupplementSession:
    """Fake async session for supplement intake route tests."""

    def __init__(self, existing: SupplementAnalysisRun | None = None) -> None:
        self.existing = existing
        self.added_analysis: SupplementAnalysisRun | None = None
        self.added_analysis_count = 0
        self.added_audits: list[AuditLog] = []
        self.committed = False

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

    def in_transaction(self) -> bool:
        """Return whether the fake session has an active transaction.

        Returns:
            False because this fake session does not model implicit transactions.
        """
        return False

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        """Return a fake existing row for idempotency lookup.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Existing supplement analysis run or None.
        """
        return self.existing

    def add(self, record: object) -> None:
        """Capture ORM records passed by route services.

        Args:
            record: ORM object passed by a service.

        Returns:
            None.
        """
        if isinstance(record, SupplementAnalysisRun):
            self.added_analysis_count += 1
            self.added_analysis = record
            return
        if isinstance(record, AuditLog):
            self.added_audits.append(record)

    async def refresh(self, record: object) -> None:
        """Populate server-generated fields after fake persistence.

        Args:
            record: ORM object to refresh.

        Returns:
            None.
        """
        supplement_run = cast(SupplementAnalysisRun, record)
        supplement_run.id = uuid4()
        supplement_run.created_at = datetime.now(UTC)
        supplement_run.updated_at = datetime.now(UTC)

    async def commit(self) -> None:
        """Record an audit commit.

        Returns:
            None.
        """
        self.committed = True


def _png_bytes() -> bytes:
    """Return a tiny PNG image.

    Returns:
        PNG image bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", (3, 2), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _existing_run(image_sha256: str = "a" * 64) -> SupplementAnalysisRun:
    """Return an existing supplement analysis run fixture.

    Args:
        image_sha256: Stored image hash.

    Returns:
        Existing supplement analysis run.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256=image_sha256,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="intake-only",
        parsed_snapshot={"parsed_product": {}, "ingredient_candidates": []},
        match_snapshot={"matched_product_candidates": []},
        warnings=[],
        algorithm_version="supplement-intake-v1.0.0",
        expires_at=now + timedelta(minutes=30),
        created_at=now,
        updated_at=now,
    )


def _session_dependency(
    fake_session: _FakeSupplementSession,
) -> Callable[[], AsyncIterator[object]]:
    """Build a FastAPI dependency override yielding a fake session.

    Args:
        fake_session: Fake session to yield.

    Returns:
        Dependency callable.
    """

    async def dependency() -> AsyncIterator[object]:
        """Yield the fake session.

        Yields:
            Fake session object.
        """
        yield fake_session

    return dependency


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
    raise ConsentRequiredError("OCR image processing consent is required.")


async def _record_noop_audit(*_args: object, **_kwargs: object) -> None:
    """No-op audit writer for error-path route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


def _empty_analysis_adapters() -> SupplementImageAnalysisAdapters:
    """Return an intake-only adapter bundle.

    Returns:
        Empty supplement image analysis adapters.
    """
    return SupplementImageAnalysisAdapters()


def _settings(
    *,
    rate_limit_enabled: bool = True,
    rate_limit_window_seconds: int = 60,
    supplement_image_upload_rate_limit: int = 10,
    supplement_image_max_bytes: int = 5 * 1024 * 1024,
    supplement_image_max_pixels: int = 12_000_000,
    supplement_preview_ttl_minutes: int = 30,
) -> Settings:
    """Return settings for route tests.

    Args:
        rate_limit_enabled: Whether API rate limiting is active.
        rate_limit_window_seconds: Fixed-window duration for local limits.
        supplement_image_upload_rate_limit: Upload requests allowed per subject/window.
        supplement_image_max_bytes: Maximum image byte size.
        supplement_image_max_pixels: Maximum decoded image pixels.
        supplement_preview_ttl_minutes: Preview TTL in minutes.

    Returns:
        Settings object.
    """
    return Settings(
        _env_file=None,
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_window_seconds=rate_limit_window_seconds,
        supplement_image_upload_rate_limit=supplement_image_upload_rate_limit,
        supplement_image_max_bytes=supplement_image_max_bytes,
        supplement_image_max_pixels=supplement_image_max_pixels,
        supplement_preview_ttl_minutes=supplement_preview_ttl_minutes,
    )


def test_analyze_supplement_label_accepts_valid_png_and_stores_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement analyze performs image intake and returns a preview."""
    fake_session = _FakeSupplementSession()
    settings = _settings()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert fake_session.added_analysis is not None
    assert fake_session.added_analysis.owner_subject == "local-development::local-dev-user"
    stored_idempotency_key = fake_session.added_analysis.client_request_id
    assert stored_idempotency_key is not None
    prefix, sep, suffix = stored_idempotency_key.partition(":")
    assert sep == ":"
    assert len(prefix) == 16
    assert all(char in "0123456789abcdef" for char in prefix)
    assert suffix == "client-1"
    assert fake_session.added_analysis.ocr_text_hash is None
    assert fake_session.added_analysis.parsed_snapshot["ingredient_candidates"] == []
    assert len(fake_session.added_audits) == 1
    body = response.json()
    assert body["status"] == "requires_confirmation"
    assert body["ingredient_candidates"] == []
    assert body["algorithm_version"] == "supplement-intake-v1.0.0"


def test_analyze_supplement_label_requires_ocr_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement image intake fails closed without OCR consent."""
    fake_session = _FakeSupplementSession()
    settings = _settings()
    monkeypatch.setattr(supplements, "require_user_consent", _deny_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"
    assert response.json()["detail"]["required_consents"] == ["ocr_image_processing"]


def test_analyze_supplement_label_rejects_media_type_spoofing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify content-type and image bytes must agree."""
    fake_session = _FakeSupplementSession()
    settings = _settings()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.jpg", _png_bytes(), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["detail"]["code"] == "unsupported_media_type"
    assert fake_session.added_analysis is None


def test_analyze_supplement_label_rate_limits_repeated_uploads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify repeated supplement image uploads are blocked before handler work."""
    fake_session = _FakeSupplementSession()
    settings = _settings(
        rate_limit_window_seconds=60,
        supplement_image_upload_rate_limit=1,
    )
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    first_response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
    )
    second_response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-2"},
    )

    assert first_response.status_code == status.HTTP_202_ACCEPTED
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["detail"]["code"] == "too_many_requests"
    assert second_response.json()["detail"]["bucket"] == "supplement_image_upload"
    assert int(second_response.headers["Retry-After"]) >= 1
    assert second_response.headers["X-Content-Type-Options"] == "nosniff"
    assert fake_session.added_analysis_count == 1


def test_analyze_supplement_label_rate_limit_ignores_unverified_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify arbitrary Authorization changes cannot bypass local upload limits."""
    fake_session = _FakeSupplementSession()
    settings = _settings(
        rate_limit_window_seconds=60,
        supplement_image_upload_rate_limit=1,
    )
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    first_response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
        headers={"Authorization": "Bearer attacker-token-1"},
    )
    second_response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-2"},
        headers={"Authorization": "Bearer attacker-token-2"},
    )

    assert first_response.status_code == status.HTTP_202_ACCEPTED
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["detail"]["code"] == "too_many_requests"
    assert fake_session.added_analysis_count == 1


def test_analyze_supplement_label_rejects_oversized_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement image byte limits are enforced through settings."""
    fake_session = _FakeSupplementSession()
    settings = _settings(supplement_image_max_bytes=1024)
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", b"x" * 1025, "image/png")},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json()["detail"]["code"] == "payload_too_large"
    assert fake_session.added_analysis is None


def test_analyze_supplement_label_rejects_idempotency_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a client idempotency key cannot be reused for another image."""
    fake_session = _FakeSupplementSession(existing=_existing_run(image_sha256="b" * 64))
    settings = _settings()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"]["code"] == "idempotency_conflict"
    assert fake_session.added_analysis is None

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
from pydantic import SecretStr
from src.api.v1 import supplements
from src.barcode.normalization import normalize_barcode_text
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.db.privacy import AuditLog
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.privacy import ConsentType
from src.models.schemas.supplement import (
    SupplementAnalysisStatus,
    SupplementBarcodeProductCandidate,
)
from src.services.privacy import ConsentRequiredError
from src.services.supplement_barcode_lookup import BarcodeLookupServiceResult
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
        self.added_audits: list[AuditLog] = []
        self.committed = False

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

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

    async def rollback(self) -> None:
        """Allow service-level rollback in failed fake transactions.

        Returns:
            None.
        """


class _FakeBarcodeLookupService:
    """Fake barcode lookup service for analyze route tests."""

    def __init__(self, result: BarcodeLookupServiceResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str | None]] = []

    async def lookup(
        self,
        barcode_text: str,
        *,
        barcode_format: str | None = None,
    ) -> BarcodeLookupServiceResult:
        """Return a configured barcode lookup result.

        Args:
            barcode_text: Request barcode text.
            barcode_format: Optional scanner format.

        Returns:
            Configured barcode lookup result.
        """

        self.calls.append((barcode_text, barcode_format))
        return self.result


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


def _settings(
    *,
    supplement_image_max_bytes: int = 5 * 1024 * 1024,
    supplement_image_max_pixels: int = 12_000_000,
    supplement_preview_ttl_minutes: int = 30,
) -> Settings:
    """Return settings for route tests.

    Args:
        supplement_image_max_bytes: Maximum image byte size.
        supplement_image_max_pixels: Maximum decoded image pixels.
        supplement_preview_ttl_minutes: Preview TTL in minutes.

    Returns:
        Settings object.
    """
    return Settings(
        supplement_image_max_bytes=supplement_image_max_bytes,
        supplement_image_max_pixels=supplement_image_max_pixels,
        supplement_preview_ttl_minutes=supplement_preview_ttl_minutes,
    )


def _empty_analysis_adapters() -> SupplementImageAnalysisAdapters:
    """Return an empty adapter bundle for intake-only route tests.

    Returns:
        Empty supplement image analysis adapters.
    """
    return SupplementImageAnalysisAdapters()


def test_analyze_supplement_label_accepts_valid_png_and_stores_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement analyze performs image intake and returns a preview."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
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
    assert fake_session.added_analysis.client_request_id == "client-1"
    assert fake_session.added_analysis.ocr_text_hash is None
    assert fake_session.added_analysis.parsed_snapshot["ingredient_candidates"] == []
    assert len(fake_session.added_audits) == 1
    body = response.json()
    assert body["status"] == "requires_confirmation"
    assert body["ingredient_candidates"] == []
    assert body["action_required"] == "none"
    assert body["analysis_scope"] == "unknown"
    assert body["detected_product_regions"] == []
    assert body["algorithm_version"] == "supplement-intake-v1.0.0"


def test_analyze_supplement_label_attaches_optional_barcode_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify analyze can attach review-only barcode candidates to the preview."""
    fake_session = _FakeSupplementSession()
    identifier = normalize_barcode_text("08801007325224", scanner_format="GTIN_14")
    candidate = SupplementBarcodeProductCandidate(
        source_id="foodqr:08801007325224:1:1",
        provider="foodqr",
        product_name="[CJ] Bibigo Gyoza Dumplings",
        manufacturer="씨제이제일제당(주)",
        barcode="08801007325224",
        version="1",
        valid_from="20250211",
        valid_to="99991231",
        match_score=0.92,
        review_required_reason="user_confirmation_required",
    )
    fake_barcode_service = _FakeBarcodeLookupService(
        BarcodeLookupServiceResult(
            status="review_required",
            identifier=identifier,
            candidates=(candidate,),
            warnings=("Official barcode candidates require user confirmation before storage.",),
        )
    )
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_barcode_lookup_service] = (
        lambda: fake_barcode_service
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={
            "client_request_id": "client-with-barcode",
            "barcode_text": "08801007325224",
            "barcode_format": "GTIN_14",
        },
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["barcode_lookup"]["status"] == "review_required"
    assert body["barcode_lookup"]["auto_confirmed"] is False
    assert body["matched_product_candidates"][0]["source_id"] == "foodqr:08801007325224:1:1"
    assert fake_barcode_service.calls == [("08801007325224", "GTIN_14")]
    assert fake_session.added_analysis is not None
    barcode_snapshot = fake_session.added_analysis.parsed_snapshot["barcode_lookup"]
    assert barcode_snapshot["raw_provider_payload_stored"] is False
    assert "raw_payload" not in str(barcode_snapshot)


def test_analyze_supplement_label_requires_ocr_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement image intake fails closed without OCR consent."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _deny_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"
    assert response.json()["detail"]["required_consents"] == ["ocr_image_processing"]


def test_analyze_supplement_label_requires_external_consent_for_clova_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify CLOVA fallback requires external OCR consent even without primary OCR."""
    fake_session = _FakeSupplementSession()
    seen_consents: list[ConsentType] = []

    async def deny_external_consent(*args: object, **_kwargs: object) -> None:
        """Deny only external OCR consent and capture checked buckets."""
        consent_type = cast(ConsentType, args[2])
        seen_consents.append(consent_type)
        if consent_type == ConsentType.EXTERNAL_OCR_PROCESSING:
            raise ConsentRequiredError("external OCR consent is required.")

    settings = Settings(
        enable_clova_ocr=True,
        allow_external_ocr=True,
        clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
        clova_ocr_secret=SecretStr("test-secret"),
    )

    def empty_adapters() -> SupplementImageAnalysisAdapters:
        """Return an empty adapter bundle so this test isolates consent routing.

        Returns:
            Empty supplement image analysis adapters.
        """
        return SupplementImageAnalysisAdapters()

    monkeypatch.setattr(supplements, "require_user_consent", deny_external_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = empty_adapters
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert seen_consents == [
        ConsentType.OCR_IMAGE_PROCESSING,
        ConsentType.EXTERNAL_OCR_PROCESSING,
    ]
    assert response.json()["detail"]["required_consents"] == ["external_ocr_processing"]
    assert fake_session.added_analysis is None


def test_analyze_supplement_label_rejects_media_type_spoofing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify content-type and image bytes must agree."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.jpg", _png_bytes(), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["detail"]["code"] == "unsupported_media_type"
    assert fake_session.added_analysis is None


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
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
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

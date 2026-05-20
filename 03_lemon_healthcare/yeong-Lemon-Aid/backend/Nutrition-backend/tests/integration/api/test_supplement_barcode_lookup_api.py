"""Supplement barcode lookup API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr
from src.api.v1 import supplements
from src.barcode.normalization import normalize_barcode_text
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.db.privacy import AuditLog
from src.models.schemas.supplement import SupplementBarcodeProductCandidate
from src.services.supplement_barcode_lookup import BarcodeLookupServiceResult


class _FakeAuditSession:
    """Fake async session for barcode lookup route audit tests."""

    def __init__(self) -> None:
        self.added_audits: list[AuditLog] = []
        self.committed = False

    def add(self, record: object) -> None:
        """Capture audit records.

        Args:
            record: ORM object passed by the audit service.

        Returns:
            None.
        """

        if isinstance(record, AuditLog):
            self.added_audits.append(record)

    async def commit(self) -> None:
        """Record commit.

        Returns:
            None.
        """

        self.committed = True


class _FakeBarcodeLookupService:
    """Fake barcode lookup service for route tests."""

    def __init__(self, result: BarcodeLookupServiceResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str | None]] = []

    async def lookup(
        self,
        barcode_text: str,
        *,
        barcode_format: str | None = None,
    ) -> BarcodeLookupServiceResult:
        """Return configured lookup result.

        Args:
            barcode_text: Request barcode text.
            barcode_format: Optional scanner format.

        Returns:
            Configured result.
        """

        self.calls.append((barcode_text, barcode_format))
        return self.result


def _session_dependency(
    fake_session: _FakeAuditSession,
) -> Callable[[], AsyncIterator[object]]:
    """Build a dependency override for the fake session.

    Args:
        fake_session: Fake session.

    Returns:
        Dependency callable.
    """

    async def dependency() -> AsyncIterator[object]:
        """Yield the fake session.

        Yields:
            Fake session.
        """

        yield fake_session

    return dependency


def test_lookup_supplement_barcode_returns_review_only_candidates() -> None:
    """Verify barcode lookup returns candidates without requiring OCR consent."""
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
    fake_service = _FakeBarcodeLookupService(
        BarcodeLookupServiceResult(
            status="review_required",
            identifier=identifier,
            candidates=(candidate,),
            warnings=("Official barcode candidates require user confirmation before storage.",),
        )
    )
    fake_session = _FakeAuditSession()
    settings = Settings(_env_file=None, privacy_hash_secret=SecretStr("test-secret"))
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_barcode_lookup_service] = (
        lambda: fake_service
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/barcode/lookup",
        json={"barcode_text": "08801007325224", "barcode_format": "GTIN_14"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "review_required"
    assert body["candidate_count"] == 1
    assert body["auto_confirmed"] is False
    assert body["raw_provider_payload_stored"] is False
    assert fake_service.calls == [("08801007325224", "GTIN_14")]
    assert len(fake_session.added_audits) == 1
    audit_metadata = fake_session.added_audits[0].event_metadata
    assert audit_metadata["barcode_hash"].startswith("sha256:")
    assert "08801007325224" not in str(audit_metadata)


def test_lookup_supplement_barcode_rejects_invalid_barcode() -> None:
    """Verify invalid barcodes return 422 after sanitized audit logging."""
    fake_service = _FakeBarcodeLookupService(
        BarcodeLookupServiceResult(
            status="invalid_request",
            warnings=("Barcode check digit is invalid.",),
            error_code="barcode_check_digit_invalid",
            error_message="Barcode check digit is invalid.",
        )
    )
    fake_session = _FakeAuditSession()
    settings = Settings(_env_file=None, privacy_hash_secret=SecretStr("test-secret"))
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_barcode_lookup_service] = (
        lambda: fake_service
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/barcode/lookup",
        json={"barcode_text": "8801234567890"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["code"] == "barcode_check_digit_invalid"
    assert fake_session.added_audits[0].outcome == "blocked"

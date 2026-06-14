"""Integration tests for image-safety guarantees on /supplements/analyze.

Two surfaces:

1. EXIF/GPS stripping — bytes that reach the OCR adapter and storage must not
   carry GPS/Make/Software EXIF entries.
2. Decompression-bomb guard — uploads exceeding the configured pixel cap are
   rejected with HTTP 413 before any decode work runs downstream.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
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
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.ocr.base import OCRAdapter, OCRImageInput, OCRResult
from src.ocr.providers.paddle import PADDLE_OCR_PROVIDER
from src.services.supplement_image_analysis import SupplementImageAnalysisAdapters

GPSINFO_TAG = 0x8825
SOFTWARE_TAG = 0x0131
MAKE_TAG = 0x010F


class _TransactionContext:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None


class _FakeSession:
    """Capture analysis rows + audit events for assertion."""

    def __init__(self) -> None:
        self.added_analysis: SupplementAnalysisRun | None = None
        self.added_audits: list[AuditLog] = []
        self.committed = False
        # A real AsyncSession always exposes ``.info``; persist_scope reads it.
        self.info: dict[str, object] = {}

    async def flush(self) -> None:
        """No-op flush (persist_scope flushes pending writes)."""

    async def rollback(self) -> None:
        """No-op rollback (persist_scope own-mode rolls back on exception)."""

    def begin(self) -> _TransactionContext:
        return _TransactionContext()

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        return self.added_analysis

    def add(self, record: object) -> None:
        if isinstance(record, SupplementAnalysisRun):
            self.added_analysis = record
            return
        if isinstance(record, AuditLog):
            self.added_audits.append(record)

    async def refresh(self, record: object) -> None:
        run = cast(SupplementAnalysisRun, record)
        if getattr(run, "id", None) is None:
            run.id = uuid4()
        run.created_at = datetime.now(UTC)
        run.updated_at = datetime.now(UTC)

    async def commit(self) -> None:
        self.committed = True


class _CapturingOCRAdapter(OCRAdapter):
    """OCR adapter spy that records the bytes it was given."""

    def __init__(self) -> None:
        self.received: OCRImageInput | None = None

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        self.received = image
        return OCRResult(text="비타민 D 1000", provider=PADDLE_OCR_PROVIDER, confidence=0.9)


class _FakeParser:
    async def parse_supplement_ocr_text(self, _ocr_text: str) -> SupplementStructuredParseResult:
        return SupplementStructuredParseResult.model_validate(
            {
                "parsed_product": {"product_name": "비타민 D"},
                "ingredient_candidates": [],
                "low_confidence_fields": [],
                "warnings": [],
            }
        )


def _session_dependency(session: _FakeSession) -> Callable[[], AsyncIterator[object]]:
    async def dep() -> AsyncIterator[object]:
        yield session

    return dep


def _client(
    *,
    fake_session: _FakeSession,
    settings: Settings,
    adapters: SupplementImageAnalysisAdapters,
) -> TestClient:
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = lambda: adapters
    return TestClient(app)


def _jpeg_with_identifying_exif() -> bytes:
    """Build a 32x24 JPEG carrying GPS, Software, and Make EXIF entries."""
    base = Image.new("RGB", (32, 24), color=(40, 200, 120))
    buf = BytesIO()
    exif = base.getexif()
    exif[SOFTWARE_TAG] = "lemon-test-suite"
    exif[MAKE_TAG] = "TestPhone"
    gps_ifd = exif.get_ifd(GPSINFO_TAG)
    gps_ifd[1] = "N"
    gps_ifd[3] = "E"
    base.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def _oversized_png(width: int = 6000, height: int = 6000) -> bytes:
    """Build a PNG whose decoded pixel count exceeds the default 12 Mpx cap."""
    buf = BytesIO()
    Image.new("L", (width, height), color=0).save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def test_supplement_analyze_strips_exif_from_bytes_handed_to_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the OCR adapter receives sanitized bytes (no GPS/Make/Software)."""
    session = _FakeSession()
    adapter = _CapturingOCRAdapter()
    parser = _FakeParser()

    async def allow_consent(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(supplements, "require_user_consent", allow_consent)
    settings = Settings(_env_file=None)

    client = _client(
        fake_session=session,
        settings=settings,
        adapters=SupplementImageAnalysisAdapters(ocr=adapter, parser=parser),
    )
    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.jpg", _jpeg_with_identifying_exif(), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert adapter.received is not None
    with Image.open(BytesIO(adapter.received.image_bytes)) as sanitized:
        sanitized_exif = sanitized.getexif()
        assert sanitized_exif.get(SOFTWARE_TAG) is None
        assert sanitized_exif.get(MAKE_TAG) is None
        assert sanitized_exif.get_ifd(GPSINFO_TAG) == {}


def test_supplement_analyze_rejects_oversized_image_with_413(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify uploads that exceed the configured pixel cap are blocked with 413."""
    session = _FakeSession()

    async def allow_consent(*_args: object, **_kwargs: object) -> None:
        return None

    async def noop_audit(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(supplements, "require_user_consent", allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", noop_audit)
    settings = Settings(_env_file=None)

    client = _client(
        fake_session=session,
        settings=settings,
        adapters=SupplementImageAnalysisAdapters(),
    )
    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("bomb.png", _oversized_png(), "image/png")},
    )

    assert response.status_code == 413
    assert session.added_analysis is None

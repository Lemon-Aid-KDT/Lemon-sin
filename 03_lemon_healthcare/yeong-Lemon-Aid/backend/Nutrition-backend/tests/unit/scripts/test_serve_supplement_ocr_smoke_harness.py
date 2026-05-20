"""Tests for the local supplement OCR smoke harness."""

from __future__ import annotations

from io import BytesIO
from typing import cast

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from src.config import Settings
from src.ocr.base import OCRImageInput, OCRResult

from scripts import serve_supplement_ocr_smoke_harness as harness


def _png_bytes() -> bytes:
    """Build a valid in-memory PNG fixture.

    Returns:
        PNG bytes accepted by the supplement image validator.
    """
    image = Image.new("RGB", (240, 120), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakePaddleAdapter:
    """Fake local OCR adapter for smoke harness tests."""

    def __init__(self, _settings: Settings) -> None:
        """Initialize the fake adapter.

        Args:
            _settings: Runtime settings ignored by the fake.
        """

    async def extract_text(self, _image: OCRImageInput) -> OCRResult:
        """Return deterministic OCR text.

        Args:
            _image: OCR input ignored by the fake.

        Returns:
            OCR result containing raw text for the local-only response.
        """
        return OCRResult(
            text="Vitamin D 25 ug\nZinc 10 mg",
            provider="paddleocr_local",
            confidence=0.91,
        )


def test_index_exposes_camera_capture_input() -> None:
    """Verify the harness page supports camera or file upload."""
    app = harness.create_app(adapter_factory=cast(harness.OCRAdapterFactory, _FakePaddleAdapter))

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'accept="image/*"' in response.text
    assert 'capture="environment"' in response.text
    assert response.headers["cache-control"] == "no-store"


def test_run_ocr_returns_transient_raw_text() -> None:
    """Verify OCR text is returned to the local browser response."""
    app = harness.create_app(adapter_factory=cast(harness.OCRAdapterFactory, _FakePaddleAdapter))

    response = TestClient(app).post(
        "/api/ocr",
        files={"image": ("label.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["provider"] == "paddleocr_local"
    assert payload["confidence"] == 0.91
    assert payload["line_count"] == 2
    assert payload["text"] == "Vitamin D 25 ug\nZinc 10 mg"
    assert payload["image"]["mime_type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"


def test_run_ocr_rejects_unsupported_upload() -> None:
    """Verify non-image uploads fail before OCR execution."""
    app = harness.create_app(adapter_factory=cast(harness.OCRAdapterFactory, _FakePaddleAdapter))

    response = TestClient(app).post(
        "/api/ocr",
        files={"image": ("label.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_media_type"


def test_validate_server_options_rejects_non_loopback_without_opt_in() -> None:
    """Verify the harness fails closed for non-loopback binds."""
    options = harness.ServerOptions(
        host="0.0.0.0",
        port=8790,
        allow_non_loopback=False,
        confidence_threshold=0.0,
    )

    with pytest.raises(SystemExit, match="Refusing non-loopback bind"):
        harness.validate_server_options(options)

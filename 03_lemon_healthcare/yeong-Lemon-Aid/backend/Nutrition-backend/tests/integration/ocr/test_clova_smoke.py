"""Opt-in NAVER Cloud CLOVA OCR smoke test.

This test is skipped unless RUN_CLOVA_OCR_LIVE_SMOKE=1 and a local sample image
path are provided. Credentials and sample images must not be committed to the
repository.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from src.config import Settings
from src.ocr.base import OCRImageInput
from src.ocr.providers.clova import CLOVA_OCR_PROVIDER, ClovaOCRAdapter

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CLOVA_OCR_LIVE_SMOKE") != "1",
    reason="CLOVA OCR smoke test requires RUN_CLOVA_OCR_LIVE_SMOKE=1.",
)


@pytest.mark.asyncio
async def test_clova_smoke_returns_non_empty_text() -> None:
    """Verify a real opt-in CLOVA OCR call returns text for a local sample image."""
    image_path_value = os.getenv("CLOVA_OCR_SMOKE_IMAGE_PATH")
    assert image_path_value, "CLOVA_OCR_SMOKE_IMAGE_PATH is required."
    image_path = Path(image_path_value)
    image_bytes = image_path.read_bytes()
    mime_type = _mime_type_for_path(image_path)
    settings = Settings(_env_file=None)

    assert settings.enable_clova_ocr is True
    assert settings.allow_external_ocr is True
    assert settings.clova_ocr_api_url
    assert settings.clova_ocr_secret is not None

    adapter = ClovaOCRAdapter(settings)
    result = await adapter.extract_text(
        OCRImageInput(
            image_bytes=image_bytes,
            mime_type=mime_type,
            width=1,
            height=1,
        )
    )

    assert result.text.strip()
    assert result.provider == CLOVA_OCR_PROVIDER


def _mime_type_for_path(path: Path) -> str:
    """Infer an accepted image MIME type from a smoke image path.

    Args:
        path: Local smoke image path.

    Returns:
        Image MIME type.
    """
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"

"""PaddleOCR fallback provider tests."""

from __future__ import annotations

import pytest
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.providers.paddle import PADDLE_OCR_PROVIDER, PaddleOCRAdapter


class _FakePaddlePredictor:
    """Fake PaddleOCR predictor."""

    def __init__(self, prediction: object) -> None:
        self.prediction = prediction
        self.received_path: str | None = None

    def predict(self, image_path: str) -> object:
        """Capture the image path and return configured prediction data.

        Args:
            image_path: Temporary image path.

        Returns:
            Fake prediction data.
        """
        self.received_path = image_path
        return self.prediction


def _image_input() -> OCRImageInput:
    """Return a minimal OCR image input.

    Returns:
        OCR image input.
    """
    return OCRImageInput(
        image_bytes=b"fake-png-bytes",
        mime_type="image/png",
        width=10,
        height=8,
    )


@pytest.mark.asyncio
async def test_paddle_adapter_flattens_prediction_text_and_scores() -> None:
    """Verify PaddleOCR fallback normalizes common 3.x prediction fields."""
    predictor = _FakePaddlePredictor(
        [{"rec_texts": ["비타민 D 1000", "비타민 D 25 ug"], "rec_scores": [0.92, 0.88]}]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input())

    assert result.provider == PADDLE_OCR_PROVIDER
    assert result.text == "비타민 D 1000\n비타민 D 25 ug"
    assert result.confidence == pytest.approx(0.90)
    assert predictor.received_path is not None


@pytest.mark.asyncio
async def test_paddle_adapter_requires_local_ocr_gate() -> None:
    """Verify local OCR stays fail-closed by default."""
    adapter = PaddleOCRAdapter(Settings(_env_file=None), predictor=_FakePaddlePredictor([]))

    with pytest.raises(OCRError, match="ENABLE_LOCAL_OCR"):
        await adapter.extract_text(_image_input())


@pytest.mark.asyncio
async def test_paddle_adapter_rejects_low_confidence_prediction() -> None:
    """Verify weak local OCR output escalates instead of being accepted."""
    adapter = PaddleOCRAdapter(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            local_ocr_confidence_threshold=0.75,
        ),
        predictor=_FakePaddlePredictor([{"rec_texts": ["흐린 텍스트"], "rec_scores": [0.50]}]),
    )

    with pytest.raises(OCRError, match="confidence"):
        await adapter.extract_text(_image_input())

"""PaddleOCR fallback provider tests."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.providers.paddle import (
    PADDLE_OCR_PROVIDER,
    PaddleOCRAdapter,
    _get_paddle_predictor,
)


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


class _FailingPaddlePredictor:
    """Fake PaddleOCR predictor raising a provider exception."""

    def predict(self, image_path: str) -> object:  # noqa: ARG002
        """Raise a fake provider failure.

        Args:
            image_path: Temporary image path.

        Raises:
            RuntimeError: Always raised to simulate provider failure.
        """
        raise RuntimeError("provider internals should stay hidden")


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
    """Verify the adapter fails closed when ENABLE_LOCAL_OCR is explicitly disabled."""
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=False),
        predictor=_FakePaddlePredictor([]),
    )

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


@pytest.mark.asyncio
async def test_paddle_adapter_wraps_provider_prediction_failure() -> None:
    """Verify provider exceptions become bounded OCR errors."""
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=_FailingPaddlePredictor(),
    )

    with pytest.raises(OCRError, match="provider prediction failed") as exc_info:
        await adapter.extract_text(_image_input())

    assert "provider internals" not in str(exc_info.value)


class _RecordingFakePaddleOCR:
    """Fake PaddleOCR class capturing constructor kwargs for assertions."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def predict(self, image_path: str) -> object:  # noqa: ARG002
        """Return an empty prediction for kwarg-focused tests."""
        return []


@pytest.fixture
def _fake_paddleocr_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the ``paddleocr`` module with a kwargs-recording fake.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    The lru_cache around ``_get_paddle_predictor`` is cleared before and after
    so toggle states do not leak between tests.
    """
    fake_module = types.ModuleType("paddleocr")
    fake_module.PaddleOCR = _RecordingFakePaddleOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)
    _get_paddle_predictor.cache_clear()
    yield
    _get_paddle_predictor.cache_clear()


def test_predictor_forwards_textline_orientation_when_disabled(
    _fake_paddleocr_module: None,
) -> None:
    """Verify the default settings keep PaddleOCR textline orientation off."""
    predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        use_textline_orientation=False,
    )
    assert predictor.kwargs["use_textline_orientation"] is False  # type: ignore[attr-defined]


def test_predictor_forwards_textline_orientation_when_enabled(
    _fake_paddleocr_module: None,
) -> None:
    """Verify operators can enable textline orientation for isolation runs."""
    predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        use_textline_orientation=True,
    )
    assert predictor.kwargs["use_textline_orientation"] is True  # type: ignore[attr-defined]


def test_predictor_caches_orientation_toggle_separately(
    _fake_paddleocr_module: None,
) -> None:
    """Verify the toggle is part of the cache key so flipped runs do not collide."""
    off = _get_paddle_predictor(
        language="korean",
        device=None,
        use_textline_orientation=False,
    )
    on = _get_paddle_predictor(
        language="korean",
        device=None,
        use_textline_orientation=True,
    )
    assert off is not on


@pytest.mark.asyncio
async def test_paddle_adapter_propagates_textline_orientation_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the adapter forwards the settings flag into the cached predictor."""
    fake_module = types.ModuleType("paddleocr")
    fake_module.PaddleOCR = _RecordingFakePaddleOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)
    _get_paddle_predictor.cache_clear()
    try:
        adapter = PaddleOCRAdapter(
            Settings(
                _env_file=None,
                enable_local_ocr=True,
                local_ocr_use_textline_orientation=True,
            )
        )
        with pytest.raises(OCRError, match="readable text"):
            await adapter.extract_text(_image_input())

        predictor = _get_paddle_predictor(
            language="korean",
            device=None,
            use_textline_orientation=True,
        )
        assert predictor.kwargs["use_textline_orientation"] is True  # type: ignore[attr-defined]
    finally:
        _get_paddle_predictor.cache_clear()

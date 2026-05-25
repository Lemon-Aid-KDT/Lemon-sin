"""PaddleOCR fallback provider tests."""

from __future__ import annotations

import sys
import types
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.providers.paddle import (
    PADDLE_MOBILE_TEXT_DETECTION_MODEL,
    PADDLE_OCR_PROVIDER,
    PADDLE_SERVER_TEXT_DETECTION_MODEL,
    PADDLE_SERVER_TEXT_RECOGNITION_MODEL,
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


class _ReadingFakePaddlePredictor(_FakePaddlePredictor):
    """Fake predictor that records temporary OCR input bytes."""

    def __init__(self, prediction: object) -> None:
        """Initialize prediction and captured-byte storage."""
        super().__init__(prediction)
        self.received_bytes: bytes | None = None

    def predict(self, image_path: str) -> object:
        """Capture temporary file bytes and return configured prediction data."""
        self.received_path = image_path
        with Path(image_path).open("rb") as file:
            self.received_bytes = file.read()
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


def _valid_png_image_input() -> OCRImageInput:
    """Return a valid PNG OCR image input for preprocessing tests."""
    buffer = BytesIO()
    Image.new("RGB", (20, 12), (240, 240, 240)).save(buffer, format="PNG")
    return OCRImageInput(
        image_bytes=buffer.getvalue(),
        mime_type="image/png",
        width=20,
        height=12,
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
async def test_paddle_adapter_preprocess_mode_reencodes_temp_png_only() -> None:
    """Verify opt-in preprocessing changes only the local temporary OCR input."""
    predictor = _ReadingFakePaddlePredictor([{"rec_texts": ["아연 10 mg"], "rec_scores": [0.91]}])
    adapter = PaddleOCRAdapter(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            local_ocr_preprocess_mode="autocontrast",
        ),
        predictor=predictor,
    )

    result = await adapter.extract_text(_valid_png_image_input())

    assert result.text == "아연 10 mg"
    assert predictor.received_path is not None
    assert predictor.received_path.endswith(".png")
    assert predictor.received_bytes is not None
    assert predictor.received_bytes.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_paddle_adapter_preprocess_failure_is_bounded() -> None:
    """Verify invalid images fail with a bounded preprocessing error."""
    adapter = PaddleOCRAdapter(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            local_ocr_preprocess_mode="grayscale_autocontrast",
        ),
        predictor=_FakePaddlePredictor([]),
    )

    with pytest.raises(OCRError, match="preprocessing failed"):
        await adapter.extract_text(_image_input())


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
    assert predictor.kwargs["text_detection_model_name"] == PADDLE_MOBILE_TEXT_DETECTION_MODEL  # type: ignore[attr-defined]
    assert predictor.kwargs["text_recognition_model_name"] == "korean_PP-OCRv5_mobile_rec"  # type: ignore[attr-defined]


def test_predictor_wraps_import_time_provider_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify PaddleOCR import-time runtime failures become bounded OCR errors.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """

    def _raise_permission_error(module_name: str) -> object:
        """Raise a runtime import failure for the requested module.

        Args:
            module_name: Imported module name.

        Raises:
            PermissionError: Simulated provider cache permission failure.
        """
        raise PermissionError(f"{module_name} cache unavailable")

    monkeypatch.setattr("src.ocr.providers.paddle.import_module", _raise_permission_error)
    _get_paddle_predictor.cache_clear()
    try:
        with pytest.raises(OCRError, match="provider initialization"):
            _get_paddle_predictor(language="korean", device=None)
    finally:
        _get_paddle_predictor.cache_clear()


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


def test_predictor_server_detection_profile_keeps_korean_mobile_recognition(
    _fake_paddleocr_module: None,
) -> None:
    """Verify server detection can be isolated from Korean recognition changes."""
    predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        model_profile="server_detection",
    )

    assert predictor.kwargs["text_detection_model_name"] == PADDLE_SERVER_TEXT_DETECTION_MODEL  # type: ignore[attr-defined]
    assert predictor.kwargs["text_recognition_model_name"] == "korean_PP-OCRv5_mobile_rec"  # type: ignore[attr-defined]


def test_predictor_server_profile_uses_server_detection_and_recognition(
    _fake_paddleocr_module: None,
) -> None:
    """Verify the explicit server profile changes both PaddleOCR model stages."""
    predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        model_profile="server",
    )

    assert predictor.kwargs["text_detection_model_name"] == PADDLE_SERVER_TEXT_DETECTION_MODEL  # type: ignore[attr-defined]
    assert predictor.kwargs["text_recognition_model_name"] == PADDLE_SERVER_TEXT_RECOGNITION_MODEL  # type: ignore[attr-defined]


def test_predictor_cache_separates_model_profiles(
    _fake_paddleocr_module: None,
) -> None:
    """Verify profile comparisons do not reuse a prior cached predictor."""
    mobile_predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        model_profile="mobile",
    )
    server_detection_predictor = _get_paddle_predictor(
        language="korean",
        device=None,
        model_profile="server_detection",
    )

    assert mobile_predictor is not server_detection_predictor


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

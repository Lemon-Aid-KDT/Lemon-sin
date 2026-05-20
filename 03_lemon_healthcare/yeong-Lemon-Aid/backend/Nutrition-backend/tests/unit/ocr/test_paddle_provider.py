"""PaddleOCR fallback provider tests."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import ClassVar

import pytest
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.providers.paddle import PADDLE_OCR_PROVIDER, PaddleOCRAdapter, _get_paddle_predictor
from src.parsing.layout_parser import parse_label_layout
from src.services.supplement_layout_context import build_supplement_layout_context


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


class _CapturingPaddleOCR:
    """Fake PaddleOCR class that captures initializer kwargs."""

    kwargs: ClassVar[dict[str, object]] = {}

    def __init__(self, **kwargs: object) -> None:
        """Capture initializer keyword arguments.

        Args:
            kwargs: PaddleOCR initializer kwargs.
        """
        self.__class__.kwargs = kwargs

    def predict(self, image_path: str) -> object:
        """Return a minimal OCR prediction.

        Args:
            image_path: Temporary image path.

        Returns:
            Fake PaddleOCR prediction.
        """
        _ = image_path
        return [{"rec_texts": ["비타민 D 25 ug"], "rec_scores": [0.95]}]


class _JsonPropertyPrediction:
    """Fake PaddleOCR result object with a ``json`` mapping property."""

    def __init__(self, prediction: object) -> None:
        """Initialize the fake object.

        Args:
            prediction: Prediction payload exposed through ``json``.
        """
        self.json = prediction


class _JsonMethodPrediction:
    """Fake PaddleOCR result object with a callable ``json()`` method."""

    def __init__(self, prediction: object) -> None:
        """Initialize the fake object.

        Args:
            prediction: Prediction payload returned by ``json()``.
        """
        self._prediction = prediction

    def json(self) -> object:
        """Return the configured prediction payload.

        Returns:
            Fake prediction payload.
        """
        return self._prediction


class _ToDictPrediction:
    """Fake PaddleOCR result object with a callable ``to_dict()`` method."""

    def __init__(self, prediction: object) -> None:
        """Initialize the fake object.

        Args:
            prediction: Prediction payload returned by ``to_dict()``.
        """
        self._prediction = prediction

    def to_dict(self) -> object:
        """Return the configured prediction payload.

        Returns:
            Fake prediction payload.
        """
        return self._prediction


def _image_input(*, width: int = 10, height: int = 8) -> OCRImageInput:
    """Return a minimal OCR image input.

    Args:
        width: Image width for page metadata.
        height: Image height for page metadata.

    Returns:
        OCR image input.
    """
    return OCRImageInput(
        image_bytes=b"fake-png-bytes",
        mime_type="image/png",
        width=width,
        height=height,
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
    assert result.pages == ()
    assert predictor.received_path is not None


@pytest.mark.asyncio
async def test_paddle_adapter_builds_pages_from_rec_polys() -> None:
    """Verify PaddleOCR recognition polygons populate OCRResult pages."""
    predictor = _FakePaddlePredictor(
        [
            {
                "rec_texts": ["영양·기능정보", "비타민 D", "25 ug"],
                "rec_scores": [0.96, 0.91, 0.93],
                "rec_polys": [
                    [[10, 10], [120, 10], [120, 24], [10, 24]],
                    [[10, 40], [80, 40], [80, 55], [10, 55]],
                    [[150, 40], [190, 40], [190, 55], [150, 55]],
                ],
            }
        ]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input(width=240, height=120))

    assert result.text == "영양·기능정보\n비타민 D\n25 ug"
    assert result.confidence == pytest.approx(0.9333333333)
    assert len(result.pages) == 1
    page = result.pages[0]
    assert page.width == 240
    assert page.height == 120
    words = page.blocks[0].paragraphs[0].words
    assert [word.text for word in words] == ["영양·기능정보", "비타민 D", "25 ug"]
    assert words[0].bounding_box is not None
    assert words[0].bounding_box.vertices[0].x == 10
    assert words[0].bounding_box.vertices[0].y == 10

    layout = parse_label_layout(result)
    context = build_supplement_layout_context(result, Settings(_env_file=None))
    assert layout.sections[0].section_type == "nutrition_function_info"
    assert context.layout_available is True
    assert context.parser_input_text is not None
    assert "cell=sec-000:r001:c000: 비타민 D" in context.parser_input_text


@pytest.mark.asyncio
async def test_paddle_adapter_falls_back_to_dt_polys_when_rec_polys_missing() -> None:
    """Verify detection polygons are used only when recognition polygons are absent."""
    predictor = _FakePaddlePredictor(
        [
            {
                "rec_texts": ["섭취방법"],
                "rec_scores": [0.89],
                "dt_polys": [[[8, 12], [70, 12], [70, 28], [8, 28]]],
            }
        ]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input(width=100, height=60))

    words = result.pages[0].blocks[0].paragraphs[0].words
    assert result.text == "섭취방법"
    assert words[0].bounding_box is not None
    assert words[0].bounding_box.vertices[1].x == 70


@pytest.mark.asyncio
async def test_paddle_adapter_reads_common_object_result_shapes() -> None:
    """Verify ``json``, ``json()``, and ``to_dict()`` provider objects are handled."""
    predictor = _FakePaddlePredictor(
        [
            _JsonPropertyPrediction({"res": {"rec_texts": ["A"], "rec_scores": [0.91]}}),
            _JsonMethodPrediction({"res": {"rec_texts": ["B"], "rec_scores": [0.92]}}),
            _ToDictPrediction({"res": {"rec_texts": ["C"], "rec_scores": [0.93]}}),
        ]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input())

    assert result.text == "A\nB\nC"
    assert result.confidence == pytest.approx(0.92)
    assert result.pages == ()


@pytest.mark.asyncio
async def test_paddle_adapter_degrades_layout_when_polygon_invalid() -> None:
    """Verify invalid polygons do not fail otherwise usable local OCR text."""
    predictor = _FakePaddlePredictor(
        [
            {
                "rec_texts": ["흐린 성분표"],
                "rec_scores": [0.90],
                "rec_polys": [[[-1, 10], [60, 10], [60, 20], [-1, 20]]],
            }
        ]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input(width=100, height=60))

    assert result.text == "흐린 성분표"
    assert result.confidence == pytest.approx(0.90)
    assert result.pages == ()


@pytest.mark.asyncio
async def test_paddle_adapter_degrades_mismatched_score_and_polygon_lengths() -> None:
    """Verify index mismatches keep text OCR while partially preserving valid boxes."""
    predictor = _FakePaddlePredictor(
        [
            {
                "rec_texts": ["아연", "아연"],
                "rec_scores": [0.94],
                "rec_polys": [[[10, 10], [40, 10], [40, 24], [10, 24]]],
            }
        ]
    )
    adapter = PaddleOCRAdapter(
        Settings(_env_file=None, enable_local_ocr=True),
        predictor=predictor,
    )

    result = await adapter.extract_text(_image_input(width=90, height=50))

    assert result.text == "아연\n아연"
    assert result.confidence == pytest.approx(0.94)
    words = result.pages[0].blocks[0].paragraphs[0].words
    assert [word.text for word in words] == ["아연", "아연"]
    assert words[0].bounding_box is not None
    assert words[1].bounding_box is None


@pytest.mark.asyncio
async def test_paddle_adapter_requires_local_ocr_gate() -> None:
    """Verify local OCR stays fail-closed when explicitly disabled."""
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
async def test_paddle_adapter_passes_finetuned_model_settings_to_paddleocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify fine-tuned model settings use PaddleOCR 3.x parameter names."""
    _get_paddle_predictor.cache_clear()
    monkeypatch.setitem(
        sys.modules,
        "paddleocr",
        SimpleNamespace(PaddleOCR=_CapturingPaddleOCR),
    )
    adapter = PaddleOCRAdapter(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            local_ocr_text_recognition_model_dir="/models/rec",
            local_ocr_text_detection_model_dir="/models/det",
            local_ocr_text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
            local_ocr_text_detection_model_name="PP-OCRv5_server_det",
        )
    )

    result = await adapter.extract_text(_image_input())

    assert result.provider == PADDLE_OCR_PROVIDER
    assert _CapturingPaddleOCR.kwargs["text_recognition_model_dir"] == "/models/rec"
    assert _CapturingPaddleOCR.kwargs["text_detection_model_dir"] == "/models/det"
    assert _CapturingPaddleOCR.kwargs["text_recognition_model_name"] == "korean_PP-OCRv5_mobile_rec"
    assert _CapturingPaddleOCR.kwargs["text_detection_model_name"] == "PP-OCRv5_server_det"
    assert "rec_model_dir" not in _CapturingPaddleOCR.kwargs
    assert "det_model_dir" not in _CapturingPaddleOCR.kwargs
    _get_paddle_predictor.cache_clear()

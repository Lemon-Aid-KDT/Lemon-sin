"""Optional PaddleOCR local fallback provider for supplement labels."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, cast

from src.config import Settings
from src.ocr.base import (
    OCRAdapter,
    OCRBlock,
    OCRBoundingPoly,
    OCRError,
    OCRImageInput,
    OCRPage,
    OCRParagraph,
    OCRResult,
    OCRVertex,
    OCRWord,
)

PADDLE_OCR_PROVIDER = "paddleocr_local"
PADDLE_MOBILE_TEXT_DETECTION_MODEL = "PP-OCRv5_mobile_det"
PADDLE_MOBILE_TEXT_RECOGNITION_MODELS = {
    "en": "en_PP-OCRv5_mobile_rec",
    "korean": "korean_PP-OCRv5_mobile_rec",
}
PADDLE_TEXT_KEYS = {"text", "inferText"}
PADDLE_SCORE_KEYS = {"score", "confidence", "inferConfidence"}
LEGACY_TEXT_SCORE_PAIR_LENGTH = 2
MIN_POLYGON_COORDINATES = 2
MIN_POLYGON_VERTICES = 2


class PaddlePredictor(Protocol):
    """Protocol for the small PaddleOCR API surface used by this adapter."""

    def predict(self, image_path: str) -> Any:
        """Run OCR prediction for one local image path.

        Args:
            image_path: Local image path.

        Returns:
            Provider-specific prediction object.
        """
        ...


class PaddleOCRAdapter(OCRAdapter):
    """Local PaddleOCR fallback adapter.

    The adapter is optional and lazy-loads PaddleOCR only when the fallback path is
    explicitly enabled. It writes request bytes to a temporary file because the
    official PaddleOCR 3.x pipeline examples use file-path based ``predict`` calls.
    """

    def __init__(self, settings: Settings, predictor: PaddlePredictor | None = None) -> None:
        """Initialize the adapter.

        Args:
            settings: Runtime settings.
            predictor: Optional fake or prebuilt predictor for tests.
        """
        self._settings = settings
        self._predictor = predictor

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Extract text with a local PaddleOCR predictor.

        Args:
            image: Validated OCR image input.

        Returns:
            OCR result with joined text and averaged confidence when available.

        Raises:
            OCRError: If local OCR is disabled, unavailable, or returns no text.
        """
        if not self._settings.enable_local_ocr:
            raise OCRError("ENABLE_LOCAL_OCR=true is required for PaddleOCR fallback.")

        predictor = self._predictor or _get_paddle_predictor(
            language=self._settings.local_ocr_language,
            device=self._settings.local_ocr_device,
            use_textline_orientation=self._settings.local_ocr_use_textline_orientation,
        )
        suffix = _suffix_for_mime_type(image.mime_type)
        with TemporaryDirectory(prefix="lemon-paddleocr-") as temporary_directory:
            image_path = Path(temporary_directory) / f"supplement_label{suffix}"
            try:
                image_path.write_bytes(image.image_bytes)
            except OSError as exc:
                raise OCRError("PaddleOCR temporary image write failed.") from exc
            try:
                prediction = predictor.predict(str(image_path))
            except Exception as exc:
                raise OCRError("PaddleOCR provider prediction failed.") from exc

        fragments, scores = _collect_text_and_scores(prediction)
        text = "\n".join(fragments).strip()
        if not text:
            raise OCRError("PaddleOCR returned no readable text.")

        confidence = _average_scores(scores)
        if confidence is not None and confidence < self._settings.local_ocr_confidence_threshold:
            raise OCRError("PaddleOCR confidence is below LOCAL_OCR_CONFIDENCE_THRESHOLD.")
        return OCRResult(
            text=text,
            provider=PADDLE_OCR_PROVIDER,
            confidence=confidence,
            pages=_collect_layout_pages(prediction),
        )


@lru_cache(maxsize=8)
def _get_paddle_predictor(
    *,
    language: str,
    device: str | None,
    use_textline_orientation: bool = False,
) -> PaddlePredictor:
    """Load and cache the PaddleOCR predictor.

    Args:
        language: OCR language setting.
        device: Optional runtime device such as ``cpu`` or ``gpu:0``.
        use_textline_orientation: Whether to enable PaddleOCR's textline
            orientation classifier. Cached separately per toggle so isolation
            measurements can flip the flag without polluting the prior cache.

    Returns:
        PaddleOCR predictor.

    Raises:
        OCRError: If PaddleOCR is not installed or cannot be initialized.
    """
    try:
        paddle_ocr_class = cast(Any, import_module("paddleocr")).PaddleOCR
    except ImportError as exc:
        raise OCRError("PaddleOCR is not installed. Install backend .[ocr-local].") from exc

    kwargs: dict[str, object] = {
        "lang": language,
        "text_detection_model_name": PADDLE_MOBILE_TEXT_DETECTION_MODEL,
        "text_recognition_model_name": _mobile_text_recognition_model_name(language),
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": use_textline_orientation,
    }
    if device:
        kwargs["device"] = device
    try:
        return cast(PaddlePredictor, paddle_ocr_class(**kwargs))
    except Exception as exc:
        raise OCRError("PaddleOCR predictor initialization failed.") from exc


def _mobile_text_recognition_model_name(language: str) -> str:
    """Return a lightweight PP-OCRv5 recognition model for the OCR language.

    Args:
        language: PaddleOCR language code.

    Returns:
        Mobile recognition model name.
    """
    return PADDLE_MOBILE_TEXT_RECOGNITION_MODELS.get(language, "PP-OCRv5_mobile_rec")


def _suffix_for_mime_type(mime_type: str) -> str:
    """Return a safe image suffix for a MIME type.

    Args:
        mime_type: Validated image MIME type.

    Returns:
        File suffix used for the temporary image.
    """
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def _collect_text_and_scores(value: object) -> tuple[list[str], list[float]]:
    """Collect OCR text fragments and confidence scores from provider output.

    Args:
        value: PaddleOCR output in dict/list/object form.

    Returns:
        Text fragments and bounded scores.
    """
    fragments: list[str] = []
    scores: list[float] = []
    _walk_prediction(value, fragments=fragments, scores=scores)
    return _dedupe_preserve_order(fragments), scores


def _collect_layout_pages(value: object) -> tuple[OCRPage, ...]:
    """Collect coordinate-bearing OCR pages from PaddleOCR output.

    Args:
        value: PaddleOCR output in dict/list/object form.

    Returns:
        OCR pages built from text-line polygons, if present.
    """
    pages: list[OCRPage] = []
    _walk_prediction_for_pages(value, pages=pages)
    return tuple(pages)


def _walk_prediction_for_pages(value: object, *, pages: list[OCRPage]) -> None:
    """Recursively walk PaddleOCR output looking for text-line polygons.

    Args:
        value: Provider output fragment.
        pages: Mutable page accumulator.
    """
    if isinstance(value, dict):
        page = _page_from_mapping(value)
        if page is not None:
            pages.append(page)
        for nested_value in value.values():
            _walk_prediction_for_pages(nested_value, pages=pages)
        return

    if isinstance(value, list | tuple):
        for item in value:
            _walk_prediction_for_pages(item, pages=pages)
        return

    json_value = getattr(value, "json", None)
    if isinstance(json_value, dict):
        _walk_prediction_for_pages(json_value, pages=pages)
        return
    if callable(json_value):
        try:
            parsed = json_value()
        except Exception:
            parsed = None
        if parsed is not None:
            _walk_prediction_for_pages(parsed, pages=pages)
            return

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            parsed = to_dict()
        except Exception:
            parsed = None
        if parsed is not None:
            _walk_prediction_for_pages(parsed, pages=pages)


def _page_from_mapping(value: dict[object, object]) -> OCRPage | None:
    """Build one OCR page from common PaddleOCR 3.x result fields.

    Args:
        value: Result mapping.

    Returns:
        OCR page, or ``None`` when required text/polygon fields are missing.
    """
    raw_texts = value.get("rec_texts")
    raw_polys = value.get("rec_polys")
    if not isinstance(raw_texts, list):
        return None
    polygons = _polygon_values(raw_polys)
    if not polygons:
        return None
    scores = _score_values(
        value.get("rec_scores") if isinstance(value.get("rec_scores"), list) else []
    )
    words: list[OCRWord] = []
    for index, text in enumerate(raw_texts):
        if not isinstance(text, str) or not text.strip() or index >= len(polygons):
            continue
        poly = _bounding_poly_from_points(polygons[index])
        if poly is None:
            continue
        words.append(
            OCRWord(
                text=text.strip(),
                bounding_box=poly,
                confidence=scores[index] if index < len(scores) else None,
            )
        )
    if not words:
        return None
    return OCRPage(
        blocks=(
            OCRBlock(
                paragraphs=(OCRParagraph(words=tuple(words)),),
                block_type="textline",
            ),
        ),
    )


def _polygon_values(value: object) -> list[object]:
    """Return a list-like polygon collection from PaddleOCR output.

    Args:
        value: Candidate polygon container.

    Returns:
        Polygon values.
    """
    if isinstance(value, list | tuple):
        return list(value)
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            converted = tolist()
        except Exception:
            return []
        if isinstance(converted, list):
            return converted
    return []


def _bounding_poly_from_points(value: object) -> OCRBoundingPoly | None:
    """Build an OCR bounding polygon from a PaddleOCR polygon value.

    Args:
        value: Candidate point sequence.

    Returns:
        Bounding polygon, or ``None`` when points are malformed.
    """
    points = _polygon_values(value)
    vertices: list[OCRVertex] = []
    for point in points:
        coordinates = _polygon_values(point)
        if len(coordinates) < MIN_POLYGON_COORDINATES:
            return None
        x, y = coordinates[:MIN_POLYGON_COORDINATES]
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            return None
        vertices.append(OCRVertex(x=float(x), y=float(y)))
    return (
        OCRBoundingPoly(vertices=tuple(vertices)) if len(vertices) >= MIN_POLYGON_VERTICES else None
    )


def _walk_prediction(value: object, *, fragments: list[str], scores: list[float]) -> None:
    """Recursively walk common PaddleOCR result shapes.

    Args:
        value: Provider output fragment.
        fragments: Accumulator for text fragments.
        scores: Accumulator for confidence scores.
    """
    if isinstance(value, dict):
        _collect_from_mapping(value, fragments=fragments, scores=scores)
        for nested_value in value.values():
            _walk_prediction(nested_value, fragments=fragments, scores=scores)
        return

    if isinstance(value, list | tuple):
        _collect_legacy_tuple(value, fragments=fragments, scores=scores)
        for item in value:
            _walk_prediction(item, fragments=fragments, scores=scores)
        return

    json_value = getattr(value, "json", None)
    if isinstance(json_value, dict):
        _walk_prediction(json_value, fragments=fragments, scores=scores)
        return
    if callable(json_value):
        try:
            parsed = json_value()
        except Exception:
            parsed = None
        if parsed is not None:
            _walk_prediction(parsed, fragments=fragments, scores=scores)
            return

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            parsed = to_dict()
        except Exception:
            parsed = None
        if parsed is not None:
            _walk_prediction(parsed, fragments=fragments, scores=scores)


def _collect_from_mapping(
    value: dict[object, object],
    *,
    fragments: list[str],
    scores: list[float],
) -> None:
    """Collect text and confidence fields from a mapping.

    Args:
        value: Result mapping.
        fragments: Accumulator for text fragments.
        scores: Accumulator for confidence scores.
    """
    for key, nested_value in value.items():
        if key in {"rec_texts", "texts"} and isinstance(nested_value, list):
            fragments.extend(item for item in nested_value if isinstance(item, str))
        elif key in PADDLE_TEXT_KEYS and isinstance(nested_value, str):
            fragments.append(nested_value)
        elif key in {"rec_scores", "scores"} and isinstance(nested_value, list):
            scores.extend(_score_values(nested_value))
        elif key in PADDLE_SCORE_KEYS:
            scores.extend(_score_values([nested_value]))


def _collect_legacy_tuple(
    value: Sequence[object],
    *,
    fragments: list[str],
    scores: list[float],
) -> None:
    """Collect legacy PaddleOCR tuple values such as ``(text, score)``.

    Args:
        value: Sequence value.
        fragments: Accumulator for text fragments.
        scores: Accumulator for confidence scores.
    """
    if len(value) != LEGACY_TEXT_SCORE_PAIR_LENGTH:
        return
    text_candidate, score_candidate = value
    if isinstance(text_candidate, str):
        fragments.append(text_candidate)
        scores.extend(_score_values([score_candidate]))


def _score_values(values: list[object]) -> list[float]:
    """Return bounded score floats from raw values.

    Args:
        values: Candidate values.

    Returns:
        Values in the inclusive range 0.0 to 1.0.
    """
    scores: list[float] = []
    for value in values:
        if isinstance(value, int | float) and 0 <= value <= 1:
            scores.append(float(value))
    return scores


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Trim and deduplicate text fragments.

    Args:
        values: Raw text fragments.

    Returns:
        Non-empty fragments in first-seen order.
    """
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        deduped.append(stripped)
        seen.add(stripped)
    return deduped


def _average_scores(scores: list[float]) -> float | None:
    """Average scores when present.

    Args:
        scores: Bounded confidence scores.

    Returns:
        Average score or None.
    """
    if not scores:
        return None
    return sum(scores) / len(scores)

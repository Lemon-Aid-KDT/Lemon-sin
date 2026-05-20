"""Optional PaddleOCR local fallback provider for supplement labels."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from numbers import Real
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, Protocol, cast

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
PADDLE_TEXT_KEYS = {"text", "inferText", "rec_text"}
PADDLE_SCORE_KEYS = {"score", "confidence", "inferConfidence", "rec_score"}
PADDLE_LINE_TEXT_KEYS = ("rec_texts", "texts")
PADDLE_LINE_SCORE_KEYS = ("rec_scores", "scores")
PADDLE_RECOGNITION_POLYGON_KEYS = ("rec_polys",)
PADDLE_DETECTION_POLYGON_KEYS = ("dt_polys", "det_polys")
LEGACY_TEXT_SCORE_PAIR_LENGTH = 2
MIN_POLYGON_VERTICES = 2
VERTEX_COORDINATE_PAIR_LENGTH = 2

PaddleLineSource = Literal["rec_polys", "dt_polys", "legacy", "none"]


@dataclass(frozen=True)
class _PaddleLine:
    """One provider-normalized PaddleOCR line.

    Args:
        text: Recognized text in provider order.
        confidence: Optional confidence from the same PaddleOCR index.
        polygon: Optional line polygon from ``rec_polys`` or ``dt_polys``.
        source: Stable source label for layout degradation tests.
    """

    text: str
    confidence: float | None
    polygon: OCRBoundingPoly | None
    source: PaddleLineSource


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
            engine=self._settings.local_ocr_engine,
            use_doc_orientation_classify=self._settings.local_ocr_use_doc_orientation_classify,
            use_doc_unwarping=self._settings.local_ocr_use_doc_unwarping,
            use_textline_orientation=self._settings.local_ocr_use_textline_orientation,
            paddlex_config=self._settings.local_ocr_paddlex_config,
            text_recognition_model_dir=self._settings.local_ocr_text_recognition_model_dir,
            text_detection_model_dir=self._settings.local_ocr_text_detection_model_dir,
            text_recognition_model_name=self._settings.local_ocr_text_recognition_model_name,
            text_detection_model_name=self._settings.local_ocr_text_detection_model_name,
        )
        suffix = _suffix_for_mime_type(image.mime_type)
        with TemporaryDirectory(prefix="lemon-paddleocr-") as temporary_directory:
            image_path = Path(temporary_directory) / f"supplement_label{suffix}"
            image_path.write_bytes(image.image_bytes)
            prediction = predictor.predict(str(image_path))

        lines, _warnings = _extract_paddle_lines(prediction)
        text = "\n".join(line.text for line in lines).strip()
        if not text:
            raise OCRError("PaddleOCR returned no readable text.")

        scores = [line.confidence for line in lines if line.confidence is not None]
        confidence = _average_scores(scores)
        if confidence is not None and confidence < self._settings.local_ocr_confidence_threshold:
            raise OCRError("PaddleOCR confidence is below LOCAL_OCR_CONFIDENCE_THRESHOLD.")
        return OCRResult(
            text=text,
            provider=PADDLE_OCR_PROVIDER,
            confidence=confidence,
            pages=_build_paddle_pages(lines, image),
        )


@lru_cache(maxsize=4)
def _get_paddle_predictor(
    *,
    language: str,
    device: str | None,
    engine: str | None,
    use_doc_orientation_classify: bool,
    use_doc_unwarping: bool,
    use_textline_orientation: bool,
    paddlex_config: str | None,
    text_recognition_model_dir: str | None,
    text_detection_model_dir: str | None,
    text_recognition_model_name: str | None,
    text_detection_model_name: str | None,
) -> PaddlePredictor:
    """Load and cache the PaddleOCR predictor.

    Args:
        language: OCR language setting.
        device: Optional runtime device such as ``cpu`` or ``gpu:0``.
        engine: Optional PaddleOCR 3.x inference engine.
        use_doc_orientation_classify: Whether to run document orientation classification.
        use_doc_unwarping: Whether to run document unwarping.
        use_textline_orientation: Whether to run textline orientation classification.
        paddlex_config: Optional PaddleX YAML config path.
        text_recognition_model_dir: Optional fine-tuned recognition inference model directory.
        text_detection_model_dir: Optional fine-tuned detection inference model directory.
        text_recognition_model_name: Optional recognition model name.
        text_detection_model_name: Optional detection model name.

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
        "use_doc_orientation_classify": use_doc_orientation_classify,
        "use_doc_unwarping": use_doc_unwarping,
        "use_textline_orientation": use_textline_orientation,
    }
    if device:
        kwargs["device"] = device
    if engine:
        kwargs["engine"] = engine
    if paddlex_config:
        kwargs["paddlex_config"] = paddlex_config
    if text_recognition_model_dir:
        kwargs["text_recognition_model_dir"] = text_recognition_model_dir
    if text_detection_model_dir:
        kwargs["text_detection_model_dir"] = text_detection_model_dir
    if text_recognition_model_name:
        kwargs["text_recognition_model_name"] = text_recognition_model_name
    if text_detection_model_name:
        kwargs["text_detection_model_name"] = text_detection_model_name
    try:
        return cast(PaddlePredictor, paddle_ocr_class(**kwargs))
    except Exception as exc:
        raise OCRError("PaddleOCR predictor initialization failed.") from exc


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


def _extract_paddle_lines(value: object) -> tuple[list[_PaddleLine], list[str]]:
    """Extract aligned PaddleOCR line text, scores, and polygons.

    Args:
        value: PaddleOCR output in object, mapping, list, or legacy tuple form.

    Returns:
        Provider-normalized lines and safe warning codes. Raw provider payloads
        are intentionally not returned.
    """
    warnings: list[str] = []
    snapshots = _collect_paddle_snapshots(value)
    lines: list[_PaddleLine] = []
    for snapshot in snapshots:
        lines.extend(_lines_from_mapping(snapshot, warnings))
    if lines:
        return lines, warnings

    fragments, scores = _collect_text_and_scores(value)
    return (
        [
            _PaddleLine(
                text=fragment,
                confidence=scores[index] if index < len(scores) else None,
                polygon=None,
                source="legacy",
            )
            for index, fragment in enumerate(fragments)
        ],
        warnings,
    )


def _collect_paddle_snapshots(value: object) -> list[Mapping[object, object]]:
    """Collect mappings that can contain index-aligned PaddleOCR line fields.

    Args:
        value: Provider output root.

    Returns:
        Mappings with ``rec_texts``/``texts`` style fields.
    """
    snapshots: list[Mapping[object, object]] = []
    _walk_paddle_snapshots(value, snapshots=snapshots, visited=set())
    return snapshots


def _walk_paddle_snapshots(
    value: object,
    *,
    snapshots: list[Mapping[object, object]],
    visited: set[int],
) -> None:
    """Walk provider output looking for mapping snapshots.

    Args:
        value: Current output fragment.
        snapshots: Mutable snapshot accumulator.
        visited: Object ids already visited to avoid cyclic provider objects.
    """
    value_id = id(value)
    if value_id in visited:
        return
    visited.add(value_id)

    if isinstance(value, Mapping):
        if _mapping_has_line_fields(value):
            snapshots.append(value)
        for nested_value in value.values():
            _walk_paddle_snapshots(nested_value, snapshots=snapshots, visited=visited)
        return

    sequence_value = _as_sequence(value)
    if sequence_value is not None:
        for item in sequence_value:
            _walk_paddle_snapshots(item, snapshots=snapshots, visited=visited)
        return

    for parsed in _object_prediction_values(value):
        _walk_paddle_snapshots(parsed, snapshots=snapshots, visited=visited)


def _mapping_has_line_fields(value: Mapping[object, object]) -> bool:
    """Return whether a mapping has PaddleOCR line text fields.

    Args:
        value: Mapping to inspect.

    Returns:
        True when ``rec_texts`` or ``texts`` is present.
    """
    return any(key in value for key in PADDLE_LINE_TEXT_KEYS)


def _lines_from_mapping(
    value: Mapping[object, object],
    warnings: list[str],
) -> list[_PaddleLine]:
    """Build provider-normalized lines from one PaddleOCR result mapping.

    Args:
        value: PaddleOCR result mapping.
        warnings: Safe warning-code accumulator.

    Returns:
        Lines in provider order.
    """
    raw_texts = _first_sequence_field(value, PADDLE_LINE_TEXT_KEYS)
    if raw_texts is None:
        return []
    raw_scores = _first_sequence_field(value, PADDLE_LINE_SCORE_KEYS)
    raw_polygons, polygon_source = _first_polygon_sequence(value)
    if raw_scores is not None and len(raw_scores) != len(raw_texts):
        _append_warning(warnings, "score_length_mismatch")
    if raw_polygons is not None and len(raw_polygons) != len(raw_texts):
        _append_warning(warnings, "polygon_length_mismatch")

    lines: list[_PaddleLine] = []
    for index, raw_text in enumerate(raw_texts):
        text = _text_value(raw_text)
        if not text:
            continue
        confidence = _score_at(raw_scores, index)
        polygon = _polygon_at(raw_polygons, index)
        source: PaddleLineSource = polygon_source if polygon is not None else "none"
        if raw_polygons is not None and polygon is None:
            _append_warning(warnings, "invalid_or_missing_polygon")
        lines.append(
            _PaddleLine(
                text=text,
                confidence=confidence,
                polygon=polygon,
                source=source,
            )
        )
    return lines


def _first_sequence_field(
    value: Mapping[object, object],
    keys: Sequence[str],
) -> list[object] | None:
    """Return the first sequence field matching the configured key priority.

    Args:
        value: Mapping to inspect.
        keys: Ordered key priority.

    Returns:
        Sequence values as a list, or None.
    """
    for key in keys:
        if key not in value:
            continue
        sequence_value = _as_sequence(value[key])
        if sequence_value is not None:
            return sequence_value
    return None


def _first_polygon_sequence(
    value: Mapping[object, object],
) -> tuple[list[object] | None, PaddleLineSource]:
    """Return the preferred PaddleOCR polygon sequence.

    Args:
        value: Mapping to inspect.

    Returns:
        Polygon values and their stable source label.
    """
    recognition_polygons = _first_sequence_field(value, PADDLE_RECOGNITION_POLYGON_KEYS)
    if recognition_polygons is not None:
        return recognition_polygons, "rec_polys"
    detection_polygons = _first_sequence_field(value, PADDLE_DETECTION_POLYGON_KEYS)
    if detection_polygons is not None:
        return detection_polygons, "dt_polys"
    return None, "none"


def _score_at(values: list[object] | None, index: int) -> float | None:
    """Return the bounded score at an index when available.

    Args:
        values: Optional score values.
        index: Score index.

    Returns:
        Score from 0.0 to 1.0, or None.
    """
    if values is None or index >= len(values):
        return None
    scores = _score_values([values[index]])
    return scores[0] if scores else None


def _polygon_at(values: list[object] | None, index: int) -> OCRBoundingPoly | None:
    """Return the parsed polygon at an index when available.

    Args:
        values: Optional polygon values.
        index: Polygon index.

    Returns:
        Parsed bounding polygon, or None.
    """
    if values is None or index >= len(values):
        return None
    return _parse_paddle_polygon(values[index])


def _parse_paddle_polygon(value: object) -> OCRBoundingPoly | None:
    """Parse a PaddleOCR polygon into the provider-neutral bounding DTO.

    Args:
        value: Candidate polygon, usually ``[[x, y], ...]``.

    Returns:
        OCR bounding polygon, or None when the shape is unusable.
    """
    points = _as_sequence(value)
    if points is None:
        return None
    vertices: list[OCRVertex] = []
    for point in points:
        vertex = _parse_paddle_vertex(point)
        if vertex is None or vertex.x < 0 or vertex.y < 0:
            return None
        vertices.append(vertex)
    if len(vertices) < MIN_POLYGON_VERTICES:
        return None
    return OCRBoundingPoly(vertices=tuple(vertices))


def _parse_paddle_vertex(value: object) -> OCRVertex | None:
    """Parse one PaddleOCR polygon vertex.

    Args:
        value: Candidate vertex mapping or sequence.

    Returns:
        Parsed vertex, or None.
    """
    if isinstance(value, Mapping):
        x_value = value.get("x")
        y_value = value.get("y")
    else:
        coordinates = _as_sequence(value)
        if coordinates is None or len(coordinates) < VERTEX_COORDINATE_PAIR_LENGTH:
            return None
        x_value = coordinates[0]
        y_value = coordinates[1]

    x_coordinate = _number_value(x_value)
    y_coordinate = _number_value(y_value)
    if x_coordinate is None or y_coordinate is None:
        return None
    return OCRVertex(x=x_coordinate, y=y_coordinate)


def _build_paddle_pages(lines: list[_PaddleLine], image: OCRImageInput) -> tuple[OCRPage, ...]:
    """Build an OCR page hierarchy from PaddleOCR line polygons.

    Args:
        lines: Provider-normalized PaddleOCR lines.
        image: Original OCR image input for page dimensions.

    Returns:
        One-page OCR hierarchy, or an empty tuple when no polygon was usable.
    """
    visible_lines = [line for line in lines if line.text.strip()]
    if not any(line.polygon is not None for line in visible_lines):
        return ()

    confidence = _average_scores(
        [line.confidence for line in visible_lines if line.confidence is not None]
    )
    words = tuple(
        OCRWord(
            text=line.text,
            confidence=line.confidence,
            bounding_box=line.polygon,
            block_index=0,
            paragraph_index=0,
            word_index=word_index,
        )
        for word_index, line in enumerate(visible_lines)
    )
    page_text = "\n".join(line.text for line in visible_lines)
    paragraph = OCRParagraph(
        text=page_text,
        confidence=confidence,
        bounding_box=None,
        words=words,
    )
    block = OCRBlock(
        text=page_text,
        confidence=confidence,
        bounding_box=None,
        block_type="TEXT",
        paragraphs=(paragraph,),
    )
    return (
        OCRPage(
            width=image.width,
            height=image.height,
            confidence=confidence,
            blocks=(block,),
        ),
    )


def _collect_text_and_scores(value: object) -> tuple[list[str], list[float]]:
    """Collect OCR text fragments and confidence scores from provider output.

    Args:
        value: PaddleOCR output in dict/list/object form.

    Returns:
        Text fragments and bounded scores.
    """
    fragments: list[str] = []
    scores: list[float] = []
    _walk_prediction(value, fragments=fragments, scores=scores, visited=set())
    return _dedupe_preserve_order(fragments), scores


def _walk_prediction(
    value: object,
    *,
    fragments: list[str],
    scores: list[float],
    visited: set[int],
) -> None:
    """Recursively walk common PaddleOCR result shapes.

    Args:
        value: Provider output fragment.
        fragments: Accumulator for text fragments.
        scores: Accumulator for confidence scores.
        visited: Object ids already visited to avoid cycles.
    """
    value_id = id(value)
    if value_id in visited:
        return
    visited.add(value_id)

    if isinstance(value, Mapping):
        _collect_from_mapping(value, fragments=fragments, scores=scores)
        for nested_value in value.values():
            _walk_prediction(
                nested_value,
                fragments=fragments,
                scores=scores,
                visited=visited,
            )
        return

    sequence_value = _as_sequence(value)
    if sequence_value is not None:
        _collect_legacy_tuple(sequence_value, fragments=fragments, scores=scores)
        for item in sequence_value:
            _walk_prediction(item, fragments=fragments, scores=scores, visited=visited)
        return

    for parsed in _object_prediction_values(value):
        _walk_prediction(parsed, fragments=fragments, scores=scores, visited=visited)


def _collect_from_mapping(
    value: Mapping[object, object],
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
        if key in PADDLE_LINE_TEXT_KEYS:
            text_items = _as_sequence(nested_value)
            if text_items is not None:
                fragments.extend(text for item in text_items if (text := _text_value(item)))
        elif key in PADDLE_TEXT_KEYS and isinstance(nested_value, str):
            fragments.append(nested_value)
        elif key in PADDLE_LINE_SCORE_KEYS:
            score_items = _as_sequence(nested_value)
            if score_items is not None:
                scores.extend(_score_values(score_items))
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
    sequence_value = _as_sequence(value)
    if sequence_value is None or len(sequence_value) != LEGACY_TEXT_SCORE_PAIR_LENGTH:
        return
    text_candidate, score_candidate = sequence_value
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
        number = _number_value(value)
        if number is not None and 0 <= number <= 1:
            scores.append(number)
    return scores


def _object_prediction_values(value: object) -> list[object]:
    """Return parseable object-backed prediction payloads.

    Args:
        value: Provider result object.

    Returns:
        Parsed payloads from ``.json``, ``.json()``, and ``.to_dict()``.
    """
    parsed_values: list[object] = []
    json_value = getattr(value, "json", None)
    if isinstance(json_value, Mapping):
        parsed_values.append(json_value)
    elif callable(json_value):
        try:
            parsed = json_value()
        except Exception:
            parsed = None
        if parsed is not None:
            parsed_values.append(parsed)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            parsed = to_dict()
        except Exception:
            parsed = None
        if parsed is not None:
            parsed_values.append(parsed)
    return parsed_values


def _as_sequence(value: object) -> list[object] | None:
    """Return a non-string iterable value as a list.

    Args:
        value: Candidate sequence, including numpy-array-like values.

    Returns:
        List of items, or None for scalar/string/mapping values.
    """
    if isinstance(value, str | bytes | bytearray | Mapping):
        return None
    if isinstance(value, Sequence):
        return list(value)
    if isinstance(value, Iterable):
        try:
            return list(value)
        except TypeError:
            return None
    return None


def _text_value(value: object) -> str | None:
    """Return a stripped text value when usable.

    Args:
        value: Candidate text value.

    Returns:
        Non-empty stripped text, or None.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _number_value(value: object) -> float | None:
    """Return a numeric value as float while rejecting booleans.

    Args:
        value: Candidate numeric value.

    Returns:
        Float value, or None.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    return float(value)


def _append_warning(warnings: list[str], warning: str) -> None:
    """Append a warning code once.

    Args:
        warnings: Mutable warning list.
        warning: Stable warning code.
    """
    if warning not in warnings:
        warnings.append(warning)


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

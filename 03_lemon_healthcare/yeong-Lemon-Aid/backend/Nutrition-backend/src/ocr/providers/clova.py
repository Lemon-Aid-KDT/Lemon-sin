"""Optional NAVER Cloud CLOVA OCR fallback provider."""

from __future__ import annotations

import base64
import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol
from uuid import uuid4

import httpx

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

CLOVA_OCR_PROVIDER = "clova_ocr"
HTTP_ERROR_STATUS_MIN = 400
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class ClovaHTTPResponse(Protocol):
    """Protocol for the HTTP response fields used by the CLOVA adapter."""

    status_code: int

    def json(self) -> Any:
        """Return parsed JSON response.

        Returns:
            Parsed JSON payload.
        """
        ...


class ClovaHTTPClient(Protocol):
    """Protocol for the async HTTP client used by the CLOVA adapter."""

    async def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float | None = None,
    ) -> ClovaHTTPResponse:
        """Post a CLOVA OCR request.

        Args:
            url: Request URL.
            json: Request payload.
            headers: Request headers.
            timeout: Request timeout.

        Returns:
            HTTP response.
        """
        ...


class ClovaOCRAdapter(OCRAdapter):
    """External CLOVA OCR adapter used only as an explicit fallback.

    The adapter sends image bytes to NAVER Cloud CLOVA OCR, so callers must keep
    ``ALLOW_EXTERNAL_OCR`` and external OCR consent gates enforced before use.
    """

    def __init__(self, settings: Settings, client: ClovaHTTPClient | None = None) -> None:
        """Initialize the adapter.

        Args:
            settings: Runtime settings.
            client: Optional injected HTTP client for tests.
        """
        self._settings = settings
        self._client = client

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Extract text with NAVER Cloud CLOVA OCR.

        Args:
            image: Validated OCR image input.

        Returns:
            OCR result with text, provider confidence, and normalized layout metadata
            when CLOVA returns coordinates.

        Raises:
            OCRError: If external OCR is disabled, credentials are missing, or
                CLOVA returns an invalid response.
        """
        _validate_clova_settings(self._settings)
        payload = _build_clova_payload(image)
        headers = _build_clova_headers(self._settings)
        response_payload = await self._post_with_retries(payload=payload, headers=headers)
        return _parse_clova_response(response_payload, image)

    async def _post_with_retries(
        self,
        *,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Post a CLOVA OCR request and retry transient failures.

        Args:
            payload: Request payload.
            headers: Request headers.

        Returns:
            Parsed JSON object.

        Raises:
            OCRError: If transport or response parsing fails.
        """
        attempts = self._settings.clova_ocr_max_retries + 1
        last_error: OCRError | None = None
        for attempt in range(attempts):
            try:
                response = await self._post_once(payload=payload, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = OCRError("CLOVA OCR transport failure.")
                if attempt + 1 >= attempts:
                    raise last_error from exc
                continue

            if response.status_code < HTTP_ERROR_STATUS_MIN:
                return _parse_response_json(response)

            error = _response_error(response)
            if response.status_code not in TRANSIENT_STATUS_CODES or attempt + 1 >= attempts:
                raise error
            last_error = error

        if last_error is not None:
            raise last_error
        raise OCRError("CLOVA OCR request failed.")

    async def _post_once(
        self,
        *,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> ClovaHTTPResponse:
        """Post one CLOVA OCR HTTP request without retry logic.

        Args:
            payload: Request payload.
            headers: Request headers.

        Returns:
            HTTP response object.

        Raises:
            httpx.TimeoutException: If the request times out.
            httpx.TransportError: If the transport fails.
        """
        timeout = float(self._settings.clova_ocr_timeout_seconds)
        if self._client is not None:
            return await self._client.post(
                self._settings.clova_ocr_api_url or "",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(
                self._settings.clova_ocr_api_url or "",
                json=payload,
                headers=headers,
            )


def _parse_response_json(response: ClovaHTTPResponse) -> dict[str, Any]:
    """Parse and validate a CLOVA JSON response object.

    Args:
        response: HTTP response returned by CLOVA.

    Returns:
        Parsed JSON object.

    Raises:
        OCRError: If CLOVA returned invalid JSON or a non-object payload.
    """
    try:
        parsed = response.json()
    except ValueError as exc:
        raise OCRError("CLOVA OCR returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise OCRError("CLOVA OCR returned an invalid response shape.")
    return parsed


def _response_error(response: ClovaHTTPResponse) -> OCRError:
    """Build a sanitized error for a non-success CLOVA HTTP response.

    Args:
        response: HTTP response returned by CLOVA.

    Returns:
        Sanitized OCR error.
    """
    status_message = f"CLOVA OCR request failed: status {response.status_code}"
    try:
        parsed = response.json()
    except ValueError:
        return OCRError(f"{status_message}.")
    if not isinstance(parsed, dict):
        return OCRError(f"{status_message}.")
    error_code = _first_string_value(parsed, ("code", "errorCode", "statusCode"))
    if error_code is None:
        error_code = _first_image_string_value(parsed, ("code", "errorCode", "statusCode"))
    if error_code:
        return OCRError(f"{status_message}; code={error_code}.")
    return OCRError(f"{status_message}.")


def _first_string_value(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    """Return the first non-empty string value for candidate keys.

    Args:
        payload: JSON object to inspect.
        keys: Candidate keys in priority order.

    Returns:
        String value or None.
    """
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_image_string_value(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    """Return a safe string value from the first image response object.

    Args:
        payload: CLOVA response payload.
        keys: Candidate keys in priority order.

    Returns:
        String value or None.
    """
    images = payload.get("images")
    if not isinstance(images, list) or not images or not isinstance(images[0], dict):
        return None
    return _first_string_value(images[0], keys)


def _validate_clova_settings(settings: Settings) -> None:
    """Validate CLOVA OCR settings before sending image bytes.

    Args:
        settings: Runtime settings.

    Raises:
        OCRError: If required external OCR settings are missing.
    """
    if not settings.enable_clova_ocr:
        raise OCRError("ENABLE_CLOVA_OCR=true is required for CLOVA fallback.")
    if not settings.allow_external_ocr:
        raise OCRError("ALLOW_EXTERNAL_OCR=true is required for CLOVA OCR.")
    if not settings.clova_ocr_api_url:
        raise OCRError("CLOVA_OCR_API_URL is required for CLOVA OCR.")
    if settings.clova_ocr_secret is None:
        raise OCRError("CLOVA_OCR_SECRET is required for CLOVA OCR.")


def _build_clova_headers(settings: Settings) -> dict[str, str]:
    """Build CLOVA request headers without logging secrets.

    Args:
        settings: Runtime settings.

    Returns:
        Request headers.
    """
    secret = settings.clova_ocr_secret
    if secret is None:
        raise OCRError("CLOVA_OCR_SECRET is required for CLOVA OCR.")
    return {
        "Content-Type": "application/json",
        "X-OCR-SECRET": secret.get_secret_value(),
    }


def _build_clova_payload(image: OCRImageInput) -> dict[str, object]:
    """Build a CLOVA OCR JSON request payload.

    Args:
        image: Validated OCR image input.

    Returns:
        JSON payload.
    """
    return {
        "version": "V2",
        "requestId": str(uuid4()),
        "timestamp": int(time.time() * 1000),
        "images": [
            {
                "format": _clova_format_for_mime_type(image.mime_type),
                "name": "supplement_label",
                "data": base64.b64encode(image.image_bytes).decode("ascii"),
            }
        ],
    }


def _clova_format_for_mime_type(mime_type: str) -> str:
    """Return CLOVA image format token for a MIME type.

    Args:
        mime_type: Validated image MIME type.

    Returns:
        CLOVA image format.
    """
    if mime_type == "image/jpeg":
        return "jpg"
    if mime_type == "image/webp":
        return "png"
    return "png"


def _parse_clova_response(payload: dict[str, Any], image: OCRImageInput) -> OCRResult:
    """Normalize CLOVA OCR response JSON.

    Args:
        payload: Parsed CLOVA response.
        image: Original OCR input metadata.

    Returns:
        OCR result.

    Raises:
        OCRError: If the response shape is invalid or CLOVA reports failed inference.
    """
    images = payload.get("images")
    if not isinstance(images, list) or not images:
        raise OCRError("CLOVA OCR response is missing images.")
    first_image = images[0]
    if not isinstance(first_image, dict):
        raise OCRError("CLOVA OCR response image shape is invalid.")

    infer_result = first_image.get("inferResult")
    if isinstance(infer_result, str) and infer_result not in {"SUCCESS", ""}:
        raise OCRError(f"CLOVA OCR inference failed: {infer_result}.")

    fields = _json_objects(first_image.get("fields"))
    tables = _json_objects(first_image.get("tables"))
    text_block = _build_fields_block(fields)
    table_blocks = _build_table_blocks(tables, start_block_index=1 if text_block else 0)
    blocks = tuple(block for block in (text_block, *table_blocks) if block is not None)

    page = _build_page(first_image, image, blocks) if blocks else None
    pages = (page,) if page is not None else ()
    field_lines = _field_text_lines(fields)
    table_lines = [block.text for block in table_blocks if block.text]
    text = "\n".join((*field_lines, *table_lines)).strip()
    return OCRResult(
        text=text,
        provider=CLOVA_OCR_PROVIDER,
        confidence=_average_layout_confidence(pages),
        pages=pages,
    )


def _build_fields_block(fields: Sequence[Mapping[str, Any]]) -> OCRBlock | None:
    """Build a synthetic text block from CLOVA field objects.

    Args:
        fields: CLOVA ``fields`` entries.

    Returns:
        OCR text block, or None when no readable field text is present.
    """
    words: list[OCRWord] = []
    for field in fields:
        text = _field_string(field, "inferText")
        if text is None:
            continue
        word = _build_word(
            source=field,
            text=text,
            block_index=0,
            paragraph_index=0,
            word_index=len(words),
        )
        words.append(word)
    if not words:
        return None
    paragraph = _build_paragraph(words=tuple(words), text="\n".join(_field_text_lines(fields)))
    return _build_block(
        block_index=0,
        block_type="TEXT",
        paragraphs=(paragraph,),
    )


def _build_table_blocks(
    tables: Sequence[Mapping[str, Any]],
    *,
    start_block_index: int,
) -> tuple[OCRBlock, ...]:
    """Build OCR table blocks from CLOVA table objects.

    Args:
        tables: CLOVA ``tables`` entries.
        start_block_index: Block index assigned to the first table block.

    Returns:
        Table OCR blocks.
    """
    blocks: list[OCRBlock] = []
    for table in tables:
        block_index = start_block_index + len(blocks)
        table_words = _table_words(table, block_index=block_index)
        if not table_words:
            continue
        text = " ".join(word.text for word in table_words)
        paragraph = _build_paragraph(words=tuple(table_words), text=text)
        blocks.append(
            _build_block(
                block_index=block_index,
                block_type="TABLE",
                paragraphs=(paragraph,),
                source=table,
            )
        )
    return tuple(blocks)


def _build_word(
    *,
    source: Mapping[str, Any],
    text: str,
    block_index: int,
    paragraph_index: int,
    word_index: int,
) -> OCRWord:
    """Build a normalized OCR word from a CLOVA word-like object.

    Args:
        source: CLOVA field, cell, or word object.
        text: Recognized text.
        block_index: Parent block index.
        paragraph_index: Parent paragraph index.
        word_index: Word index within the paragraph.

    Returns:
        OCR word.
    """
    return OCRWord(
        text=text,
        confidence=_bounded_confidence(source.get("inferConfidence")),
        bounding_box=_parse_bounding_poly(source),
        block_index=block_index,
        paragraph_index=paragraph_index,
        word_index=word_index,
    )


def _build_paragraph(*, words: tuple[OCRWord, ...], text: str) -> OCRParagraph:
    """Build a normalized OCR paragraph.

    Args:
        words: Paragraph words.
        text: Paragraph text.

    Returns:
        OCR paragraph.
    """
    return OCRParagraph(
        text=text,
        confidence=_average_optional(word.confidence for word in words),
        bounding_box=None,
        words=words,
    )


def _build_block(
    *,
    block_index: int,
    block_type: str,
    paragraphs: tuple[OCRParagraph, ...],
    source: Mapping[str, Any] | None = None,
) -> OCRBlock:
    """Build a normalized OCR block.

    Args:
        block_index: Block index on the page.
        block_type: Synthetic block type.
        paragraphs: Paragraphs in provider order.
        source: Optional provider object used for block-level geometry.

    Returns:
        OCR block.
    """
    _ = block_index
    text = "\n".join(paragraph.text for paragraph in paragraphs if paragraph.text)
    return OCRBlock(
        text=text,
        confidence=_average_optional(paragraph.confidence for paragraph in paragraphs),
        bounding_box=_parse_bounding_poly(source) if source is not None else None,
        block_type=block_type,
        paragraphs=paragraphs,
    )


def _build_page(
    image_payload: Mapping[str, Any],
    source_image: OCRImageInput,
    blocks: tuple[OCRBlock, ...],
) -> OCRPage:
    """Build a normalized OCR page from CLOVA response metadata.

    Args:
        image_payload: First CLOVA image response object.
        source_image: Original OCR input.
        blocks: OCR blocks for the page.

    Returns:
        OCR page.
    """
    converted_info = image_payload.get("convertedImageInfo")
    converted = converted_info if isinstance(converted_info, dict) else {}
    width = _page_dimension(converted.get("width"), fallback=source_image.width)
    height = _page_dimension(converted.get("height"), fallback=source_image.height)
    return OCRPage(
        width=width,
        height=height,
        confidence=_average_optional(block.confidence for block in blocks),
        blocks=blocks,
    )


def _field_text_lines(fields: Sequence[Mapping[str, Any]]) -> list[str]:
    """Assemble CLOVA field text while respecting line break markers.

    Args:
        fields: CLOVA field objects.

    Returns:
        Text lines in provider order.
    """
    lines: list[str] = []
    current_line: list[str] = []
    for field in fields:
        text = _field_string(field, "inferText")
        if text is None:
            continue
        current_line.append(text)
        line_break = field.get("lineBreak")
        if line_break is False:
            continue
        lines.append(" ".join(current_line).strip())
        current_line = []
    if current_line:
        lines.append(" ".join(current_line).strip())
    return [line for line in lines if line]


def _table_words(table: Mapping[str, Any], *, block_index: int) -> tuple[OCRWord, ...]:
    """Extract normalized words from CLOVA table cells.

    Args:
        table: CLOVA table object.
        block_index: Synthetic table block index.

    Returns:
        Table words in response order.
    """
    words: list[OCRWord] = []
    for cell in _json_objects(table.get("cells")):
        for source, text in _cell_word_sources(cell):
            words.append(
                _build_word(
                    source=source,
                    text=text,
                    block_index=block_index,
                    paragraph_index=0,
                    word_index=len(words),
                )
            )
    return tuple(words)


def _cell_word_sources(
    cell: Mapping[str, Any],
) -> Iterable[tuple[Mapping[str, Any], str]]:
    """Yield word-like table sources from one CLOVA table cell.

    Args:
        cell: CLOVA table cell object.

    Yields:
        Pairs of source object and recognized text.
    """
    found_word = False
    for line in _json_objects(cell.get("cellTextLines")):
        for word in _json_objects(line.get("cellWords")):
            text = _field_string(word, "inferText") or _field_string(word, "text")
            if text is None:
                continue
            found_word = True
            yield word, text
    if found_word:
        return
    text = (
        _field_string(cell, "inferText")
        or _field_string(cell, "text")
        or _field_string(cell, "cellText")
    )
    if text is not None:
        yield cell, text


def _parse_bounding_poly(source: Mapping[str, Any] | None) -> OCRBoundingPoly | None:
    """Parse a CLOVA bounding polygon.

    Args:
        source: CLOVA object that may contain ``boundingPoly``.

    Returns:
        OCR bounding polygon or None.
    """
    if source is None:
        return None
    raw_poly = source.get("boundingPoly")
    if not isinstance(raw_poly, dict):
        return None
    raw_vertices = raw_poly.get("vertices")
    if raw_vertices is None:
        raw_vertices = raw_poly.get("normalizedVertices")
    vertices = tuple(
        vertex
        for vertex in (_parse_vertex(value) for value in _json_objects(raw_vertices))
        if vertex
    )
    if not vertices:
        return None
    return OCRBoundingPoly(vertices=vertices)


def _parse_vertex(raw_vertex: Mapping[str, Any]) -> OCRVertex | None:
    """Parse one CLOVA bounding polygon vertex.

    Args:
        raw_vertex: CLOVA vertex object.

    Returns:
        OCR vertex or None.
    """
    x = _numeric(raw_vertex.get("x"))
    y = _numeric(raw_vertex.get("y"))
    if x is None or y is None:
        return None
    return OCRVertex(x=x, y=y)


def _json_objects(value: object) -> tuple[Mapping[str, Any], ...]:
    """Return only JSON object entries from a list-like value.

    Args:
        value: Candidate list value.

    Returns:
        Mapping entries in original order.
    """
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _field_string(source: Mapping[str, Any], key: str) -> str | None:
    """Return a stripped non-empty string field.

    Args:
        source: JSON object.
        key: Field name.

    Returns:
        String value or None.
    """
    value = source.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _page_dimension(value: object, *, fallback: int) -> int | None:
    """Return an integer page dimension from CLOVA metadata.

    Args:
        value: Candidate page dimension.
        fallback: Validated source image dimension.

    Returns:
        Positive integer dimension or None.
    """
    numeric_value = _numeric(value)
    if numeric_value is None:
        return fallback if fallback > 0 else None
    rounded = round(numeric_value)
    return rounded if rounded > 0 else None


def _numeric(value: object) -> float | None:
    """Return a finite numeric value.

    Args:
        value: Candidate number.

    Returns:
        Float value or None.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _bounded_confidence(value: object) -> float | None:
    """Return a confidence only when it is in the official 0-1 range.

    Args:
        value: Candidate confidence.

    Returns:
        Confidence or None.
    """
    numeric_value = _numeric(value)
    if numeric_value is None or not 0 <= numeric_value <= 1:
        return None
    return numeric_value


def _average_optional(values: Iterable[float | None]) -> float | None:
    """Average present values.

    Args:
        values: Optional confidence values.

    Returns:
        Average confidence or None.
    """
    present = [value for value in values if value is not None]
    return _average(present)


def _average_layout_confidence(pages: tuple[OCRPage, ...]) -> float | None:
    """Average provider confidence from normalized layout pages.

    Args:
        pages: OCR pages.

    Returns:
        Average confidence or None.
    """
    return _average_optional(page.confidence for page in pages)


def _average(values: list[float]) -> float | None:
    """Average values when present.

    Args:
        values: Confidence values.

    Returns:
        Average confidence or None.
    """
    if not values:
        return None
    return sum(values) / len(values)

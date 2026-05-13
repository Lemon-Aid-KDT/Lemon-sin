"""Image preprocessing helpers used before OCR provider calls."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError


class OCRPreprocessingError(ValueError):
    """Raised when an image cannot be normalized for OCR."""


def normalize_image_for_ocr(image_bytes: bytes, *, max_side_px: int = 2048) -> bytes:
    """Normalize an uploaded label image to bounded RGB PNG bytes.

    Args:
        image_bytes: Validated source image bytes.
        max_side_px: Maximum width or height after normalization.

    Returns:
        PNG-encoded RGB image bytes.

    Raises:
        OCRPreprocessingError: If the image cannot be decoded or the size bound is invalid.
    """
    if max_side_px <= 0:
        raise OCRPreprocessingError("max_side_px must be positive.")

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            normalized = source.convert("RGB")
            normalized.thumbnail((max_side_px, max_side_px), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            normalized.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except (OSError, UnidentifiedImageError) as exc:
        raise OCRPreprocessingError("Image cannot be decoded for OCR preprocessing.") from exc

"""Supplement image quality gate tests."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw
from src.services.supplement_image_quality import analyze_supplement_label_image_quality
from src.services.supplement_intake import ValidatedSupplementImage


def _png_bytes(image: Image.Image) -> bytes:
    """Return PNG bytes for a generated image."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _metadata(width: int, height: int, *, size_bytes: int = 1024) -> ValidatedSupplementImage:
    """Return validated image metadata for quality tests."""
    return ValidatedSupplementImage(
        sha256="a" * 64,
        mime_type="image/png",
        size_bytes=size_bytes,
        width=width,
        height=height,
    )


def test_quality_gate_flags_low_resolution_blur_glare_and_contrast() -> None:
    """Verify unreadable bright thumbnails produce retake guidance."""
    image = Image.new("RGB", (320, 240), color=(255, 255, 255))

    report = analyze_supplement_label_image_quality(
        _png_bytes(image),
        _metadata(320, 240),
    )

    reason_codes = {issue.reason_code for issue in report.issues}
    assert report.status == "retake_recommended"
    assert "low_resolution" in reason_codes
    assert "blurred_text" in reason_codes
    assert "glare_or_reflection" in reason_codes
    assert "raw_ocr_text" not in report.model_dump_json()


def test_quality_gate_accepts_sharp_high_resolution_label_like_image() -> None:
    """Verify a high-resolution high-contrast label-like image passes."""
    image = Image.new("RGB", (1400, 1000), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)
    for y in range(120, 880, 44):
        draw.rectangle((180, y, 1220, y + 12), fill=(20, 20, 20))

    report = analyze_supplement_label_image_quality(
        _png_bytes(image),
        _metadata(1400, 1000),
    )

    assert report.status == "acceptable"
    assert report.issues == []
    assert report.metrics["short_edge_px"] == 1000


def test_quality_gate_flags_cropped_border_content_and_skewed_aspect() -> None:
    """Verify crop and angle proxy warnings are exposed as stable reason codes."""
    image = Image.new("RGB", (2200, 600), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 2199, 70), fill=(10, 10, 10))
    draw.rectangle((0, 530, 2199, 599), fill=(10, 10, 10))

    report = analyze_supplement_label_image_quality(
        _png_bytes(image),
        _metadata(2200, 600),
    )

    reason_codes = {issue.reason_code for issue in report.issues}
    assert "cropped_label" in reason_codes
    assert "skewed_label" in reason_codes

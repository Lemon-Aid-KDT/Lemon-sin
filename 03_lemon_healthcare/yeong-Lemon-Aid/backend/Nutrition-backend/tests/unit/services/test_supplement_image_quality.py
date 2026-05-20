"""Supplement image quality analyzer tests."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
from src.services.supplement_image_quality import analyze_supplement_image_quality
from src.vision.base import BoundingBox


def _png_bytes(image: Image.Image) -> bytes:
    """Encode a PIL image as PNG.

    Args:
        image: PIL image.

    Returns:
        PNG bytes.
    """
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_quality_analyzer_reports_blur_and_low_contrast_for_flat_image() -> None:
    """Verify flat images produce deterministic retake reasons."""
    image = Image.new("RGB", (40, 40), color=(128, 128, 128))

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=40,
        image_height=40,
    )

    reasons = {issue.reason_code for issue in report.issues}
    assert report.status == "retake_recommended"
    assert "blurred_text" in reasons
    assert "low_contrast" in reasons


def test_quality_analyzer_reports_low_light() -> None:
    """Verify dark images produce a low-light warning."""
    image = Image.new("RGB", (40, 40), color=(10, 10, 10))

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=40,
        image_height=40,
    )

    assert "low_light" in {issue.reason_code for issue in report.issues}


def test_quality_analyzer_reports_glare_for_large_highlight_region() -> None:
    """Verify high-luminance regions produce a glare warning."""
    image = Image.new("RGB", (100, 100), color=(90, 90, 90))
    for x in range(30):
        for y in range(60):
            image.putpixel((x, y), (255, 255, 255))

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=100,
        image_height=100,
    )

    assert "glare_or_reflection" in {issue.reason_code for issue in report.issues}


def test_quality_analyzer_reports_small_roi_and_roi_metadata() -> None:
    """Verify small detected OCR regions are surfaced without raw image data."""
    image = Image.new("RGB", (400, 400), color=(160, 160, 160))
    roi = BoundingBox(
        x=20,
        y=20,
        width=30,
        height=30,
        confidence=0.91,
        label="supplement_label",
        model="test-roi.pt",
    )

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=400,
        image_height=400,
        label_region=roi,
    )

    assert "too_small_text" in {issue.reason_code for issue in report.issues}
    assert report.detected_rois[0].label == "supplement_label"
    assert report.detected_rois[0].area_ratio is not None


def test_quality_analyzer_reports_multi_product_placeholder() -> None:
    """Verify multiple product-like ROIs are treated as a review issue."""
    image = Image.new("RGB", (400, 400), color=(160, 160, 160))
    regions = (
        BoundingBox(x=10, y=10, width=120, height=200, confidence=0.8, label="supplement_bottle"),
        BoundingBox(x=220, y=10, width=120, height=200, confidence=0.82, label="supplement_bottle"),
    )

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=400,
        image_height=400,
        detected_regions=regions,
    )

    assert "multi_product" in {issue.reason_code for issue in report.issues}


def test_quality_analyzer_reports_roi_not_found_when_detector_enabled() -> None:
    """Verify detector miss is represented as review metadata."""
    image = Image.new("RGB", (100, 100), color=(180, 180, 180))

    report = analyze_supplement_image_quality(
        _png_bytes(image),
        image_width=100,
        image_height=100,
        roi_detection_enabled=True,
    )

    assert "roi_not_found" in {issue.reason_code for issue in report.issues}

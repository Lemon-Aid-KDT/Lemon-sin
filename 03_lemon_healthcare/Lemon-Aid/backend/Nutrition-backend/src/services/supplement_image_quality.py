"""Deterministic supplement-label image quality checks."""

from __future__ import annotations

from PIL import Image, ImageFilter, ImageStat

from src.models.schemas.image_quality import ImageQualityReport, QualityIssue
from src.services.supplement_intake import ValidatedSupplementImage
from src.utils.image_safety import safe_load_with_bomb_guard

MIN_TOTAL_PIXELS = 1_000_000
MIN_SHORT_EDGE_PX = 900
MIN_EDGE_VARIANCE = 10.0
MIN_CONTRAST_STDDEV = 18.0
GLARE_BRIGHT_RATIO = 0.72
BORDER_INK_RATIO = 0.18
SKEWED_ASPECT_RATIO = 2.8
ANALYSIS_MAX_EDGE_PX = 768
LOW_INK_THRESHOLD = 85
BRIGHT_THRESHOLD = 245


def analyze_supplement_label_image_quality(
    image_bytes: bytes,
    image_metadata: ValidatedSupplementImage,
) -> ImageQualityReport:
    """Return a redacted deterministic quality report before OCR.

    Args:
        image_bytes: Sanitized image bytes after metadata stripping.
        image_metadata: Validated image metadata from the intake gate.

    Returns:
        Image quality report containing only numeric metrics and bounded reason codes.
    """
    with safe_load_with_bomb_guard(image_bytes) as decoded:
        image = decoded.convert("RGB")
        image.thumbnail((ANALYSIS_MAX_EDGE_PX, ANALYSIS_MAX_EDGE_PX))
        grayscale = image.convert("L")

        edge_variance = _edge_variance(grayscale)
        contrast_stddev = _contrast_stddev(grayscale)
        bright_ratio = _bright_pixel_ratio(grayscale)
        border_ink_ratio = _border_ink_ratio(grayscale)

    width = image_metadata.width
    height = image_metadata.height
    short_edge = min(width, height)
    total_pixels = width * height
    aspect_ratio = max(width / height, height / width) if width and height else 0.0

    metrics = {
        "image_width": width,
        "image_height": height,
        "total_pixels": total_pixels,
        "short_edge_px": short_edge,
        "edge_variance": _round_metric(edge_variance),
        "contrast_stddev": _round_metric(contrast_stddev),
        "bright_pixel_ratio": _round_metric(bright_ratio),
        "border_ink_ratio": _round_metric(border_ink_ratio),
        "aspect_ratio": _round_metric(aspect_ratio),
    }

    issues: list[QualityIssue] = []
    if total_pixels < MIN_TOTAL_PIXELS or short_edge < MIN_SHORT_EDGE_PX:
        issues.append(
            QualityIssue(
                reason_code="low_resolution",
                severity="retake",
                message="라벨 글자가 작게 보입니다. 더 가까이에서 선명하게 다시 촬영해주세요.",
                evidence={
                    "total_pixels": total_pixels,
                    "short_edge_px": short_edge,
                },
            )
        )
    if edge_variance < MIN_EDGE_VARIANCE:
        issues.append(
            QualityIssue(
                reason_code="blurred_text",
                severity="retake",
                message="라벨 글자가 흐릿합니다. 초점을 맞춘 뒤 다시 촬영해주세요.",
                evidence={"edge_variance": _round_metric(edge_variance)},
            )
        )
    if contrast_stddev < MIN_CONTRAST_STDDEV:
        issues.append(
            QualityIssue(
                reason_code="low_contrast",
                severity="retake",
                message="라벨과 글자의 대비가 낮습니다. 밝은 곳에서 그림자 없이 촬영해주세요.",
                evidence={"contrast_stddev": _round_metric(contrast_stddev)},
            )
        )
    if bright_ratio >= GLARE_BRIGHT_RATIO and contrast_stddev < MIN_CONTRAST_STDDEV * 1.5:
        issues.append(
            QualityIssue(
                reason_code="glare_or_reflection",
                severity="review",
                message="반사광이나 과노출이 있을 수 있습니다. 빛이 비치지 않게 각도를 조정해주세요.",
                evidence={"bright_pixel_ratio": _round_metric(bright_ratio)},
            )
        )
    if border_ink_ratio >= BORDER_INK_RATIO:
        issues.append(
            QualityIssue(
                reason_code="cropped_label",
                severity="retake",
                message="라벨 글자가 화면 가장자리에 붙어 일부가 잘렸을 수 있습니다.",
                evidence={"border_ink_ratio": _round_metric(border_ink_ratio)},
            )
        )
    if aspect_ratio >= SKEWED_ASPECT_RATIO:
        issues.append(
            QualityIssue(
                reason_code="skewed_label",
                severity="review",
                message="라벨이 비스듬하거나 한쪽으로 길게 잡혔을 수 있습니다. 정면에서 촬영해주세요.",
                evidence={"aspect_ratio": _round_metric(aspect_ratio)},
            )
        )

    status = _status_from_issues(issues)
    retake_reasons = [
        issue.reason_code for issue in issues if issue.severity in {"retake", "blocked"}
    ]
    return ImageQualityReport(
        status=status,
        issues=issues,
        metrics=metrics,
        detected_rois=[],
        retake_reasons=retake_reasons,
    )


def _edge_variance(grayscale: Image.Image) -> float:
    """Return edge-response variance used as a blur proxy."""
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    width, height = edges.size
    margin = max(1, min(width, height) // 50)
    if width > margin * 2 and height > margin * 2:
        edges = edges.crop((margin, margin, width - margin, height - margin))
    return float(ImageStat.Stat(edges).var[0])


def _contrast_stddev(grayscale: Image.Image) -> float:
    """Return luminance standard deviation as a contrast proxy."""
    return float(ImageStat.Stat(grayscale).stddev[0])


def _bright_pixel_ratio(grayscale: Image.Image) -> float:
    """Return the fraction of near-white pixels."""
    histogram = grayscale.histogram()
    bright_pixels = sum(histogram[BRIGHT_THRESHOLD:])
    total_pixels = sum(histogram)
    return bright_pixels / total_pixels if total_pixels else 0.0


def _border_ink_ratio(grayscale: Image.Image) -> float:
    """Return the fraction of dark pixels near image borders."""
    width, height = grayscale.size
    border = max(1, min(width, height) // 20)
    boxes = (
        (0, 0, width, border),
        (0, max(0, height - border), width, height),
        (0, 0, border, height),
        (max(0, width - border), 0, width, height),
    )
    dark_pixels = 0
    total_pixels = 0
    for box in boxes:
        crop = grayscale.crop(box)
        histogram = crop.histogram()
        dark_pixels += sum(histogram[:LOW_INK_THRESHOLD])
        total_pixels += sum(histogram)
    return dark_pixels / total_pixels if total_pixels else 0.0


def _status_from_issues(issues: list[QualityIssue]) -> str:
    """Map issue severities to the report status contract."""
    severities = {issue.severity for issue in issues}
    if "blocked" in severities:
        return "blocked"
    if "retake" in severities:
        return "retake_recommended"
    if "review" in severities:
        return "needs_review"
    return "acceptable"


def _round_metric(value: float) -> float:
    """Round metrics so reports do not imply pixel-level precision."""
    return round(value, 4)

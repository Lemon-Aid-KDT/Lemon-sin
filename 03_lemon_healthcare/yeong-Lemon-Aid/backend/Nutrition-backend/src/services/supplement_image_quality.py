"""Deterministic quality checks for supplement label images."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from io import BytesIO
from math import sqrt

from PIL import Image, UnidentifiedImageError

from src.models.schemas.image_quality import (
    DetectedROI,
    ImageQualityReasonCode,
    ImageQualityReport,
    ImageQualitySeverity,
    ImageQualityStatus,
    QualityIssue,
)
from src.vision.base import BoundingBox

LOW_LIGHT_MEAN_LUMINANCE = 60.0
LOW_CONTRAST_STDDEV = 18.0
BLUR_EDGE_STRENGTH = 5.0
GLARE_PIXEL_RATIO = 0.12
GLARE_LUMINANCE = 245
MIN_ROI_AREA_RATIO = 0.08
MIN_ROI_DIMENSION_PX = 96
EDGE_TOUCH_MARGIN_PX = 2


class ImageQualityAnalysisError(ValueError):
    """Raised when image quality analysis cannot decode a validated image."""


def analyze_supplement_image_quality(
    image_bytes: bytes,
    *,
    image_width: int,
    image_height: int,
    label_region: BoundingBox | None = None,
    detected_regions: Sequence[BoundingBox] = (),
    roi_detection_enabled: bool = False,
) -> ImageQualityReport:
    """Analyze image quality without storing raw image bytes or OCR text.

    Args:
        image_bytes: Validated image bytes.
        image_width: Validated image width.
        image_height: Validated image height.
        label_region: Optional selected OCR ROI.
        detected_regions: Optional candidate ROIs when available.
        roi_detection_enabled: Whether a detector was expected to find ROI metadata.

    Returns:
        Deterministic quality report with bounded numeric evidence.

    Raises:
        ImageQualityAnalysisError: If image bytes cannot be decoded.
    """
    image = _decode_image(image_bytes)
    luminance_values = _luminance_values(image)
    metrics = _base_metrics(
        luminance_values,
        image_width=image_width,
        image_height=image_height,
        label_region=label_region,
    )
    regions = (
        list(detected_regions) if detected_regions else ([label_region] if label_region else [])
    )
    detected_rois = [
        _detected_roi_from_box(region, image_width=image_width, image_height=image_height)
        for region in regions
        if region is not None
    ]
    issues = _quality_issues(
        metrics,
        image_width=image_width,
        image_height=image_height,
        label_region=label_region,
        detected_regions=regions,
        roi_detection_enabled=roi_detection_enabled,
    )
    return ImageQualityReport(
        status=_status_for_issues(issues),
        issues=issues,
        metrics=metrics,
        detected_rois=detected_rois,
        retake_reasons=[
            issue.reason_code for issue in issues if issue.severity in {"retake", "blocked"}
        ],
    )


def _decode_image(image_bytes: bytes) -> Image.Image:
    """Decode image bytes as RGB.

    Args:
        image_bytes: Validated image bytes.

    Returns:
        RGB PIL image.

    Raises:
        ImageQualityAnalysisError: If decoding fails.
    """
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return image.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise ImageQualityAnalysisError("Image cannot be decoded for quality analysis.") from exc


def _luminance_values(image: Image.Image) -> list[int]:
    """Return grayscale luminance values.

    Args:
        image: RGB image.

    Returns:
        Luminance values in row-major order.
    """
    return list(image.convert("L").getdata())


def _base_metrics(
    luminance_values: list[int],
    *,
    image_width: int,
    image_height: int,
    label_region: BoundingBox | None,
) -> dict[str, float | int | str | bool | None]:
    """Compute deterministic numeric metrics for quality decisions.

    Args:
        luminance_values: Grayscale image values.
        image_width: Image width.
        image_height: Image height.
        label_region: Optional selected ROI.

    Returns:
        Bounded numeric quality metrics.
    """
    mean = _mean(luminance_values)
    stddev = _stddev(luminance_values, mean)
    glare_ratio = _ratio(value >= GLARE_LUMINANCE for value in luminance_values)
    blur_proxy = _edge_strength(luminance_values, width=image_width, height=image_height)
    roi_area_ratio = _roi_area_ratio(
        label_region, image_width=image_width, image_height=image_height
    )
    return {
        "image_width": image_width,
        "image_height": image_height,
        "mean_luminance": round(mean, 4),
        "luminance_stddev": round(stddev, 4),
        "glare_pixel_ratio": round(glare_ratio, 6),
        "edge_strength_proxy": round(blur_proxy, 4),
        "roi_area_ratio": round(roi_area_ratio, 6) if roi_area_ratio is not None else None,
        "roi_min_dimension_px": (
            min(label_region.width, label_region.height) if label_region is not None else None
        ),
    }


def _quality_issues(
    metrics: dict[str, float | int | str | bool | None],
    *,
    image_width: int,
    image_height: int,
    label_region: BoundingBox | None,
    detected_regions: Sequence[BoundingBox | None],
    roi_detection_enabled: bool,
) -> list[QualityIssue]:
    """Build quality issues from deterministic metrics.

    Args:
        metrics: Numeric quality metrics.
        image_width: Image width.
        image_height: Image height.
        label_region: Optional selected ROI.
        detected_regions: Candidate regions.
        roi_detection_enabled: Whether ROI detection was expected.

    Returns:
        Quality issues.
    """
    issues: list[QualityIssue] = []
    if roi_detection_enabled and label_region is None:
        issues.append(_issue("roi_not_found", "review", {"roi_detection_enabled": True}))

    product_regions = [
        region
        for region in detected_regions
        if region is not None and region.label in {"supplement_bottle", "supplement_label"}
    ]
    if len(product_regions) > 1:
        issues.append(
            _issue("multi_product", "review", {"detected_region_count": len(product_regions)})
        )

    if label_region is not None:
        roi_area_ratio = metrics.get("roi_area_ratio")
        roi_min_dimension = metrics.get("roi_min_dimension_px")
        if label_region.label == "brand_front_label":
            issues.append(_issue("cover_only", "retake", {"label": label_region.label}))
        if isinstance(roi_area_ratio, float) and roi_area_ratio < MIN_ROI_AREA_RATIO:
            issues.append(_issue("too_small_text", "retake", {"roi_area_ratio": roi_area_ratio}))
        if isinstance(roi_min_dimension, int) and roi_min_dimension < MIN_ROI_DIMENSION_PX:
            issues.append(
                _issue("too_small_text", "retake", {"roi_min_dimension_px": roi_min_dimension})
            )
        if _touches_image_edge(label_region, image_width=image_width, image_height=image_height):
            issues.append(_issue("partial_table", "retake", _roi_edge_evidence(label_region)))

    if _metric_below(metrics, "mean_luminance", LOW_LIGHT_MEAN_LUMINANCE):
        issues.append(_issue("low_light", "retake", {"mean_luminance": metrics["mean_luminance"]}))
    if _metric_below(metrics, "luminance_stddev", LOW_CONTRAST_STDDEV):
        issues.append(
            _issue("low_contrast", "retake", {"luminance_stddev": metrics["luminance_stddev"]})
        )
    if _metric_below(metrics, "edge_strength_proxy", BLUR_EDGE_STRENGTH):
        issues.append(
            _issue(
                "blurred_text", "retake", {"edge_strength_proxy": metrics["edge_strength_proxy"]}
            )
        )
    glare_ratio = metrics.get("glare_pixel_ratio")
    luminance_stddev = metrics.get("luminance_stddev")
    if (
        isinstance(glare_ratio, float)
        and isinstance(luminance_stddev, float)
        and glare_ratio >= GLARE_PIXEL_RATIO
        and luminance_stddev >= LOW_CONTRAST_STDDEV
    ):
        issues.append(_issue("glare_or_reflection", "retake", {"glare_pixel_ratio": glare_ratio}))
    return _dedupe_issues(issues)


def _issue(
    reason_code: ImageQualityReasonCode,
    severity: ImageQualitySeverity,
    evidence: dict[str, float | int | str | bool | None],
) -> QualityIssue:
    """Create a quality issue with a safe message.

    Args:
        reason_code: Stable reason code.
        severity: Issue severity.
        evidence: Numeric or short categorical evidence.

    Returns:
        Quality issue.
    """
    messages = {
        "blurred_text": "The label photo may be too blurry for reliable OCR.",
        "glare_or_reflection": "The label photo may contain glare or reflection over text.",
        "low_light": "The label photo appears too dark for reliable OCR.",
        "low_contrast": "The label photo has low text/background contrast.",
        "too_small_text": "The detected OCR region may be too small.",
        "partial_table": "The detected label region may be cropped at an image edge.",
        "cover_only": "The image appears to show a front label rather than supplement facts.",
        "multi_product": "Multiple product-like regions were detected; user selection is required.",
        "unsupported_layout": "The label layout may require manual review.",
        "roi_not_found": "No supplement label ROI was detected; OCR should use the full image.",
    }
    return QualityIssue(
        reason_code=reason_code,
        severity=severity,
        message=messages[reason_code],
        evidence=evidence,
    )


def _detected_roi_from_box(
    box: BoundingBox,
    *,
    image_width: int,
    image_height: int,
) -> DetectedROI:
    """Convert a runtime bounding box into redacted ROI metadata.

    Args:
        box: Runtime ROI box.
        image_width: Full image width.
        image_height: Full image height.

    Returns:
        Sanitized ROI metadata.
    """
    return DetectedROI(
        label=box.label,
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        confidence=box.confidence,
        model=box.model,
        area_ratio=_roi_area_ratio(box, image_width=image_width, image_height=image_height),
    )


def _roi_area_ratio(
    box: BoundingBox | None,
    *,
    image_width: int,
    image_height: int,
) -> float | None:
    """Return ROI area ratio.

    Args:
        box: Optional ROI box.
        image_width: Full image width.
        image_height: Full image height.

    Returns:
        ROI area ratio, or None when no ROI exists.
    """
    if box is None or image_width <= 0 or image_height <= 0:
        return None
    return min(1.0, max(0.0, (box.width * box.height) / (image_width * image_height)))


def _touches_image_edge(box: BoundingBox, *, image_width: int, image_height: int) -> bool:
    """Return whether the ROI touches an image edge.

    Args:
        box: ROI box.
        image_width: Full image width.
        image_height: Full image height.

    Returns:
        True when the box touches any image edge within the configured margin.
    """
    return (
        box.x <= EDGE_TOUCH_MARGIN_PX
        or box.y <= EDGE_TOUCH_MARGIN_PX
        or box.x + box.width >= image_width - EDGE_TOUCH_MARGIN_PX
        or box.y + box.height >= image_height - EDGE_TOUCH_MARGIN_PX
    )


def _roi_edge_evidence(box: BoundingBox) -> dict[str, int | float | str | bool | None]:
    """Build safe evidence for an edge-touching ROI.

    Args:
        box: ROI box.

    Returns:
        Evidence dictionary.
    """
    return {"x": box.x, "y": box.y, "width": box.width, "height": box.height}


def _mean(values: list[int]) -> float:
    """Return the arithmetic mean.

    Args:
        values: Numeric values.

    Returns:
        Mean value.
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[int], mean: float) -> float:
    """Return population standard deviation.

    Args:
        values: Numeric values.
        mean: Precomputed mean.

    Returns:
        Standard deviation.
    """
    if not values:
        return 0.0
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _ratio(flags: Iterable[bool]) -> float:
    """Return the true ratio of a boolean iterable.

    Args:
        flags: Iterable of boolean values.

    Returns:
        Ratio of truthy values.
    """
    total = 0
    matched = 0
    for flag in flags:
        total += 1
        if flag:
            matched += 1
    if total == 0:
        return 0.0
    return matched / total


def _edge_strength(values: list[int], *, width: int, height: int) -> float:
    """Compute a simple average neighboring-pixel edge strength proxy.

    Args:
        values: Grayscale values.
        width: Image width.
        height: Image height.

    Returns:
        Average absolute neighbor difference.
    """
    if width <= 1 or height <= 1 or len(values) < width * height:
        return 0.0
    total = 0.0
    count = 0
    for y in range(height - 1):
        row = y * width
        next_row = (y + 1) * width
        for x in range(width - 1):
            pixel = values[row + x]
            total += abs(pixel - values[row + x + 1])
            total += abs(pixel - values[next_row + x])
            count += 2
    if count == 0:
        return 0.0
    return total / count


def _metric_below(
    metrics: dict[str, float | int | str | bool | None],
    key: str,
    threshold: float,
) -> bool:
    """Check whether a numeric metric is below a threshold.

    Args:
        metrics: Metric dictionary.
        key: Metric key.
        threshold: Threshold value.

    Returns:
        True when metric exists and is below the threshold.
    """
    value = metrics.get(key)
    return isinstance(value, int | float) and float(value) < threshold


def _status_for_issues(issues: list[QualityIssue]) -> ImageQualityStatus:
    """Return aggregate status for quality issues.

    Args:
        issues: Issue list.

    Returns:
        Quality status.
    """
    severities = {issue.severity for issue in issues}
    if "blocked" in severities:
        return "blocked"
    if "retake" in severities:
        return "retake_recommended"
    if severities:
        return "needs_review"
    return "acceptable"


def _dedupe_issues(issues: list[QualityIssue]) -> list[QualityIssue]:
    """Deduplicate issues by reason code while preserving first evidence.

    Args:
        issues: Candidate issues.

    Returns:
        Deduplicated issues.
    """
    deduped: list[QualityIssue] = []
    seen: set[str] = set()
    for issue in issues:
        if issue.reason_code in seen:
            continue
        deduped.append(issue)
        seen.add(issue.reason_code)
    return deduped

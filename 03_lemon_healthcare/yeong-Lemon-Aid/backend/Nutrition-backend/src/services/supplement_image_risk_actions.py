"""Structured risk-action mapping for supplement label image previews."""

from __future__ import annotations

from src.models.schemas.image_quality import ImageQualityReport
from src.models.schemas.supplement import (
    SupplementBarcodeLookupResponse,
    SupplementDetectedProductRegion,
    SupplementIdentityConflict,
    SupplementImageAnalysisScope,
    SupplementImageRiskActionContract,
    SupplementImageRiskActionRequired,
    SupplementImageRole,
    SupplementMissingRequiredSection,
)

_RETAKE_REASON_CODES = frozenset(
    {
        "blurred_text",
        "glare_or_reflection",
        "low_light",
        "low_contrast",
        "too_small_text",
        "partial_table",
    }
)
_ROLE_BY_LABEL: dict[str, SupplementImageRole] = {
    "brand_front_label": "front_label",
    "supplement_facts_table": "supplement_facts",
    "ingredients_section": "ingredients",
    "precautions_section": "precautions",
    "barcode_region": "barcode",
}
_MIN_CONTAINED_NAME_LENGTH = 3


def build_supplement_image_risk_action(
    *,
    image_quality_report: ImageQualityReport | None,
    barcode_lookup: SupplementBarcodeLookupResponse | None = None,
    parsed_product_name: str | None = None,
) -> SupplementImageRiskActionContract:
    """Build a mobile-safe action contract from image and identity metadata.

    Args:
        image_quality_report: Deterministic image-quality report, if available.
        barcode_lookup: Optional review-only barcode lookup response.
        parsed_product_name: Product name parsed from OCR or manual text.

    Returns:
        Structured risk-action contract without raw image, OCR text, or provider payloads.
    """
    reason_codes = _reason_codes(image_quality_report)
    regions = _detected_product_regions(image_quality_report, reason_codes)
    identity_conflict = _identity_conflict(
        barcode_lookup=barcode_lookup,
        parsed_product_name=parsed_product_name,
    )
    if image_quality_report is None and identity_conflict is None:
        return SupplementImageRiskActionContract()

    action_required = _action_required(reason_codes, image_quality_report)
    analysis_scope = _analysis_scope(
        reason_codes=reason_codes,
        action_required=action_required,
        has_selected_region=any(region.selected for region in regions),
    )
    missing_sections = _missing_required_sections(reason_codes)

    if identity_conflict is not None and action_required == "none":
        action_required = "review_required"
        analysis_scope = "full_image_review"

    return SupplementImageRiskActionContract(
        analysis_scope=analysis_scope,
        action_required=action_required,
        detected_product_regions=regions,
        selected_region_id=next((region.region_id for region in regions if region.selected), None),
        missing_required_sections=missing_sections,
        image_role=_image_role(reason_codes, regions),
        multi_image_group_id=None,
        source_type="uploaded_image",
        identity_conflict=identity_conflict,
    )


def _reason_codes(image_quality_report: ImageQualityReport | None) -> set[str]:
    """Return reason codes from a quality report.

    Args:
        image_quality_report: Deterministic image-quality report, if available.

    Returns:
        Set of stable reason codes.
    """
    if image_quality_report is None:
        return set()
    return {issue.reason_code for issue in image_quality_report.issues}


def _detected_product_regions(
    image_quality_report: ImageQualityReport | None,
    reason_codes: set[str],
) -> list[SupplementDetectedProductRegion]:
    """Convert quality-report ROIs into selectable preview regions.

    Args:
        image_quality_report: Deterministic image-quality report, if available.
        reason_codes: Quality issue reason codes.

    Returns:
        Bounded region metadata with request-local ids.
    """
    if image_quality_report is None:
        return []
    selection_allowed = "multi_product" not in reason_codes and "roi_not_found" not in reason_codes
    regions: list[SupplementDetectedProductRegion] = []
    for index, roi in enumerate(image_quality_report.detected_rois, start=1):
        region_id = f"roi-{index:03d}"
        regions.append(
            SupplementDetectedProductRegion(
                region_id=region_id,
                label=roi.label,
                x=roi.x,
                y=roi.y,
                width=roi.width,
                height=roi.height,
                confidence=roi.confidence,
                area_ratio=roi.area_ratio,
                selected=selection_allowed and index == 1,
            )
        )
    return regions


def _action_required(
    reason_codes: set[str],
    image_quality_report: ImageQualityReport | None,
) -> SupplementImageRiskActionRequired:
    """Map quality reason codes to the next required user action.

    Args:
        reason_codes: Quality issue reason codes.
        image_quality_report: Deterministic image-quality report, if available.

    Returns:
        Stable action code for mobile routing.
    """
    action: SupplementImageRiskActionRequired = "none"
    if image_quality_report is not None and image_quality_report.status == "blocked":
        action = "blocked"
    elif "multi_product" in reason_codes:
        action = "product_region_selection_required"
    elif "cover_only" in reason_codes:
        action = "additional_label_image_required"
    elif reason_codes & _RETAKE_REASON_CODES:
        action = "retake_recommended"
    elif "roi_not_found" in reason_codes or (
        image_quality_report is not None and image_quality_report.status == "needs_review"
    ):
        action = "review_required"
    return action


def _analysis_scope(
    *,
    reason_codes: set[str],
    action_required: SupplementImageRiskActionRequired,
    has_selected_region: bool,
) -> SupplementImageAnalysisScope:
    """Map action state to the safe analysis scope.

    Args:
        reason_codes: Quality issue reason codes.
        action_required: Required action code.
        has_selected_region: Whether a region was safely selected.

    Returns:
        Analysis scope code.
    """
    if "multi_product" in reason_codes:
        return "multi_product_review"
    if "cover_only" in reason_codes:
        return "identity_only"
    if action_required in {"retake_recommended", "review_required", "blocked"}:
        return "full_image_review"
    if has_selected_region:
        return "selected_roi_review"
    if reason_codes:
        return "full_image_review"
    return "full_label"


def _missing_required_sections(reason_codes: set[str]) -> list[SupplementMissingRequiredSection]:
    """Return label sections that require additional image evidence.

    Args:
        reason_codes: Quality issue reason codes.

    Returns:
        Missing section codes for the preview UI.
    """
    sections: list[SupplementMissingRequiredSection] = []
    if "cover_only" in reason_codes or "partial_table" in reason_codes:
        sections.append("supplement_facts")
    return sections


def _image_role(
    reason_codes: set[str],
    regions: list[SupplementDetectedProductRegion],
) -> SupplementImageRole:
    """Infer the uploaded image role from quality issues and region labels.

    Args:
        reason_codes: Quality issue reason codes.
        regions: Bounded detected regions.

    Returns:
        Conservative image role code.
    """
    if "multi_product" in reason_codes:
        return "mixed"
    if "cover_only" in reason_codes:
        return "front_label"
    for region in regions:
        if region.label and region.label in _ROLE_BY_LABEL:
            return _ROLE_BY_LABEL[region.label]
    return "unknown"


def _identity_conflict(
    *,
    barcode_lookup: SupplementBarcodeLookupResponse | None,
    parsed_product_name: str | None,
) -> SupplementIdentityConflict | None:
    """Detect a review-only barcode/product-name mismatch.

    Args:
        barcode_lookup: Optional barcode lookup response.
        parsed_product_name: Product name parsed from OCR or manual text.

    Returns:
        Identity conflict metadata, or None when no mismatch can be established.
    """
    if barcode_lookup is None or not barcode_lookup.candidates or not parsed_product_name:
        return None
    candidate = barcode_lookup.candidates[0]
    if _names_can_match(parsed_product_name, candidate.product_name):
        return None
    return SupplementIdentityConflict(
        conflict_type="barcode_product_mismatch",
        message=(
            "The scanned barcode product candidate does not match the parsed label identity. "
            "Confirm the product before using extracted details."
        ),
        evidence={
            "barcode_candidate_count": barcode_lookup.candidate_count,
            "parsed_product_present": True,
            "barcode_candidate_present": True,
        },
    )


def _names_can_match(left: str, right: str) -> bool:
    """Return whether two product-name strings are compatible enough for review.

    Args:
        left: First product-name candidate.
        right: Second product-name candidate.

    Returns:
        True when normalized names are equal or one clearly contains the other.
    """
    left_normalized = _normalize_name(left)
    right_normalized = _normalize_name(right)
    if not left_normalized or not right_normalized:
        return True
    if left_normalized == right_normalized:
        return True
    return (
        len(left_normalized) >= _MIN_CONTAINED_NAME_LENGTH
        and len(right_normalized) >= _MIN_CONTAINED_NAME_LENGTH
        and (left_normalized in right_normalized or right_normalized in left_normalized)
    )


def _normalize_name(value: str) -> str:
    """Normalize a product name for conservative identity comparison.

    Args:
        value: Product-name candidate.

    Returns:
        Lowercase alphanumeric-only name string.
    """
    return "".join(character for character in value.casefold() if character.isalnum())

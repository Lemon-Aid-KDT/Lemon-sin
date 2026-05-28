"""Schemas for supplement image analysis pipeline metadata."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OCRConfidenceBucket = Literal["none", "unknown", "low", "medium", "high"]
OCR_CONFIDENCE_MEDIUM_THRESHOLD = Decimal("0.80")
OCR_CONFIDENCE_HIGH_THRESHOLD = Decimal("0.90")


class SupplementImagePipelineMetadata(BaseModel):
    """Non-sensitive metadata for the image analysis pipeline.

    Attributes:
        intake_completed: Whether validated intake and preview persistence completed.
        image_count: Number of images represented by the preview.
        image_role: Inferred role of this image in the analysis flow.
        vision_roi_used: Whether a vision-detected ROI was used before OCR.
        ocr_provider: OCR provider that produced text, if any.
        ocr_text_present: Whether OCR produced non-empty text without exposing it.
        ocr_confidence_bucket: Coarse OCR confidence band for diagnostics.
        roi_count: Number of safe ROI candidates used or returned.
        section_count: Number of bounded label sections available for review.
        llm_parser_used: Whether structured text parsing was invoked.
        parser_contract_version: Parser/schema version used for structured parsing.
        missing_required_sections: Required label sections still missing from evidence.
        raw_image_stored: Whether raw image bytes were retained.
        raw_ocr_text_stored: Whether raw OCR text was retained.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intake_completed: bool
    image_count: int = Field(default=1, ge=1, le=20)
    image_role: str = Field(default="unknown", min_length=1, max_length=80)
    vision_roi_used: bool = False
    ocr_provider: str | None = Field(default=None, max_length=64)
    ocr_text_present: bool = False
    ocr_confidence_bucket: OCRConfidenceBucket = "none"
    roi_count: int = Field(default=0, ge=0, le=40)
    section_count: int = Field(default=0, ge=0, le=40)
    llm_parser_used: bool = False
    parser_contract_version: str | None = Field(default=None, max_length=80)
    missing_required_sections: list[str] = Field(default_factory=list, max_length=10)
    raw_image_stored: bool = False
    raw_ocr_text_stored: bool = False


def bucket_ocr_confidence(
    confidence: Decimal | float | int | None,
    *,
    ocr_text_present: bool,
) -> OCRConfidenceBucket:
    """Return a coarse OCR confidence bucket without exposing OCR text.

    Args:
        confidence: Provider-level confidence, if the provider emitted one.
        ocr_text_present: Whether OCR produced non-empty text.

    Returns:
        Stable confidence bucket for UI diagnostics and smoke tests.
    """
    if not ocr_text_present:
        return "none"
    if confidence is None:
        return "unknown"
    normalized = Decimal(str(confidence))
    if normalized < OCR_CONFIDENCE_MEDIUM_THRESHOLD:
        return "low"
    if normalized < OCR_CONFIDENCE_HIGH_THRESHOLD:
        return "medium"
    return "high"


def count_snapshot_list(value: object) -> int:
    """Count list items in a sanitized parsed snapshot field.

    Args:
        value: Candidate JSON list.

    Returns:
        Number of items when value is a list, otherwise zero.
    """
    if isinstance(value, list):
        return len(value)
    return 0


def safe_snapshot_string(value: object, *, default: str) -> str:
    """Return a trimmed snapshot string or a fallback.

    Args:
        value: Candidate snapshot value.
        default: Fallback string when value is not usable.

    Returns:
        Trimmed string value or default.
    """
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def parser_contract_version(parser_metadata: object) -> str | None:
    """Extract a parser contract version from sanitized metadata.

    Args:
        parser_metadata: Candidate parser metadata object.

    Returns:
        Parser algorithm version when present.
    """
    if not isinstance(parser_metadata, dict):
        return None
    version = parser_metadata.get("algorithm_version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def infer_missing_required_sections(
    parsed_snapshot: dict[str, object],
    *,
    ocr_text_present: bool,
) -> list[str]:
    """Infer missing label sections without exposing raw OCR text.

    Args:
        parsed_snapshot: Sanitized parsed snapshot JSON.
        ocr_text_present: Whether OCR produced non-empty text.

    Returns:
        Missing-section codes for developer and review UI diagnostics.
    """
    raw_sections = parsed_snapshot.get("missing_required_sections")
    if isinstance(raw_sections, list):
        normalized = [
            item.strip() for item in raw_sections if isinstance(item, str) and item.strip()
        ]
        if normalized:
            return normalized[:10]

    missing: list[str] = []
    label_sections = parsed_snapshot.get("label_sections")
    section_types = (
        {
            item.get("section_type")
            for item in label_sections
            if isinstance(item, dict) and isinstance(item.get("section_type"), str)
        }
        if isinstance(label_sections, list)
        else set()
    )

    ingredient_candidates = parsed_snapshot.get("ingredient_candidates")
    has_ingredients = isinstance(ingredient_candidates, list) and bool(ingredient_candidates)
    has_facts_section = bool({"supplement_facts", "ingredients", "nutrition_info"} & section_types)
    if not ocr_text_present or not (has_ingredients or has_facts_section):
        missing.append("supplement_facts")

    intake = parsed_snapshot.get("intake_method")
    has_intake_method = (
        isinstance(intake, dict)
        and isinstance(intake.get("text"), str)
        and bool(intake["text"].strip())
    ) or "intake_method" in section_types
    if not has_intake_method:
        missing.append("intake_method")
    return missing

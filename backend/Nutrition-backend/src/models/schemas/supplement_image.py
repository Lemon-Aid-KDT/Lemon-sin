"""Schemas for supplement image analysis pipeline metadata."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SupplementImagePipelineMetadata(BaseModel):
    """Non-sensitive metadata for the image analysis pipeline.

    Attributes:
        intake_completed: Whether validated intake and preview persistence completed.
        vision_roi_used: Whether a vision-detected ROI was used before OCR.
        ocr_provider: OCR provider that produced text, if any.
        llm_parser_used: Whether structured text parsing was invoked.
        raw_image_stored: Whether raw image bytes were retained.
        raw_ocr_text_stored: Whether raw OCR text was retained.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intake_completed: bool
    vision_roi_used: bool = False
    ocr_provider: str | None = Field(default=None, max_length=64)
    llm_parser_used: bool = False
    raw_image_stored: bool = False
    raw_ocr_text_stored: bool = False

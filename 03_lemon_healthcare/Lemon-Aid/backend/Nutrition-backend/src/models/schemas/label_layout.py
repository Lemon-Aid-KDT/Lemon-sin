"""Coordinate-derived supplement label layout DTOs."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SectionType = Literal[
    "daily_intake",
    "nutrition_function_info",
    "intake_method",
    "precautions",
    "ingredients",
    "functionality",
    "storage_method",
    "unknown",
]


class LayoutParserOptions(BaseModel):
    """Deterministic layout parser thresholds.

    Attributes:
        row_y_tolerance_ratio: Fraction of median word height used for row grouping.
        column_gap_ratio: Fraction of median word width used for cell splitting.
        max_section_gap_rows: Maximum rows allowed in a detected section before warning.
    """

    model_config = ConfigDict(frozen=True)

    row_y_tolerance_ratio: float = Field(default=0.65, gt=0)
    column_gap_ratio: float = Field(default=1.8, gt=0)
    max_section_gap_rows: int = Field(default=80, gt=0)


class LabelBox(BaseModel):
    """Axis-aligned OCR layout box.

    Attributes:
        page_index: Zero-based page index.
        left: Left x coordinate.
        top: Top y coordinate.
        right: Right x coordinate.
        bottom: Bottom y coordinate.
    """

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(ge=0)
    left: float = Field(ge=0)
    top: float = Field(ge=0)
    right: float = Field(gt=0)
    bottom: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_box_order(self) -> Self:
        """Validate coordinate ordering.

        Returns:
            Validated label box.

        Raises:
            ValueError: If right/bottom do not exceed left/top.
        """
        if self.right <= self.left:
            raise ValueError("right must be greater than left.")
        if self.bottom <= self.top:
            raise ValueError("bottom must be greater than top.")
        return self


class LabelCell(BaseModel):
    """One OCR-derived visual cell.

    Attributes:
        row_index: Section-local row index.
        column_index: Section-local column index.
        text: Cell text. This is bounded preview text, not persisted raw OCR output.
        bounding_box: Cell bounding box.
        confidence: Optional average OCR confidence.
        word_count: Number of OCR words merged into this cell.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=240)
    bounding_box: LabelBox
    confidence: float | None = Field(default=None, ge=0, le=1)
    word_count: int = Field(default=1, ge=1)


class LabelSection(BaseModel):
    """Semantic supplement label section.

    Attributes:
        section_type: Normalized section type.
        anchor_text: Detected anchor text when a known heading was found.
        anchor_box: Bounding box of the detected section anchor.
        rows: Section-local rows of cells.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    section_type: SectionType
    anchor_text: str | None = Field(default=None, max_length=120)
    anchor_box: LabelBox | None = None
    rows: list[list[LabelCell]] = Field(default_factory=list, max_length=200)


class LabelLayout(BaseModel):
    """Parsed coordinate-derived OCR layout.

    Attributes:
        provider: OCR provider label.
        page_count: Number of OCR pages considered.
        sections: Semantic label sections.
        warnings: Non-sensitive parser warning codes.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=80)
    page_count: int = Field(ge=0)
    sections: list[LabelSection] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=80)


__all__ = [
    "LabelBox",
    "LabelCell",
    "LabelLayout",
    "LabelSection",
    "LayoutParserOptions",
    "SectionType",
]

"""Bounded layout context schemas for supplement OCR parser input."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPLEMENT_LAYOUT_CONTEXT_V1: Literal["supplement-layout-context-v1"] = (
    "supplement-layout-context-v1"
)

LayoutContextSectionType = Literal[
    "nutrition_info",
    "functional_info",
    "intake_method",
    "precautions",
    "ingredients",
    "storage_method",
    "unknown",
]


def _normalize_unique_strings(values: list[str]) -> list[str]:
    """Normalize string lists while preserving first-seen order.

    Args:
        values: Candidate string values.

    Returns:
        Trimmed unique string values.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


class SupplementLayoutCellEvidenceV1(BaseModel):
    """Cell-level evidence derived from deterministic OCR layout parsing.

    Attributes:
        span_id: Stable evidence id referenced by section and snapshot fields.
        section_id: Stable section id within the layout context.
        section_type: Normalized supplement label section type.
        page_index: Zero-based OCR page index when available.
        row_index: Zero-based row index within the parsed section.
        column_index: Zero-based column index within the parsed row.
        cell_ref: Stable section/row/column cell reference.
        text_excerpt: Short bounded OCR cell excerpt.
        confidence: Optional OCR/layout confidence from 0.0 to 1.0.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    span_id: str = Field(min_length=1, max_length=120)
    section_id: str = Field(min_length=1, max_length=80)
    section_type: LayoutContextSectionType
    page_index: int | None = Field(default=None, ge=0)
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    cell_ref: str = Field(min_length=1, max_length=160)
    text_excerpt: str = Field(min_length=1, max_length=240)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SupplementLayoutContextSectionV1(BaseModel):
    """Bounded semantic section produced from a parsed label layout.

    Attributes:
        section_id: Stable section id in visual order.
        section_type: Normalized supplement label section type.
        source_section_type: Original ``LabelLayout`` section type.
        heading_text: Anchor or heading text detected by the layout parser.
        text_bundle: Bounded deterministic section text bundle.
        confidence: Optional average section confidence from cell confidences.
        requires_review: Whether UI should mark this section as needing review.
        evidence_refs: Evidence span ids supporting this section.
        row_count: Number of parsed rows in the section.
        cell_count: Number of parsed cells in the section.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    section_id: str = Field(min_length=1, max_length=80)
    section_type: LayoutContextSectionType
    source_section_type: str = Field(min_length=1, max_length=80)
    heading_text: str | None = Field(default=None, max_length=120)
    text_bundle: str = Field(min_length=1, max_length=2_000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=80)
    row_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Candidate evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class SupplementLayoutContextV1(BaseModel):
    """Request-local and persisted summary of deterministic OCR layout parsing.

    ``parser_input_text`` is excluded from dumps so the full parser bundle is
    not persisted inside ``parsed_snapshot``. Persisted fields keep only bounded
    section summaries and short evidence excerpts.

    Attributes:
        schema_version: Fixed layout context schema version.
        provider: OCR provider label copied from the normalized OCR result.
        layout_available: Whether sectioned layout input is usable for parsing.
        parser_input_text: Request-local sectioned text sent to the LLM parser.
        sections: Bounded layout section summaries.
        evidence_spans: Cell evidence spans derived from layout cells.
        low_confidence_sections: Section ids requiring user review.
        low_confidence_fields: Snapshot field paths requiring user review.
        warnings: Safe layout warnings to surface in preview metadata.
        fallback_reason: Safe fallback reason when raw text parser is used.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["supplement-layout-context-v1"] = SUPPLEMENT_LAYOUT_CONTEXT_V1
    provider: str = Field(min_length=1, max_length=64)
    layout_available: bool = False
    parser_input_text: str | None = Field(default=None, max_length=50_000, exclude=True)
    sections: list[SupplementLayoutContextSectionV1] = Field(default_factory=list, max_length=40)
    evidence_spans: list[SupplementLayoutCellEvidenceV1] = Field(
        default_factory=list,
        max_length=160,
    )
    low_confidence_sections: list[str] = Field(default_factory=list, max_length=80)
    low_confidence_fields: list[str] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=50)
    fallback_reason: str | None = Field(default=None, max_length=120)

    @field_validator("low_confidence_sections", "low_confidence_fields", "warnings")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        """Normalize review and warning lists.

        Args:
            values: Candidate field paths, section ids, or warning strings.

        Returns:
            Trimmed unique strings.
        """
        return _normalize_unique_strings(values)


__all__ = [
    "SUPPLEMENT_LAYOUT_CONTEXT_V1",
    "LayoutContextSectionType",
    "SupplementLayoutCellEvidenceV1",
    "SupplementLayoutContextSectionV1",
    "SupplementLayoutContextV1",
]

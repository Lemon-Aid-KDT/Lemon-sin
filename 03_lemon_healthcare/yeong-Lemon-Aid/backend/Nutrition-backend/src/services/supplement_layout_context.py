"""Build sectioned parser input from deterministic supplement label layout."""

from __future__ import annotations

from collections.abc import Iterable

from src.config import Settings
from src.models.schemas.label_layout import LabelCell, LabelLayout, LabelSection, SectionType
from src.models.schemas.supplement_layout_context import (
    LayoutContextSectionType,
    SupplementLayoutCellEvidenceV1,
    SupplementLayoutContextSectionV1,
    SupplementLayoutContextV1,
)
from src.ocr.base import OCRResult
from src.parsing.layout_parser import parse_label_layout

LAYOUT_PAGES_UNAVAILABLE_REASON = "layout_pages_unavailable"
LAYOUT_PARSER_ERROR_REASON = "layout_parser_error"
LAYOUT_SECTIONS_EMPTY_REASON = "layout_sections_empty"
LAYOUT_SECTIONS_UNKNOWN_ONLY_REASON = "layout_sections_unknown_only"
LAYOUT_PARSER_INPUT_EMPTY_REASON = "layout_parser_input_empty"
LAYOUT_PARSER_INPUT_TOO_LONG_REASON = "layout_parser_input_too_long"

LAYOUT_FALLBACK_WARNING_PREFIX = "layout_fallback"
MAX_LAYOUT_CONTEXT_SECTIONS = 40
MAX_LAYOUT_CONTEXT_EVIDENCE_SPANS = 160
MAX_SECTION_EVIDENCE_REFS = 80
MAX_SECTION_TEXT_BUNDLE_CHARS = 2_000
MAX_EVIDENCE_EXCERPT_CHARS = 240

_SECTION_TYPE_MAP: dict[SectionType, LayoutContextSectionType] = {
    "daily_intake": "intake_method",
    "nutrition_function_info": "nutrition_info",
    "intake_method": "intake_method",
    "precautions": "precautions",
    "ingredients": "ingredients",
    "functionality": "functional_info",
    "storage_method": "storage_method",
    "unknown": "unknown",
}


def build_supplement_layout_context(
    ocr_result: OCRResult,
    settings: Settings,
) -> SupplementLayoutContextV1:
    """Build a bounded layout context for supplement OCR parser calls.

    Args:
        ocr_result: Normalized OCR result from any provider.
        settings: Runtime settings with confidence and parser length limits.

    Returns:
        Layout context with sectioned parser input when layout is usable.
    """
    try:
        layout = parse_label_layout(ocr_result)
    except (TypeError, ValueError) as exc:
        warning = f"{LAYOUT_PARSER_ERROR_REASON}:{exc.__class__.__name__}"
        return _fallback_context(
            ocr_result=ocr_result,
            reason=LAYOUT_PARSER_ERROR_REASON,
            warnings=[warning],
        )

    sections, evidence_spans = _build_sections_and_evidence(
        layout,
        confidence_threshold=settings.ocr_confidence_threshold,
    )
    fallback_reason = _fallback_reason_for_layout(layout, sections)
    parser_input_text = None
    if fallback_reason is None:
        parser_input_text = _build_parser_input_text(sections)
        if not parser_input_text:
            fallback_reason = LAYOUT_PARSER_INPUT_EMPTY_REASON
        elif len(parser_input_text) > settings.supplement_ocr_text_max_chars:
            fallback_reason = LAYOUT_PARSER_INPUT_TOO_LONG_REASON
            parser_input_text = None

    warnings = _merge_strings(layout.warnings)
    if fallback_reason is not None:
        warnings = _merge_strings(
            [*warnings, f"{LAYOUT_FALLBACK_WARNING_PREFIX}:{fallback_reason}"]
        )
        parser_input_text = None

    low_confidence_sections = [
        section.section_id for section in sections if section.requires_review
    ]
    low_confidence_fields = [
        f"layout_context.sections.{section_id}" for section_id in low_confidence_sections
    ]

    return SupplementLayoutContextV1(
        provider=ocr_result.provider,
        layout_available=fallback_reason is None,
        parser_input_text=parser_input_text,
        sections=sections,
        evidence_spans=evidence_spans,
        low_confidence_sections=low_confidence_sections,
        low_confidence_fields=low_confidence_fields,
        warnings=warnings,
        fallback_reason=fallback_reason,
    )


def _fallback_context(
    *,
    ocr_result: OCRResult,
    reason: str,
    warnings: list[str],
) -> SupplementLayoutContextV1:
    """Build a layout context for non-layout fallback.

    Args:
        ocr_result: Normalized OCR result.
        reason: Stable fallback reason.
        warnings: Safe warnings to persist.

    Returns:
        Fallback layout context.
    """
    return SupplementLayoutContextV1(
        provider=ocr_result.provider,
        layout_available=False,
        parser_input_text=None,
        sections=[],
        evidence_spans=[],
        low_confidence_sections=[],
        low_confidence_fields=[],
        warnings=_merge_strings([*warnings, f"{LAYOUT_FALLBACK_WARNING_PREFIX}:{reason}"]),
        fallback_reason=reason,
    )


def _build_sections_and_evidence(
    layout: LabelLayout,
    *,
    confidence_threshold: float,
) -> tuple[list[SupplementLayoutContextSectionV1], list[SupplementLayoutCellEvidenceV1]]:
    """Convert parsed label sections into bounded context sections and evidence.

    Args:
        layout: Coordinate-derived label layout.
        confidence_threshold: Internal threshold for user review routing.

    Returns:
        Context sections and cell evidence spans.
    """
    context_sections: list[SupplementLayoutContextSectionV1] = []
    evidence_spans: list[SupplementLayoutCellEvidenceV1] = []
    has_layout_warnings = bool(layout.warnings)

    for section_index, section in enumerate(layout.sections[:MAX_LAYOUT_CONTEXT_SECTIONS]):
        section_id = f"sec-{section_index:03d}"
        section_type = _map_section_type(section.section_type)
        row_bundles = _format_section_rows(section, section_id)
        if not row_bundles:
            continue

        section_evidence_refs: list[str] = []
        cell_count = 0
        for row in section.rows:
            for cell in row:
                cell_count += 1
                if len(evidence_spans) >= MAX_LAYOUT_CONTEXT_EVIDENCE_SPANS:
                    continue
                cell_ref = _cell_ref(section_id, cell.row_index, cell.column_index)
                span_id = f"layout:{cell_ref}"
                evidence_spans.append(
                    SupplementLayoutCellEvidenceV1(
                        span_id=span_id,
                        section_id=section_id,
                        section_type=section_type,
                        page_index=cell.bounding_box.page_index,
                        row_index=cell.row_index,
                        column_index=cell.column_index,
                        cell_ref=cell_ref,
                        text_excerpt=_truncate_text(cell.text, MAX_EVIDENCE_EXCERPT_CHARS),
                        confidence=cell.confidence,
                    )
                )
                if len(section_evidence_refs) < MAX_SECTION_EVIDENCE_REFS:
                    section_evidence_refs.append(span_id)

        confidence = _average_confidence(_iter_section_cells(section))
        requires_review = (
            section_type == "unknown"
            or confidence is None
            or confidence < confidence_threshold
            or has_layout_warnings
        )
        text_bundle = _truncate_text("\n".join(row_bundles), MAX_SECTION_TEXT_BUNDLE_CHARS)
        context_sections.append(
            SupplementLayoutContextSectionV1(
                section_id=section_id,
                section_type=section_type,
                source_section_type=section.section_type,
                heading_text=section.anchor_text,
                text_bundle=text_bundle,
                confidence=confidence,
                requires_review=requires_review,
                evidence_refs=section_evidence_refs,
                row_count=len(section.rows),
                cell_count=cell_count,
            )
        )

    return context_sections, evidence_spans


def _fallback_reason_for_layout(
    layout: LabelLayout,
    sections: list[SupplementLayoutContextSectionV1],
) -> str | None:
    """Return a fallback reason when sectioned layout is unusable.

    Args:
        layout: Parsed label layout.
        sections: Bounded context sections.

    Returns:
        Stable fallback reason, or None when layout input is usable.
    """
    if layout.page_count == 0:
        return LAYOUT_PAGES_UNAVAILABLE_REASON
    if not sections:
        return LAYOUT_SECTIONS_EMPTY_REASON
    if all(section.section_type == "unknown" for section in sections):
        return LAYOUT_SECTIONS_UNKNOWN_ONLY_REASON
    return None


def _build_parser_input_text(sections: list[SupplementLayoutContextSectionV1]) -> str:
    """Build deterministic sectioned parser input text.

    Args:
        sections: Context sections in visual order.

    Returns:
        Sectioned text bundle for the structured parser.
    """
    chunks: list[str] = []
    for section in sections:
        review_marker = " review=required" if section.requires_review else ""
        confidence = "unknown" if section.confidence is None else f"{section.confidence:.4f}"
        chunks.append(
            "\n".join(
                [
                    (
                        f"[section:{section.section_type} section_id={section.section_id} "
                        f"source={section.source_section_type} confidence={confidence}"
                        f"{review_marker}]"
                    ),
                    section.text_bundle,
                ]
            )
        )
    return "\n\n".join(chunks).strip()


def _format_section_rows(section: LabelSection, section_id: str) -> list[str]:
    """Format section rows into stable row/column text lines.

    Args:
        section: Parsed label section.
        section_id: Stable context section id.

    Returns:
        Deterministic row bundle lines.
    """
    row_lines: list[str] = []
    for row_index, row in enumerate(section.rows):
        cell_parts = []
        for cell in row:
            cell_ref = _cell_ref(section_id, cell.row_index, cell.column_index)
            cell_text = _normalize_inline_text(cell.text)
            if not cell_text:
                continue
            cell_parts.append(f"col={cell.column_index} cell={cell_ref}: {cell_text}")
        if cell_parts:
            row_lines.append(f"row={row_index} | " + " | ".join(cell_parts))
    return row_lines


def _map_section_type(section_type: SectionType) -> LayoutContextSectionType:
    """Map layout parser section types to snapshot-compatible section types.

    Args:
        section_type: Section type emitted by ``LabelLayout``.

    Returns:
        Snapshot-compatible layout context section type.
    """
    return _SECTION_TYPE_MAP.get(section_type, "unknown")


def _iter_section_cells(section: LabelSection) -> Iterable[LabelCell]:
    """Yield cells from a label section.

    Args:
        section: Parsed label section.

    Yields:
        Cells in row/column order.
    """
    for row in section.rows:
        yield from row


def _average_confidence(cells: Iterable[LabelCell]) -> float | None:
    """Calculate average cell confidence.

    Args:
        cells: Section cells.

    Returns:
        Average confidence, or None when no cell confidence is available.
    """
    values = [cell.confidence for cell in cells if cell.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _cell_ref(section_id: str, row_index: int, column_index: int) -> str:
    """Build a stable cell reference.

    Args:
        section_id: Stable section id.
        row_index: Zero-based row index.
        column_index: Zero-based column index.

    Returns:
        Stable cell reference.
    """
    return f"{section_id}:r{row_index:03d}:c{column_index:03d}"


def _normalize_inline_text(value: str) -> str:
    """Normalize OCR text for a single section row.

    Args:
        value: Candidate OCR cell text.

    Returns:
        Single-line text with collapsed whitespace.
    """
    return " ".join(value.split())


def _truncate_text(value: str, max_chars: int) -> str:
    """Trim text to a bounded storage length.

    Args:
        value: Candidate text.
        max_chars: Maximum characters to keep.

    Returns:
        Bounded text with leading/trailing whitespace removed.
    """
    normalized = value.strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


def _merge_strings(values: list[str]) -> list[str]:
    """Normalize and deduplicate strings.

    Args:
        values: Candidate strings.

    Returns:
        Trimmed unique strings.
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


__all__ = [
    "LAYOUT_FALLBACK_WARNING_PREFIX",
    "LAYOUT_PAGES_UNAVAILABLE_REASON",
    "LAYOUT_PARSER_ERROR_REASON",
    "LAYOUT_PARSER_INPUT_EMPTY_REASON",
    "LAYOUT_PARSER_INPUT_TOO_LONG_REASON",
    "LAYOUT_SECTIONS_EMPTY_REASON",
    "LAYOUT_SECTIONS_UNKNOWN_ONLY_REASON",
    "build_supplement_layout_context",
]

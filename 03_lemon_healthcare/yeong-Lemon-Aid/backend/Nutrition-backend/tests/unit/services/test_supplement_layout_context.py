"""Supplement layout context builder tests."""

from __future__ import annotations

from pydantic import SecretStr
from src.config import Settings
from src.ocr.base import (
    OCRBlock,
    OCRBoundingPoly,
    OCRPage,
    OCRParagraph,
    OCRResult,
    OCRVertex,
    OCRWord,
)
from src.services.supplement_layout_context import (
    LAYOUT_PAGES_UNAVAILABLE_REASON,
    LAYOUT_SECTIONS_UNKNOWN_ONLY_REASON,
    build_supplement_layout_context,
)


def _settings() -> Settings:
    """Return layout context test settings.

    Returns:
        Settings object.
    """
    return Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))


def _word(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    confidence: float | None = 0.9,
    word_index: int = 0,
) -> OCRWord:
    """Build an OCR word with a rectangular bounding polygon.

    Args:
        text: OCR word text.
        left: Left coordinate.
        top: Top coordinate.
        right: Right coordinate.
        bottom: Bottom coordinate.
        confidence: Optional OCR word confidence.
        word_index: Word index inside a paragraph.

    Returns:
        OCR word fixture.
    """
    return OCRWord(
        text=text,
        confidence=confidence,
        bounding_box=OCRBoundingPoly(
            vertices=(
                OCRVertex(left, top),
                OCRVertex(right, top),
                OCRVertex(right, bottom),
                OCRVertex(left, bottom),
            )
        ),
        block_index=0,
        paragraph_index=0,
        word_index=word_index,
    )


def _ocr_result(
    words: tuple[OCRWord, ...],
    *,
    provider: str = "google_vision_document",
) -> OCRResult:
    """Build a normalized one-page OCR result.

    Args:
        words: OCR words.
        provider: OCR provider label.

    Returns:
        OCR result fixture.
    """
    return OCRResult(
        text="\n".join(word.text for word in words),
        provider=provider,
        confidence=0.92,
        pages=(
            OCRPage(
                width=400,
                height=260,
                confidence=0.92,
                blocks=(
                    OCRBlock(
                        text=" ".join(word.text for word in words),
                        confidence=0.92,
                        bounding_box=None,
                        block_type="TEXT",
                        paragraphs=(
                            OCRParagraph(
                                text=" ".join(word.text for word in words),
                                confidence=0.92,
                                bounding_box=None,
                                words=words,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_build_supplement_layout_context_creates_deterministic_sectioned_input() -> None:
    """Verify layout context turns OCR coordinates into sectioned parser input."""
    words = (
        _word("영양·기능정보", 10, 10, 120, 24, word_index=0),
        _word("비타민", 10, 40, 50, 53, word_index=1),
        _word("D", 56, 40, 66, 53, word_index=2),
        _word("25", 150, 40, 170, 53, word_index=3),
        _word("ug", 176, 40, 194, 53, word_index=4),
        _word("섭취방법", 10, 78, 76, 92, word_index=5),
        _word("1일", 10, 104, 40, 118, word_index=6),
        _word("1회", 46, 104, 76, 118, word_index=7),
        _word("1정", 82, 104, 112, 118, word_index=8),
    )

    first = build_supplement_layout_context(_ocr_result(words), _settings())
    second = build_supplement_layout_context(_ocr_result(words), _settings())

    assert first.layout_available is True
    assert first.fallback_reason is None
    assert first.parser_input_text == second.parser_input_text
    assert first.parser_input_text is not None
    assert "[section:nutrition_info section_id=sec-000" in first.parser_input_text
    assert "[section:intake_method section_id=sec-001" in first.parser_input_text
    assert "cell=sec-000:r001:c000: 비타민 D" in first.parser_input_text
    assert first.sections[0].section_type == "nutrition_info"
    assert first.evidence_spans[0].cell_ref == "sec-000:r000:c000"
    assert "parser_input_text" not in first.model_dump(mode="json", exclude_none=True)


def test_build_supplement_layout_context_falls_back_without_pages() -> None:
    """Verify flat OCR text falls back to the raw text parser path."""
    context = build_supplement_layout_context(
        OCRResult(text="비타민 D 25 ug", provider="manual", confidence=None),
        _settings(),
    )

    assert context.layout_available is False
    assert context.parser_input_text is None
    assert context.fallback_reason == LAYOUT_PAGES_UNAVAILABLE_REASON
    assert "layout_fallback:layout_pages_unavailable" in context.warnings


def test_build_supplement_layout_context_falls_back_for_unknown_only_sections() -> None:
    """Verify sectioned input is not used when no semantic anchor is visible."""
    words = (
        _word("비타민", 10, 10, 50, 22, word_index=0),
        _word("D", 56, 10, 66, 22, word_index=1),
        _word("25", 150, 10, 170, 22, word_index=2),
        _word("ug", 176, 10, 194, 22, word_index=3),
    )

    context = build_supplement_layout_context(_ocr_result(words), _settings())

    assert context.layout_available is False
    assert context.parser_input_text is None
    assert context.fallback_reason == LAYOUT_SECTIONS_UNKNOWN_ONLY_REASON
    assert context.sections[0].section_type == "unknown"
    assert context.low_confidence_fields == ["layout_context.sections.sec-000"]

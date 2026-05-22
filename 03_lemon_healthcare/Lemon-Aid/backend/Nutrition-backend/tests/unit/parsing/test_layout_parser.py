"""Layout parser regression tests."""

from __future__ import annotations

from src.ocr.base import (
    OCRBlock,
    OCRBoundingPoly,
    OCRPage,
    OCRParagraph,
    OCRResult,
    OCRVertex,
    OCRWord,
)
from src.parsing.layout_parser import (
    COORDINATE_SCALE_WARNING,
    LAYOUT_UNAVAILABLE_WARNING,
    LAYOUT_WORDS_UNAVAILABLE_WARNING,
    MISSING_BOUNDING_BOX_WARNING,
    parse_label_layout,
)


def _word(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    confidence: float = 0.9,
) -> OCRWord:
    """Return one boxed OCR word."""
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
    )


def _result(
    words: tuple[OCRWord, ...],
    *,
    width: int = 1000,
    height: int = 800,
) -> OCRResult:
    """Return an OCR result with a single page and paragraph."""
    return OCRResult(
        text=" ".join(word.text for word in words),
        provider="paddleocr_local",
        confidence=0.9,
        pages=(
            OCRPage(
                width=width,
                height=height,
                blocks=(OCRBlock(paragraphs=(OCRParagraph(words=words),)),),
            ),
        ),
    )


def test_parse_label_layout_returns_warning_when_pages_missing() -> None:
    """Verify layout parsing degrades safely when providers omit pages."""
    layout = parse_label_layout(
        OCRResult(text="비타민 C 500 mg", provider="paddleocr_local", confidence=0.9)
    )

    assert layout.sections == []
    assert layout.warnings == [LAYOUT_UNAVAILABLE_WARNING]


def test_parse_label_layout_reports_missing_bounding_boxes() -> None:
    """Verify missing word boxes are reported without raw OCR persistence."""
    layout = parse_label_layout(
        _result((OCRWord(text="비타민 C", bounding_box=None, confidence=0.9),))
    )

    assert layout.sections == []
    assert f"{MISSING_BOUNDING_BOX_WARNING}:1" in layout.warnings
    assert LAYOUT_WORDS_UNAVAILABLE_WARNING in layout.warnings


def test_parse_label_layout_reports_coordinate_scale_mismatch() -> None:
    """Verify out-of-page coordinates remain parseable but warning-backed."""
    layout = parse_label_layout(_result((_word("비타민 C", 0, 0, 180, 40),), width=100, height=100))

    assert layout.sections[0].section_type == "unknown"
    assert f"{COORDINATE_SCALE_WARNING}:1" in layout.warnings


def test_parse_label_layout_detects_korean_anchor_variation() -> None:
    """Verify Korean section anchor variants map to stable section types."""
    layout = parse_label_layout(
        _result(
            (
                _word("영양", 20, 20, 80, 45),
                _word("기능정보", 90, 20, 180, 45),
                _word("비타민", 20, 75, 90, 100),
                _word("C", 95, 75, 115, 100),
                _word("500", 280, 75, 340, 100),
                _word("mg", 345, 75, 380, 100),
            )
        )
    )

    assert layout.sections[0].section_type == "nutrition_function_info"
    assert layout.sections[0].anchor_text == "영양·기능정보"
    assert layout.sections[0].rows[1][0].text == "비타민 C"

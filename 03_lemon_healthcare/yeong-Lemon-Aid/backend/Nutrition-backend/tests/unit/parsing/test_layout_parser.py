"""Coordinate-based label layout parser tests."""

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
    INVALID_BOUNDING_BOX_WARNING,
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


def _ocr_result(words: tuple[OCRWord, ...], *, provider: str = "fixture_ocr") -> OCRResult:
    """Build a one-page OCR result from words.

    Args:
        words: OCR words.
        provider: Provider label.

    Returns:
        OCR result fixture.
    """
    return OCRResult(
        text="\n".join(word.text for word in words),
        provider=provider,
        confidence=0.9,
        pages=(
            OCRPage(
                width=400,
                height=260,
                confidence=0.9,
                blocks=(
                    OCRBlock(
                        text=" ".join(word.text for word in words),
                        confidence=0.9,
                        bounding_box=None,
                        block_type="TEXT",
                        paragraphs=(
                            OCRParagraph(
                                text=" ".join(word.text for word in words),
                                confidence=0.9,
                                bounding_box=None,
                                words=words,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_parse_label_layout_restores_rows_and_columns_from_google_like_fixture() -> None:
    """Verify y-band and x-gap grouping reconstruct a nutrition table."""
    words = (
        _word("영양·기능정보", 10, 10, 120, 24, word_index=0),
        _word("성분", 10, 39, 42, 51, word_index=1),
        _word("함량", 150, 40, 182, 52, word_index=2),
        _word("%기준치", 260, 39, 312, 51, word_index=3),
        _word("비타민", 10, 60, 50, 73, confidence=0.91, word_index=4),
        _word("D", 55, 61, 66, 74, confidence=0.89, word_index=5),
        _word("25", 150, 60, 170, 73, confidence=0.88, word_index=6),
        _word("ug", 176, 61, 194, 74, confidence=0.86, word_index=7),
        _word("250%", 260, 60, 304, 73, confidence=0.84, word_index=8),
        _word("아연", 10, 82, 40, 95, word_index=9),
        _word("8.5", 150, 82, 176, 95, word_index=10),
        _word("mg", 182, 82, 202, 95, word_index=11),
        _word("100%", 260, 82, 304, 95, word_index=12),
    )

    layout = parse_label_layout(_ocr_result(words, provider="google_vision_document"))

    assert layout.provider == "google_vision_document"
    assert layout.page_count == 1
    assert layout.warnings == []
    assert len(layout.sections) == 1
    section = layout.sections[0]
    assert section.section_type == "nutrition_function_info"
    assert section.anchor_text == "영양·기능정보"
    assert section.rows[0][0].text == "영양·기능정보"
    assert [cell.text for cell in section.rows[1]] == ["성분", "함량", "%기준치"]
    assert [cell.column_index for cell in section.rows[1]] == [0, 1, 2]
    assert [cell.text for cell in section.rows[2]] == ["비타민 D", "25 ug", "250%"]
    assert section.rows[2][0].confidence == 0.9
    assert section.rows[2][1].confidence == 0.87
    dumped = layout.model_dump()
    assert dumped["sections"][0]["rows"][2][0]["text"] == "비타민 D"


def test_parse_label_layout_detects_korean_section_anchors() -> None:
    """Verify configured Korean anchors split rows into semantic sections."""
    words = (
        _word("원재료명", 10, 10, 76, 22, word_index=0),
        _word("정제어유", 10, 32, 68, 44, word_index=1),
        _word("젤라틴", 78, 32, 126, 44, word_index=2),
        _word("섭취방법", 10, 70, 76, 82, word_index=3),
        _word("1일", 10, 92, 40, 104, word_index=4),
        _word("1회", 46, 92, 76, 104, word_index=5),
        _word("2캡슐", 82, 92, 130, 104, word_index=6),
        _word("섭취시", 10, 130, 56, 142, word_index=7),
        _word("주의사항", 62, 130, 126, 142, word_index=8),
        _word("질환자는", 10, 152, 78, 164, word_index=9),
        _word("전문가와", 84, 152, 152, 164, word_index=10),
        _word("상담", 158, 152, 190, 164, word_index=11),
    )

    layout = parse_label_layout(_ocr_result(words))

    assert [section.section_type for section in layout.sections] == [
        "ingredients",
        "intake_method",
        "precautions",
    ]
    assert layout.sections[0].rows[1][0].text == "정제어유 젤라틴"
    assert layout.sections[1].rows[1][0].text == "1일 1회 2캡슐"
    assert layout.sections[2].anchor_text == "섭취 시 주의사항"
    assert layout.sections[2].rows[1][0].text == "질환자는 전문가와 상담"


def test_parse_label_layout_detects_storage_method_anchor() -> None:
    """Verify storage-method rows are not merged into generic precautions."""
    words = (
        _word("보관방법", 10, 10, 76, 22, word_index=0),
        _word("직사광선을", 10, 32, 88, 44, word_index=1),
        _word("피하여", 94, 32, 142, 44, word_index=2),
        _word("보관", 148, 32, 180, 44, word_index=3),
    )

    layout = parse_label_layout(_ocr_result(words))

    assert len(layout.sections) == 1
    assert layout.sections[0].section_type == "storage_method"
    assert layout.sections[0].rows[1][0].text == "직사광선을 피하여 보관"


def test_parse_label_layout_preserves_unknown_rows_without_anchor() -> None:
    """Verify rows are preserved as unknown when no section anchor is visible."""
    words = (
        _word("비타민", 10, 10, 50, 22, word_index=0),
        _word("D", 56, 10, 66, 22, word_index=1),
        _word("25", 150, 10, 170, 22, word_index=2),
        _word("ug", 176, 10, 194, 22, word_index=3),
    )

    layout = parse_label_layout(_ocr_result(words))

    assert len(layout.sections) == 1
    assert layout.sections[0].section_type == "unknown"
    assert [cell.text for cell in layout.sections[0].rows[0]] == ["비타민 D", "25 ug"]


def test_parse_label_layout_warns_for_missing_and_invalid_bounding_boxes() -> None:
    """Verify missing or invalid word coordinates degrade without fabricating layout."""
    words = (
        OCRWord(
            text="원재료명",
            confidence=0.9,
            bounding_box=None,
            block_index=0,
            paragraph_index=0,
            word_index=0,
        ),
        OCRWord(
            text="비타민",
            confidence=0.9,
            bounding_box=OCRBoundingPoly(vertices=(OCRVertex(0, 0),)),
            block_index=0,
            paragraph_index=0,
            word_index=1,
        ),
    )

    layout = parse_label_layout(_ocr_result(words))

    assert layout.sections == []
    assert f"{MISSING_BOUNDING_BOX_WARNING}:1" in layout.warnings
    assert f"{INVALID_BOUNDING_BOX_WARNING}:1" in layout.warnings
    assert LAYOUT_WORDS_UNAVAILABLE_WARNING in layout.warnings


def test_parse_label_layout_returns_unavailable_warning_without_pages() -> None:
    """Verify flat OCR text without layout pages returns a degraded layout artifact."""
    layout = parse_label_layout(
        OCRResult(
            text="비타민 D 25 ug",
            provider="flat_ocr",
            confidence=None,
            pages=(),
        )
    )

    assert layout.provider == "flat_ocr"
    assert layout.page_count == 0
    assert layout.sections == []
    assert layout.warnings == [LAYOUT_UNAVAILABLE_WARNING]

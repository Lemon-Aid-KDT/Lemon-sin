"""OCR 배치 처리 테스트"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.ocr import DrawingOCR, OCRResult


class TestExtractBatch:
    """extract_batch() 메서드 테스트"""

    def test_empty_list(self):
        ocr = DrawingOCR()
        assert ocr.extract_batch([]) == []

    def test_single_item_uses_sequential(self):
        """1~2건은 순차 처리"""
        ocr = DrawingOCR()
        with patch.object(ocr, 'extract') as mock_extract:
            mock_extract.return_value = OCRResult(
                full_text="test", text_blocks=[], part_numbers=[],
                dimensions=[], materials=[],
            )
            results = ocr.extract_batch(["file1.png"], workers=4)
            assert len(results) == 1
            mock_extract.assert_called_once_with("file1.png")

    def test_workers_zero_uses_sequential(self):
        """workers=0이면 순차 처리"""
        ocr = DrawingOCR()
        paths = ["a.png", "b.png", "c.png"]
        with patch.object(ocr, 'extract') as mock_extract:
            mock_extract.return_value = OCRResult(
                full_text="test", text_blocks=[], part_numbers=[],
                dimensions=[], materials=[],
            )
            results = ocr.extract_batch(paths, workers=0)
            assert len(results) == 3
            assert mock_extract.call_count == 3

    def test_result_order_preserved(self):
        """결과 순서가 입력 순서와 동일"""
        ocr = DrawingOCR()
        # 순차 모드로 테스트 (병렬은 프로세스 생성 필요)
        paths = [Path("a.png"), Path("b.png"), Path("c.png")]
        results_map = {
            "a.png": OCRResult(full_text="A", text_blocks=[], part_numbers=[], dimensions=[], materials=[]),
            "b.png": OCRResult(full_text="B", text_blocks=[], part_numbers=[], dimensions=[], materials=[]),
            "c.png": OCRResult(full_text="C", text_blocks=[], part_numbers=[], dimensions=[], materials=[]),
        }
        with patch.object(ocr, 'extract', side_effect=lambda p: results_map[Path(p).name]):
            results = ocr.extract_batch(paths, workers=0)

        assert [r.full_text for r in results] == ["A", "B", "C"]

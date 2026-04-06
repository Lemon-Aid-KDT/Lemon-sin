"""
증분 도면 등록 스크립트 테스트.
"""

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class _MockRecord:
    drawing_id: str = "test-001"
    file_path: str = "/tmp/test.png"
    file_name: str = "existing.png"
    ocr_text: str = ""
    part_numbers: list = field(default_factory=list)
    dimensions: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    category: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    yolo_confidence: float = 0.0
    yolo_needs_review: bool = False
    yolo_top_k: list = field(default_factory=list)
    detected_regions: list = field(default_factory=list)
    title_block_data: dict = field(default_factory=dict)
    parts_table_data: dict = field(default_factory=dict)
    detection_enhanced: bool = False
    dxf_path: str = ""
    similar_drawings: list = field(default_factory=list)


@pytest.fixture
def sample_dir(tmp_path):
    """테스트용 디렉토리에 파일 생성."""
    (tmp_path / "existing.png").write_bytes(b"\x89PNG" + b"\x00" * 100)
    (tmp_path / "new_file.png").write_bytes(b"\x89PNG" + b"\x00" * 100)
    (tmp_path / "another.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
    (tmp_path / "readme.txt").write_text("not an image")
    return tmp_path


class TestScanAndRegister:
    def test_skips_existing_files(self, sample_dir):
        """이미 등록된 파일은 건너뛴다."""
        mock_pipeline = MagicMock()
        existing_record = _MockRecord(file_name="existing.png")
        mock_pipeline.get_all_records.return_value = [existing_record]

        new_record = _MockRecord(drawing_id="new-001", file_name="new_file.png")
        mock_pipeline.register_drawing.return_value = new_record

        with patch("core.dependencies.get_pipeline", return_value=mock_pipeline):
            from scripts.incremental_register import scan_and_register
            count = scan_and_register(sample_dir)

        # existing.png은 스킵, new_file.png + another.jpg = 2건 등록
        assert count == 2
        assert mock_pipeline.register_drawing.call_count == 2

    def test_registers_new_files(self, sample_dir):
        """미등록 파일만 등록한다."""
        mock_pipeline = MagicMock()
        mock_pipeline.get_all_records.return_value = []  # 아무것도 등록 안됨
        mock_pipeline.register_drawing.return_value = _MockRecord()

        with patch("core.dependencies.get_pipeline", return_value=mock_pipeline):
            from scripts.incremental_register import scan_and_register
            count = scan_and_register(sample_dir)

        # 3건 (png 2 + jpg 1, txt는 무시)
        assert count == 3

    def test_ignores_non_image_files(self, sample_dir):
        """지원하지 않는 확장자는 무시한다."""
        mock_pipeline = MagicMock()
        mock_pipeline.get_all_records.return_value = []
        mock_pipeline.register_drawing.return_value = _MockRecord()

        with patch("core.dependencies.get_pipeline", return_value=mock_pipeline):
            from scripts.incremental_register import scan_and_register
            count = scan_and_register(sample_dir)

        # readme.txt는 포함되지 않음
        registered_files = [
            call.args[0].name if call.args else call.kwargs.get("image_path", Path()).name
            for call in mock_pipeline.register_drawing.call_args_list
        ]
        assert "readme.txt" not in registered_files

    def test_empty_directory(self, tmp_path):
        """빈 디렉토리는 0건 반환."""
        mock_pipeline = MagicMock()
        mock_pipeline.get_all_records.return_value = []

        with patch("core.dependencies.get_pipeline", return_value=mock_pipeline):
            from scripts.incremental_register import scan_and_register
            count = scan_and_register(tmp_path)

        assert count == 0

    def test_handles_registration_error(self, sample_dir):
        """등록 실패 시 에러 카운트만 증가하고 계속 진행."""
        mock_pipeline = MagicMock()
        mock_pipeline.get_all_records.return_value = []
        mock_pipeline.register_drawing.side_effect = RuntimeError("OCR failed")

        with patch("core.dependencies.get_pipeline", return_value=mock_pipeline):
            from scripts.incremental_register import scan_and_register
            count = scan_and_register(sample_dir)

        # 모두 실패 → 0건 성공
        assert count == 0

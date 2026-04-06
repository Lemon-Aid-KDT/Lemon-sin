"""
DXFRenderer 유닛 테스트

DXF -> PNG 렌더링, 메타데이터 추출, 유틸리티 검증.
"""

import pytest
from pathlib import Path

from core.dxf_renderer import DXFRenderer


# ─────────────────────────────────────────────
# DXF 판별
# ─────────────────────────────────────────────


class TestIsDXF:
    """is_dxf 확장자 판별 테스트"""

    def test_dxf_extension_lower(self):
        assert DXFRenderer.is_dxf(Path("drawing.dxf")) is True

    def test_dxf_extension_upper(self):
        assert DXFRenderer.is_dxf(Path("DRAWING.DXF")) is True

    def test_dxf_extension_mixed(self):
        assert DXFRenderer.is_dxf(Path("test.Dxf")) is True

    def test_png_is_not_dxf(self):
        assert DXFRenderer.is_dxf(Path("test.png")) is False

    def test_string_path(self):
        assert DXFRenderer.is_dxf("/tmp/test.dxf") is True

    def test_no_extension(self):
        assert DXFRenderer.is_dxf(Path("noext")) is False


# ─────────────────────────────────────────────
# 렌더링
# ─────────────────────────────────────────────


class TestRenderToPNG:
    """render_to_png 테스트"""

    def test_render_creates_png(self, sample_dxf, tmp_path):
        """DXF -> PNG 변환 후 파일 생성 확인"""
        renderer = DXFRenderer()
        output = tmp_path / "output.png"
        result = renderer.render_to_png(sample_dxf, output)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_render_output_is_valid_png(self, sample_dxf, tmp_path):
        """출력이 유효한 PNG인지 확인 (매직 바이트)"""
        renderer = DXFRenderer()
        output = tmp_path / "output.png"
        renderer.render_to_png(sample_dxf, output)

        with open(output, "rb") as f:
            header = f.read(8)
        # PNG 매직 바이트
        assert header[:4] == b"\x89PNG"

    def test_render_creates_parent_dirs(self, sample_dxf, tmp_path):
        """출력 디렉토리가 없으면 자동 생성"""
        renderer = DXFRenderer()
        output = tmp_path / "subdir" / "nested" / "output.png"
        renderer.render_to_png(sample_dxf, output)

        assert output.exists()

    def test_render_custom_dpi(self, sample_dxf, tmp_path):
        """DPI 설정이 반영되는지 확인 (파일 크기 비교)"""
        low = tmp_path / "low.png"
        high = tmp_path / "high.png"

        DXFRenderer(dpi=72).render_to_png(sample_dxf, low)
        DXFRenderer(dpi=300).render_to_png(sample_dxf, high)

        # 높은 DPI → 더 큰 파일
        assert high.stat().st_size > low.stat().st_size

    def test_render_invalid_dxf(self, tmp_path):
        """손상된 DXF → 예외 발생"""
        bad_dxf = tmp_path / "bad.dxf"
        bad_dxf.write_text("this is not a valid dxf file")

        renderer = DXFRenderer()
        output = tmp_path / "output.png"

        with pytest.raises(Exception):
            renderer.render_to_png(bad_dxf, output)


# ─────────────────────────────────────────────
# 메타데이터 추출
# ─────────────────────────────────────────────


class TestExtractMetadata:
    """extract_metadata 테스트"""

    def test_extract_metadata_layers(self, sample_dxf):
        """레이어 목록 추출"""
        renderer = DXFRenderer()
        meta = renderer.extract_metadata(sample_dxf)

        assert "layers" in meta
        assert isinstance(meta["layers"], list)
        # ezdxf.new()는 기본 "0" 레이어를 생성
        assert "0" in meta["layers"]

    def test_extract_metadata_entity_count(self, sample_dxf):
        """엔티티 수 확인 (LINE 2 + CIRCLE 1 = 3)"""
        renderer = DXFRenderer()
        meta = renderer.extract_metadata(sample_dxf)

        assert meta["entity_count"] == 3

    def test_extract_metadata_entity_types(self, sample_dxf):
        """엔티티 타입별 개수"""
        renderer = DXFRenderer()
        meta = renderer.extract_metadata(sample_dxf)

        assert meta["entity_types"].get("LINE") == 2
        assert meta["entity_types"].get("CIRCLE") == 1

    def test_extract_metadata_bounding_box(self, sample_dxf):
        """바운딩 박스 추출"""
        renderer = DXFRenderer()
        meta = renderer.extract_metadata(sample_dxf)

        bbox = meta["bounding_box"]
        # sample_dxf: lines (0,0)-(10,5), circle center (5,5) r=3
        # bbox should encompass all entities
        assert bbox is not None
        assert len(bbox) == 4
        # min_x <= 0, min_y <= 0 (line starts at 0,0)
        assert bbox[0] <= 0.0
        assert bbox[1] <= 0.0

    def test_extract_metadata_invalid_dxf(self, tmp_path):
        """손상된 DXF → 예외 발생"""
        bad_dxf = tmp_path / "bad.dxf"
        bad_dxf.write_text("not a dxf")

        renderer = DXFRenderer()
        with pytest.raises(Exception):
            renderer.extract_metadata(bad_dxf)

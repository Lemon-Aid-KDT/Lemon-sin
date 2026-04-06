"""
OCR 순수 함수 유닛 테스트

_extract_part_numbers(), _extract_dimensions(), _extract_materials()는
정규식 기반 순수 함수이므로 외부 의존성 없이 테스트 가능하다.
"""

import pytest
from core.ocr import DrawingOCR


class TestExtractPartNumbers:
    """부품번호 추출 테스트"""

    def test_standard_format(self):
        """표준 부품번호 형식 (AB-12345)"""
        result = DrawingOCR._extract_part_numbers("부품번호: AB-12345")
        assert "AB-12345" in result

    def test_long_numeric(self):
        """장수 숫자 부품번호 (12345678)"""
        result = DrawingOCR._extract_part_numbers("Part 12345678")
        assert "12345678" in result

    def test_mixed_alphanumeric(self):
        """알파벳+숫자 혼합 (A12-B3456)"""
        result = DrawingOCR._extract_part_numbers("코드: A12-B3456")
        assert any("A12" in pn for pn in result)

    def test_pn_prefix(self):
        """P/N 접두어"""
        result = DrawingOCR._extract_part_numbers("P/N: XY-9876")
        assert any("XY-9876" in pn for pn in result)

    def test_part_prefix(self):
        """PART 접두어"""
        result = DrawingOCR._extract_part_numbers("PART: GH-5432")
        assert any("GH-5432" in pn for pn in result)

    def test_multiple_part_numbers(self):
        """여러 부품번호 추출"""
        text = "AB-1234 CD-5678 부품 EF-9012"
        result = DrawingOCR._extract_part_numbers(text)
        assert len(result) >= 2

    def test_no_match(self):
        """부품번호 없는 텍스트"""
        result = DrawingOCR._extract_part_numbers("일반 텍스트입니다.")
        assert len(result) == 0

    def test_empty_text(self):
        """빈 문자열"""
        result = DrawingOCR._extract_part_numbers("")
        assert result == []

    def test_case_insensitive(self):
        """대소문자 무관하게 추출"""
        result = DrawingOCR._extract_part_numbers("p/n: ab-12345")
        assert len(result) >= 1

    def test_deduplication(self):
        """중복 제거"""
        text = "AB-1234 AB-1234 AB-1234"
        result = DrawingOCR._extract_part_numbers(text)
        assert len([pn for pn in result if "AB-1234" in pn]) == 1


class TestExtractDimensions:
    """치수 정보 추출 테스트"""

    def test_mm_unit(self):
        """밀리미터 단위"""
        result = DrawingOCR._extract_dimensions("길이 100mm")
        assert any("100mm" in d for d in result)

    def test_decimal_dimension(self):
        """소수점 포함 치수"""
        result = DrawingOCR._extract_dimensions("두께 25.4mm")
        assert any("25.4mm" in d for d in result)

    def test_diameter_symbol(self):
        """지름 기호 (Ø)"""
        result = DrawingOCR._extract_dimensions("Ø50")
        assert len(result) >= 1

    def test_tolerance(self):
        """공차 표기 (±)"""
        result = DrawingOCR._extract_dimensions("25.4±0.1")
        assert len(result) >= 1

    def test_radius(self):
        """반지름 표기 (R)"""
        result = DrawingOCR._extract_dimensions("R10")
        assert any("R10" in d for d in result)

    def test_cross_dimension(self):
        """가로x세로 치수"""
        result = DrawingOCR._extract_dimensions("100x50")
        assert len(result) >= 1

    def test_inch_unit(self):
        """인치 단위"""
        result = DrawingOCR._extract_dimensions("2.5inch")
        assert len(result) >= 1

    def test_no_dimensions(self):
        """치수 없는 텍스트"""
        result = DrawingOCR._extract_dimensions("도면 제목")
        assert len(result) == 0

    def test_empty_text(self):
        """빈 문자열"""
        result = DrawingOCR._extract_dimensions("")
        assert result == []

    def test_multiple_dimensions(self):
        """여러 치수 추출"""
        text = "길이 100mm, 폭 50mm, Ø30, R5"
        result = DrawingOCR._extract_dimensions(text)
        assert len(result) >= 3


class TestExtractMaterials:
    """재질 정보 추출 테스트"""

    def test_sus(self):
        """스테인리스 (SUS)"""
        result = DrawingOCR._extract_materials("재질: SUS304")
        assert any("SUS" in m for m in result)

    def test_steel(self):
        """스틸"""
        result = DrawingOCR._extract_materials("MATERIAL: STEEL")
        assert any("STEEL" in m.upper() for m in result)

    def test_aluminum(self):
        """알루미늄"""
        result = DrawingOCR._extract_materials("재질 ALUMINUM")
        assert any("ALUMINUM" in m.upper() for m in result)

    def test_korean_material(self):
        """한국어 재질명"""
        result = DrawingOCR._extract_materials("재질: 스테인리스")
        assert any("스테인리스" in m for m in result)

    def test_jis_material(self):
        """JIS 규격 재질 (S45C)"""
        result = DrawingOCR._extract_materials("재질: S45C")
        assert any("S45C" in m for m in result)

    def test_ss400(self):
        """SS400 일반구조용강"""
        result = DrawingOCR._extract_materials("SS400")
        assert any("SS400" in m for m in result)

    def test_a6061(self):
        """알루미늄 합금 A6061"""
        result = DrawingOCR._extract_materials("재질 A6061")
        assert any("A6061" in m for m in result)

    def test_no_materials(self):
        """재질 없는 텍스트"""
        result = DrawingOCR._extract_materials("도면 번호 12345")
        assert len(result) == 0

    def test_empty_text(self):
        """빈 문자열"""
        result = DrawingOCR._extract_materials("")
        assert result == []

    def test_multiple_materials(self):
        """여러 재질 추출"""
        text = "본체: SUS304, 샤프트: S45C, 부싱: BRASS"
        result = DrawingOCR._extract_materials(text)
        assert len(result) >= 3

    def test_case_insensitive(self):
        """대소문자 무관"""
        result = DrawingOCR._extract_materials("material: aluminum")
        assert len(result) >= 1


# ─────────────────────────────────────────────
# Phase 3: 영역 OCR 테스트
# ─────────────────────────────────────────────


class TestRegionOCRResult:
    """RegionOCRResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 초기화"""
        from core.ocr import RegionOCRResult
        r = RegionOCRResult()
        assert r.region_class == ""
        assert r.bbox == (0, 0, 0, 0)
        assert r.text == ""
        assert r.confidence == 0.0
        assert r.structured_data == {}

    def test_full_initialization(self):
        """전체 필드 초기화"""
        from core.ocr import RegionOCRResult
        r = RegionOCRResult(
            region_class="title_block",
            bbox=(100, 200, 500, 400),
            text="도번 A-1234",
            confidence=0.85,
            structured_data={"drawing_number": "A-1234"},
        )
        assert r.region_class == "title_block"
        assert r.structured_data["drawing_number"] == "A-1234"


class TestOCRResultRegionFields:
    """OCRResult에 추가된 영역 필드 테스트"""

    def test_default_regions_empty(self):
        """기존 OCRResult에 regions 기본값이 빈 리스트"""
        from core.ocr import OCRResult
        result = OCRResult(full_text="")
        assert result.regions == []
        assert result.detection_enhanced is False

    def test_ocr_result_backward_compatible(self):
        """기존 코드와 하위 호환"""
        from core.ocr import OCRResult
        result = OCRResult(
            full_text="test",
            part_numbers=["P001"],
            dimensions=["10mm"],
            materials=["SUS304"],
        )
        assert result.full_text == "test"
        assert result.regions == []
        assert result.detection_enhanced is False


class TestParseTitleBlock:
    """표제란 파싱 테스트"""

    def test_drawing_number_korean(self):
        """한국어 도면번호 추출"""
        text = "도면번호: A-1234-REV01\n재질: SUS304\n척도: 1:1"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("drawing_number") == "A-1234-REV01"

    def test_drawing_number_english(self):
        """영문 DWG NO 추출"""
        text = "DWG NO. AB-5678\nMATERIAL: S45C\nSCALE: 2:1"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("drawing_number") == "AB-5678"

    def test_material_extraction(self):
        """재질 추출"""
        text = "재질: SUS304\n도번: X-001"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("material") == "SUS304"

    def test_material_english(self):
        """영문 MATERIAL 추출"""
        text = "MATERIAL: ALUMINUM\nDWG NO: Y-002"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("material") == "ALUMINUM"

    def test_scale_extraction(self):
        """척도 추출"""
        text = "척도: 1:2\n도면번호: Z-003"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("scale") == "1:2"

    def test_scale_english(self):
        """영문 SCALE 추출"""
        text = "SCALE: 5:1\nDWG NO: W-004"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("scale") == "5:1"

    def test_date_extraction(self):
        """날짜 추출"""
        text = "일자: 2024-01-15\n도번: D-001"
        result = DrawingOCR._parse_title_block(text)
        assert result.get("date") == "2024-01-15"

    def test_empty_text(self):
        """빈 텍스트 → 빈 dict"""
        result = DrawingOCR._parse_title_block("")
        assert result == {}

    def test_no_matching_fields(self):
        """매칭 필드 없는 텍스트 → 빈 dict"""
        result = DrawingOCR._parse_title_block("아무 관련 없는 텍스트입니다.")
        assert isinstance(result, dict)


class TestParsePartsTable:
    """부품표 파싱 테스트"""

    def test_bom_rows_parsing(self):
        """BOM 행 파싱"""
        text = "1 축 2 S45C\n2 기어 1 SUS304\n3 부싱 4 BRASS"
        result = DrawingOCR._parse_parts_table(text)
        assert "items" in result
        assert len(result["items"]) >= 1

    def test_empty_text(self):
        """빈 텍스트"""
        result = DrawingOCR._parse_parts_table("")
        assert "items" in result
        assert len(result["items"]) == 0


class TestParseDimensionArea:
    """치수 영역 파싱 테스트"""

    def test_dimensions_extraction(self):
        """치수 추출"""
        text = "25.4mm 50mm Ø30 R10 M5"
        result = DrawingOCR._parse_dimension_area(text)
        assert "dimensions" in result
        assert len(result["dimensions"]) >= 1

    def test_tolerances_extraction(self):
        """공차 추출"""
        text = "25.0±0.1 50.0+0.05/-0.02"
        result = DrawingOCR._parse_dimension_area(text)
        assert "tolerances" in result

    def test_empty_text(self):
        """빈 텍스트"""
        result = DrawingOCR._parse_dimension_area("")
        assert result.get("dimensions", []) == []

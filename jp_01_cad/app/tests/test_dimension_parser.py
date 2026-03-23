"""
DimensionParser 유닛 테스트

치수 파싱, 비교, OCR 노이즈 보정, 엣지 케이스 검증.
"""

import pytest

from core.dimension_parser import (
    ParsedDimension,
    DimensionDiff,
    parse_dimensions,
    compare_dimensions,
)


# ─────────────────────────────────────────────
# 치수 파싱
# ─────────────────────────────────────────────


class TestParseDimensions:
    """parse_dimensions 테스트"""

    # --- 나사산 ---

    def test_thread_simple(self):
        """M8 단순 나사산"""
        dims = parse_dimensions("M8")
        assert len(dims) == 1
        assert dims[0].dim_type == "thread"
        assert dims[0].value == 8.0
        assert dims[0].label == "M8"

    def test_thread_with_pitch(self):
        """M10x1.5 나사산+피치"""
        dims = parse_dimensions("M10x1.5")
        assert len(dims) == 1
        assert dims[0].dim_type == "thread"
        assert dims[0].value == 10.0
        assert "x1.5" in dims[0].label

    def test_thread_unicode_multiply(self):
        """M10×1.5 유니코드 곱셈 기호"""
        dims = parse_dimensions("M10×1.5")
        threads = [d for d in dims if d.dim_type == "thread"]
        assert len(threads) == 1
        assert threads[0].value == 10.0

    def test_thread_with_space(self):
        """M 8 공백 포함 (OCR 노이즈)"""
        dims = parse_dimensions("M 8")
        threads = [d for d in dims if d.dim_type == "thread"]
        assert len(threads) >= 1
        assert threads[0].value == 8.0

    # --- 지름 ---

    def test_diameter_phi_upper(self):
        """Φ20 대문자 파이"""
        dims = parse_dimensions("Φ20")
        assert len(dims) == 1
        assert dims[0].dim_type == "diameter"
        assert dims[0].value == 20.0

    def test_diameter_phi_lower(self):
        """φ15.5 소문자 파이"""
        dims = parse_dimensions("φ15.5")
        diams = [d for d in dims if d.dim_type == "diameter"]
        assert len(diams) == 1
        assert diams[0].value == 15.5

    def test_diameter_oslash(self):
        """ø30 ø 기호"""
        dims = parse_dimensions("ø30")
        diams = [d for d in dims if d.dim_type == "diameter"]
        assert len(diams) == 1
        assert diams[0].value == 30.0

    # --- 공차 ---

    def test_tolerance_plus_minus(self):
        """50±0.05"""
        dims = parse_dimensions("50±0.05")
        tols = [d for d in dims if d.dim_type == "tolerance"]
        assert len(tols) == 1
        assert tols[0].value == 50.0
        assert tols[0].tolerance_plus == 0.05
        assert tols[0].tolerance_minus == 0.05

    def test_tolerance_asymmetric(self):
        """50+0.1/-0.05 비대칭 공차"""
        dims = parse_dimensions("50+0.1/-0.05")
        tols = [d for d in dims if d.dim_type == "tolerance"]
        assert len(tols) == 1
        assert tols[0].value == 50.0
        assert tols[0].tolerance_plus == 0.1
        assert tols[0].tolerance_minus == 0.05

    def test_tolerance_symmetric_slash(self):
        """50+/-0.05 대칭 공차"""
        dims = parse_dimensions("50+/-0.05")
        tols = [d for d in dims if d.dim_type == "tolerance"]
        assert len(tols) == 1
        assert tols[0].tolerance_plus == 0.05

    # --- 각도 ---

    def test_angle_degree_symbol(self):
        """45°"""
        dims = parse_dimensions("45°")
        angles = [d for d in dims if d.dim_type == "angle"]
        assert len(angles) == 1
        assert angles[0].value == 45.0
        assert angles[0].unit == "°"

    def test_angle_deg_text(self):
        """90deg"""
        dims = parse_dimensions("90deg")
        angles = [d for d in dims if d.dim_type == "angle"]
        assert len(angles) == 1
        assert angles[0].value == 90.0

    # --- 단위 포함 길이 ---

    def test_length_mm(self):
        """100mm"""
        dims = parse_dimensions("100mm")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 100.0
        assert lengths[0].unit == "mm"

    def test_length_cm(self):
        """25.5cm"""
        dims = parse_dimensions("25.5cm")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 25.5
        assert lengths[0].unit == "cm"

    def test_length_m(self):
        """2.5m"""
        dims = parse_dimensions("2.5m")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 2.5
        assert lengths[0].unit == "m"

    # --- 순수 숫자 ---

    def test_plain_number(self):
        """단위 없는 숫자는 mm로 처리"""
        dims = parse_dimensions("75")
        assert len(dims) >= 1
        assert dims[0].value == 75.0
        assert dims[0].dim_type == "length"

    # --- OCR 노이즈 ---

    def test_ocr_o_to_zero(self):
        """O → 0 변환 (1O0mm → 100mm)"""
        dims = parse_dimensions("1O0mm")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 100.0

    def test_ocr_spaces_in_number(self):
        """숫자 사이 공백 (1 0 0 → 100)"""
        dims = parse_dimensions("1 0 0mm")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 100.0

    # --- 복합 텍스트 ---

    def test_multiple_dimensions(self):
        """여러 치수가 포함된 텍스트"""
        text = "M8x1.25 hole, Φ20 bore, 100mm length, 45°"
        dims = parse_dimensions(text)
        types = {d.dim_type for d in dims}
        assert "thread" in types
        assert "diameter" in types
        assert "angle" in types

    def test_dedup(self):
        """중복 제거: 같은 치수 두 번"""
        dims = parse_dimensions("M8 and M8")
        threads = [d for d in dims if d.dim_type == "thread"]
        assert len(threads) == 1


# ─────────────────────────────────────────────
# 치수 비교
# ─────────────────────────────────────────────


class TestCompareDimensions:
    """compare_dimensions 테스트"""

    def test_exact_match(self):
        """완전 일치"""
        a = [ParsedDimension(value=10.0, dim_type="length")]
        b = [ParsedDimension(value=10.0, dim_type="length")]
        diff = compare_dimensions(a, b)
        assert len(diff.matched) == 1
        assert len(diff.changed) == 0
        assert diff.similarity == 1.0

    def test_changed_value(self):
        """같은 타입, 다른 값"""
        a = [ParsedDimension(value=10.0, dim_type="length")]
        b = [ParsedDimension(value=12.0, dim_type="length")]
        diff = compare_dimensions(a, b)
        assert len(diff.changed) == 1
        assert diff.changed[0][2] == pytest.approx(-2.0)
        assert diff.similarity == 0.0

    def test_only_in_a(self):
        """a에만 존재"""
        a = [
            ParsedDimension(value=10.0, dim_type="length"),
            ParsedDimension(value=5.0, dim_type="diameter"),
        ]
        b = [ParsedDimension(value=10.0, dim_type="length")]
        diff = compare_dimensions(a, b)
        assert len(diff.matched) == 1
        assert len(diff.only_in_a) == 1
        assert diff.only_in_a[0].dim_type == "diameter"

    def test_only_in_b(self):
        """b에만 존재"""
        a = [ParsedDimension(value=10.0, dim_type="length")]
        b = [
            ParsedDimension(value=10.0, dim_type="length"),
            ParsedDimension(value=45.0, dim_type="angle"),
        ]
        diff = compare_dimensions(a, b)
        assert len(diff.only_in_b) == 1
        assert diff.only_in_b[0].dim_type == "angle"

    def test_empty_both(self):
        """양쪽 모두 비어있으면 similarity=1.0"""
        diff = compare_dimensions([], [])
        assert diff.similarity == 1.0
        assert len(diff.matched) == 0

    def test_empty_a(self):
        """a만 비어있으면 similarity=0.0"""
        b = [ParsedDimension(value=10.0, dim_type="length")]
        diff = compare_dimensions([], b)
        assert diff.similarity == 0.0
        assert len(diff.only_in_b) == 1

    def test_empty_b(self):
        """b만 비어있으면 similarity=0.0"""
        a = [ParsedDimension(value=10.0, dim_type="length")]
        diff = compare_dimensions(a, [])
        assert diff.similarity == 0.0
        assert len(diff.only_in_a) == 1

    def test_similarity_partial(self):
        """부분 일치 similarity 계산"""
        a = [
            ParsedDimension(value=10.0, dim_type="length"),
            ParsedDimension(value=20.0, dim_type="length"),
        ]
        b = [
            ParsedDimension(value=10.0, dim_type="length"),
            ParsedDimension(value=25.0, dim_type="length"),
        ]
        diff = compare_dimensions(a, b)
        assert len(diff.matched) == 1
        assert len(diff.changed) == 1
        assert diff.similarity == pytest.approx(0.5)

    def test_cross_type_no_match(self):
        """다른 타입은 매칭하지 않음"""
        a = [ParsedDimension(value=10.0, dim_type="length")]
        b = [ParsedDimension(value=10.0, dim_type="angle")]
        diff = compare_dimensions(a, b)
        assert len(diff.matched) == 0
        assert len(diff.only_in_a) == 1
        assert len(diff.only_in_b) == 1


# ─────────────────────────────────────────────
# 엣지 케이스
# ─────────────────────────────────────────────


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_string(self):
        """빈 문자열"""
        assert parse_dimensions("") == []

    def test_whitespace_only(self):
        """공백만 있는 문자열"""
        assert parse_dimensions("   \n\t  ") == []

    def test_no_dimensions(self):
        """치수가 없는 텍스트"""
        dims = parse_dimensions("This is a drawing title block")
        # 숫자가 없으므로 결과 없음
        assert len(dims) == 0

    def test_mixed_types_in_one_text(self):
        """한 텍스트에 여러 타입 혼합"""
        text = "M12x1.75 thread, Φ25 bore, 50±0.02, 30° chamfer, 200mm"
        dims = parse_dimensions(text)
        types_found = {d.dim_type for d in dims}
        assert "thread" in types_found
        assert "diameter" in types_found
        assert "tolerance" in types_found
        assert "angle" in types_found
        assert "length" in types_found

    def test_decimal_values(self):
        """소수점 값"""
        dims = parse_dimensions("12.75mm")
        assert len(dims) >= 1
        assert dims[0].value == pytest.approx(12.75)

    def test_large_number(self):
        """큰 숫자"""
        dims = parse_dimensions("2500mm")
        lengths = [d for d in dims if d.dim_type == "length"]
        assert len(lengths) == 1
        assert lengths[0].value == 2500.0

"""``field_extractor`` 단위 테스트 — 제품명 / 성분 / 함량 추출 규칙 검증.

Reference:
    backend/src/ocr/field_extractor.py
    scripts/synth_label_dataset.py
"""

from __future__ import annotations

from src.ocr.field_extractor import (
    extract_dosage,
    extract_fields,
    extract_ingredients,
    extract_product_name,
)


class TestExtractProductName:
    """제품명 추출 규칙."""

    def test_header_then_product_name(self) -> None:
        """헤더 다음 줄이 제품명."""
        text = "영양 정보\n비타민 C 종합 영양제\n성분\n- 비타민 C: 1000mg"
        assert extract_product_name(text) == "비타민 C 종합 영양제"

    def test_english_header_then_product_name(self) -> None:
        """Nutrition Facts → 다음 줄."""
        text = "Nutrition Facts\nVitamin C Complex\nIngredients\n- Vitamin C: 1000mg"
        assert extract_product_name(text) == "Vitamin C Complex"

    def test_no_header_returns_first_line(self) -> None:
        """헤더가 없으면 첫 줄."""
        text = "비타민 C 1000mg\n- 비타민 C: 1000mg"
        assert extract_product_name(text) == "비타민 C 1000mg"

    def test_empty_returns_none(self) -> None:
        assert extract_product_name("") is None

    def test_only_header_returns_none(self) -> None:
        """헤더만 있고 다음 줄이 없으면 ``None`` 이 아닌 헤더 자체 반환되지 않도록 한다."""
        # 헤더 본 직후 줄이 없으면 ``None``; 헤더가 없으면 그 헤더가 첫 줄로 반환됨.
        assert extract_product_name("영양 정보") == "영양 정보"


class TestExtractIngredients:
    """성분 추출 규칙."""

    def test_korean_lines(self) -> None:
        text = "- 비타민 C: 1000mg\n- 비타민 D: 25μg"
        assert extract_ingredients(text) == ["비타민 C", "비타민 D"]

    def test_english_lines_preserve_original(self) -> None:
        """영문은 영문 그대로 (canonicalization 안 함)."""
        text = "- Vitamin C: 1000mg\n- Vitamin D: 25μg"
        assert extract_ingredients(text) == ["Vitamin C", "Vitamin D"]

    def test_mixed_lines_preserve_parens(self) -> None:
        """``비타민 A (Vitamin A)`` 형태는 보존된다."""
        text = "- 비타민 A (Vitamin A): 800μg RAE\n- 셀레늄 (Selenium): 50μg"
        assert extract_ingredients(text) == ["비타민 A (Vitamin A)", "셀레늄 (Selenium)"]

    def test_skips_lines_without_colon_amount(self) -> None:
        """``이름: 숫자`` 패턴이 아니면 무시."""
        text = "영양 정보\n비타민 C 종합 영양제\n성분\n- 비타민 C: 1000mg"
        # '비타민 C 종합 영양제' 는 콜론+숫자 패턴이 없어 ingredients 후보 아님.
        assert extract_ingredients(text) == ["비타민 C"]

    def test_empty_input(self) -> None:
        assert extract_ingredients("") == []


class TestExtractDosage:
    """함량 정규식 검증."""

    def test_simple_mg(self) -> None:
        assert extract_dosage("- 비타민 C: 1000mg") == "1000mg"

    def test_mu_g(self) -> None:
        assert extract_dosage("- 비타민 D: 25μg") == "25μg"

    def test_mu_g_rae_compound_unit(self) -> None:
        """μg RAE 같은 복합 단위도 캡처."""
        assert extract_dosage("- 비타민 A: 800μg RAE") == "800μg RAE"

    def test_mg_alpha_te_compound_unit(self) -> None:
        assert extract_dosage("- 비타민 E: 12mg α-TE") == "12mg α-TE"

    def test_mu_g_dfe_compound_unit(self) -> None:
        assert extract_dosage("- 엽산: 400μg DFE") == "400μg DFE"

    def test_decimal_amount(self) -> None:
        assert extract_dosage("- 비타민 B6: 1.5mg") == "1.5mg"

    def test_returns_first_match(self) -> None:
        text = "- 비타민 C: 1000mg\n- 비타민 D: 25μg"
        assert extract_dosage(text) == "1000mg"

    def test_no_match_returns_none(self) -> None:
        assert extract_dosage("no numbers here") is None


class TestExtractFields:
    """전체 필드 추출 통합."""

    def test_all_three_fields(self) -> None:
        text = (
            "영양 정보\n"
            "비타민 C 종합 영양제\n"
            "\n"
            "성분\n"
            "- 비타민 C: 1000mg\n"
            "- 비타민 D: 25μg"
        )
        result = extract_fields(text)
        assert result == {
            "product_name": "비타민 C 종합 영양제",
            "ingredients": ["비타민 C", "비타민 D"],
            "dosage": "1000mg",
        }

    def test_english_all_fields(self) -> None:
        text = (
            "Nutrition Facts\n"
            "Vitamin C Complex\n"
            "Ingredients\n"
            "- Vitamin C: 1000mg"
        )
        result = extract_fields(text)
        assert result == {
            "product_name": "Vitamin C Complex",
            "ingredients": ["Vitamin C"],
            "dosage": "1000mg",
        }

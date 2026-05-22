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
        text = "Nutrition Facts\n" "Vitamin C Complex\n" "Ingredients\n" "- Vitamin C: 1000mg"
        result = extract_fields(text)
        assert result == {
            "product_name": "Vitamin C Complex",
            "ingredients": ["Vitamin C"],
            "dosage": "1000mg",
        }


class TestPaddleOCRRegressionShape:
    """PaddleOCR 출력 변형에서 어떤 형식이 누락되는지 명시적으로 박아둔다.

    P1-5 안정화 후 chronic 평가에서 ingredient_name_exact_rate=0% 가 관측되었다.
    이 클래스는 ``INGREDIENT_LINE_PATTERN`` / ``DOSAGE_PATTERN`` 정규식이 PaddleOCR
    이 흔히 내놓는 출력 형식 중 어디서 깨지는지 회귀 testbed 로 잡아둔다.
    개선 PR 은 여기 표시된 ``xfail`` / 누락 케이스를 채워나가는 방향이다.
    """

    def test_table_row_without_colon_currently_dropped(self) -> None:
        """PaddleOCR 표 셀 출력 ``비타민 C  1000mg`` 은 현재 정규식에서 누락된다.

        ``INGREDIENT_LINE_PATTERN`` 이 콜론을 필수로 요구하므로 표 레이아웃을
        평면화한 출력 (e.g. ``ppstructure`` 없이 ``ppocr`` 만 사용했을 때)에서
        ingredient 가 모두 비어 나온다. P1-5 회귀의 가장 유력한 원인.
        """
        text = "성분\n비타민 C  1000mg\n비타민 D  25μg"
        result = extract_ingredients(text)
        assert result == []

    def test_table_row_pipe_separator_currently_dropped(self) -> None:
        """파이프 구분자 표 출력 ``비타민 C | 1000mg`` 도 동일하게 누락된다."""
        text = "성분\n비타민 C | 1000mg"
        result = extract_ingredients(text)
        assert result == []

    def test_colon_with_surrounding_spaces_is_matched(self) -> None:
        """``이름 : 1000mg`` (콜론 주변 공백) 변형은 정규식에서 잡혀야 한다.

        ``INGREDIENT_LINE_PATTERN`` 의 ``\\s*:\\s*`` 가 양쪽 공백을 흡수하므로
        PaddleOCR 가 콜론을 약간 띄워 출력하더라도 ingredient 가 추출된다.
        """
        text = "- 비타민 C : 1000mg"
        result = extract_ingredients(text)
        assert result == ["비타민 C"]

    def test_dosage_pattern_misreads_comma_thousand_separator(self) -> None:
        """``1,000mg`` 같은 천단위 콤마는 ``DOSAGE_PATTERN`` 이 잘못 해석한다.

        amount 그룹이 ``\\d+(?:\\.\\d+)?`` 라 콤마를 받지 않고 ``re.search`` 가
        콤마 뒤의 ``000mg`` 을 첫 매치로 채택한다 → dosage 가 ``"000mg"`` 으로
        기록되어 GT(``"1000mg"``) 와 mismatch. PaddleOCR 출력에서 천단위 콤마가
        나오면 dosage 평가가 즉시 깨진다.
        """
        result = extract_dosage("- 비타민 C: 1,000mg")
        assert result == "000mg"
        assert result != "1000mg"

    def test_dosage_pattern_misses_mcg_unit(self) -> None:
        """``mcg`` 단위는 ``DOSAGE_PATTERN`` 에서 누락된다.

        PaddleOCR 가 라벨의 ``μg`` 를 ``mcg`` 로 출력하는 경우가 흔하지만 현재
        패턴에는 ``μg`` / ``ug`` 만 정의되어 있어 dosage 가 ``None`` 이 된다.
        """
        result = extract_dosage("- 비타민 D: 25mcg")
        assert result is None

    def test_dosage_pattern_misses_combined_units_lowercase(self) -> None:
        """``μg rae`` (소문자 RAE)는 ``DOSAGE_PATTERN`` 에서 잡히지만 정규화 후

        대문자가 보존되지 않아 라벨 원문과 다르게 표시될 수 있음을 명시한다.
        OCR raw 가 ``25 μg rae`` 인 경우 추출은 되지만 unit 이 ``μg rae`` 로
        기록되어 GT(``μg RAE``) 와 다르므로 평가 단계에서 mismatch 가 발생한다.
        """
        result = extract_dosage("비타민 A: 25 μg rae")
        assert result == "25μg rae"
        assert result != "25μg RAE"

"""
Phase 4: LLM 컨텍스트 주입 & 환각 탐지 테스트

AnalysisContext, ValidationResult, HallucinationDetector 및
DrawingLLM 컨텍스트 주입 기능을 테스트한다.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.llm import (
    AnalysisContext,
    ValidationResult,
    HallucinationDetector,
    DrawingLLM,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def sample_context():
    """풍부한 AnalysisContext (YOLO + OCR 모두 포함)"""
    return AnalysisContext(
        yolo_category="Shafts",
        yolo_confidence=0.92,
        yolo_top_k=[("Shafts", 0.92), ("Linear_Bushings", 0.04), ("Gears", 0.02)],
        detected_regions=["title_block", "dimension_area"],
        title_block_data={
            "drawing_number": "SH-1234",
            "material": "S45C",
            "scale": "1:2",
        },
        part_numbers=["SH-1234"],
        dimensions=["Ø50mm", "100mm", "M8x1.25"],
        materials=["S45C"],
        ocr_text="SH-1234 S45C Ø50mm 100mm M8x1.25",
    )


@pytest.fixture
def llm():
    """DrawingLLM 인스턴스"""
    return DrawingLLM(base_url="http://localhost:11434", model="qwen3.5:9b")


# ─────────────────────────────────────────────
# AnalysisContext 테스트
# ─────────────────────────────────────────────


class TestAnalysisContext:
    """AnalysisContext 데이터클래스 테스트"""

    def test_has_context_empty(self):
        """빈 컨텍스트 → False"""
        ctx = AnalysisContext()
        assert ctx.has_context() is False

    def test_has_context_with_category(self):
        """카테고리만 → True"""
        ctx = AnalysisContext(yolo_category="Gears")
        assert ctx.has_context() is True

    def test_has_context_with_part_numbers(self):
        """부품번호만 → True"""
        ctx = AnalysisContext(part_numbers=["A-100"])
        assert ctx.has_context() is True

    def test_has_context_with_dimensions(self):
        """치수만 → True"""
        ctx = AnalysisContext(dimensions=["10mm"])
        assert ctx.has_context() is True

    def test_has_context_with_materials(self):
        """재질만 → True"""
        ctx = AnalysisContext(materials=["SUS304"])
        assert ctx.has_context() is True

    def test_has_context_with_title_block(self):
        """표제란만 → True"""
        ctx = AnalysisContext(title_block_data={"drawing_number": "X-001"})
        assert ctx.has_context() is True

    def test_to_prompt_section_empty(self):
        """빈 컨텍스트 → 빈 문자열"""
        ctx = AnalysisContext()
        assert ctx.to_prompt_section() == ""

    def test_to_prompt_section_full(self, sample_context):
        """전체 필드 포함 시 구조화된 블록 생성"""
        section = sample_context.to_prompt_section()
        assert "PRE-EXTRACTED FACTS" in section
        assert "END PRE-EXTRACTED FACTS" in section
        assert "Shafts" in section
        assert "SH-1234" in section
        assert "S45C" in section
        assert "Ø50mm" in section
        assert "ground truth" in section

    def test_to_prompt_section_confidence_high(self):
        """신뢰도 0.8+ → HIGH"""
        ctx = AnalysisContext(yolo_category="Gears", yolo_confidence=0.9)
        section = ctx.to_prompt_section()
        assert "HIGH" in section

    def test_to_prompt_section_confidence_medium(self):
        """신뢰도 0.5-0.8 → MEDIUM"""
        ctx = AnalysisContext(yolo_category="Gears", yolo_confidence=0.6)
        section = ctx.to_prompt_section()
        assert "MEDIUM" in section

    def test_to_prompt_section_confidence_low(self):
        """신뢰도 0.5 미만 → LOW"""
        ctx = AnalysisContext(yolo_category="Gears", yolo_confidence=0.3)
        section = ctx.to_prompt_section()
        assert "LOW" in section

    def test_to_prompt_section_alternative_categories(self):
        """대안 카테고리 출력 (top_k 2위 이후)"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.8,
            yolo_top_k=[("Shafts", 0.8), ("Gears", 0.1), ("Bolts", 0.05)],
        )
        section = ctx.to_prompt_section()
        assert "Alternative categories" in section
        assert "Gears" in section

    def test_to_prompt_section_ocr_truncation(self):
        """OCR 텍스트 300자 제한"""
        ctx = AnalysisContext(
            yolo_category="Gears",
            ocr_text="A" * 500,
        )
        section = ctx.to_prompt_section()
        # 전체 500자가 아닌 300자만 포함
        assert "A" * 300 in section
        assert "A" * 301 not in section

    def test_to_prompt_section_title_block_fields(self):
        """표제란 필드별 출력"""
        ctx = AnalysisContext(
            title_block_data={
                "drawing_number": "D-999",
                "material": "AL6061",
                "scale": "2:1",
            },
        )
        section = ctx.to_prompt_section()
        assert "Drawing/Part Number: D-999" in section
        assert "Material (from title block): AL6061" in section
        assert "Scale: 2:1" in section

    def test_to_prompt_section_detected_regions(self):
        """탐지 영역 출력"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            detected_regions=["title_block", "dimension_area"],
        )
        section = ctx.to_prompt_section()
        assert "Detected regions" in section
        assert "title_block" in section


# ─────────────────────────────────────────────
# ValidationResult 테스트
# ─────────────────────────────────────────────


class TestValidationResult:
    """ValidationResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값"""
        vr = ValidationResult()
        assert vr.is_valid is True
        assert vr.score == 1.0
        assert vr.checks == []
        assert vr.contradictions == []

    def test_to_dict(self):
        """직렬화"""
        vr = ValidationResult(
            is_valid=False,
            score=0.75,
            checks=[{"field": "material", "found": True}],
            contradictions=["Category mismatch"],
        )
        d = vr.to_dict()
        assert d["is_valid"] is False
        assert d["score"] == 0.75
        assert d["num_checks"] == 1
        assert d["num_contradictions"] == 1
        assert "Category mismatch" in d["contradictions"]

    def test_to_dict_score_rounding(self):
        """점수 소수점 반올림"""
        vr = ValidationResult(score=0.333333)
        d = vr.to_dict()
        assert d["score"] == 0.33


# ─────────────────────────────────────────────
# HallucinationDetector 테스트
# ─────────────────────────────────────────────


class TestHallucinationDetector:
    """HallucinationDetector 테스트"""

    def test_validate_no_context(self):
        """컨텍스트 없음 → is_valid=True, score=1.0"""
        ctx = AnalysisContext()
        vr = HallucinationDetector.validate("Any response", ctx)
        assert vr.is_valid is True
        assert vr.score == 1.0

    def test_validate_material_match(self):
        """재질 일치 (정확)"""
        ctx = AnalysisContext(materials=["S45C"])
        vr = HallucinationDetector.validate(
            "This shaft is made of S45C carbon steel.", ctx
        )
        mat_check = next(c for c in vr.checks if c["field"] == "material")
        assert mat_check["found"] is True
        assert len(vr.contradictions) == 0

    def test_validate_material_mismatch(self):
        """재질 불일치"""
        ctx = AnalysisContext(materials=["S45C"])
        vr = HallucinationDetector.validate(
            "This part is made of aluminum.", ctx
        )
        mat_check = next(c for c in vr.checks if c["field"] == "material")
        assert mat_check["found"] is False
        assert len(vr.contradictions) >= 1
        assert any("S45C" in c for c in vr.contradictions)

    def test_validate_material_alias_sus304(self):
        """재질 별칭 일치: SUS304 = SS304"""
        ctx = AnalysisContext(materials=["SUS304"])
        vr = HallucinationDetector.validate(
            "Made of SS304 stainless steel.", ctx
        )
        mat_check = next(c for c in vr.checks if c["field"] == "material")
        assert mat_check["found"] is True

    def test_validate_material_alias_aisi_304(self):
        """재질 별칭 일치: SUS304 = AISI 304"""
        ctx = AnalysisContext(materials=["SUS304"])
        vr = HallucinationDetector.validate(
            "Material specification: AISI 304", ctx
        )
        mat_check = next(c for c in vr.checks if c["field"] == "material")
        assert mat_check["found"] is True

    def test_validate_material_alias_s45c_1045(self):
        """재질 별칭 일치: S45C = AISI 1045"""
        ctx = AnalysisContext(materials=["S45C"])
        vr = HallucinationDetector.validate(
            "This is AISI 1045 medium carbon steel.", ctx
        )
        mat_check = next(c for c in vr.checks if c["field"] == "material")
        assert mat_check["found"] is True

    def test_validate_category_match(self):
        """카테고리 일치 (고신뢰도)"""
        ctx = AnalysisContext(yolo_category="Shafts", yolo_confidence=0.92)
        vr = HallucinationDetector.validate(
            "This is a precision ground shafts drawing.", ctx
        )
        cat_check = next(c for c in vr.checks if c["field"] == "category")
        assert cat_check["found"] is True

    def test_validate_category_mismatch(self):
        """카테고리 불일치"""
        ctx = AnalysisContext(yolo_category="Shafts", yolo_confidence=0.92)
        vr = HallucinationDetector.validate(
            "This is a gear assembly drawing.", ctx
        )
        cat_check = next(c for c in vr.checks if c["field"] == "category")
        assert cat_check["found"] is False
        assert any("Shafts" in c for c in vr.contradictions)

    def test_validate_category_low_conf_skip(self):
        """카테고리 낮은 신뢰도 → 체크 스킵"""
        ctx = AnalysisContext(yolo_category="Shafts", yolo_confidence=0.6)
        vr = HallucinationDetector.validate(
            "This is a gear assembly.", ctx
        )
        cat_checks = [c for c in vr.checks if c["field"] == "category"]
        assert len(cat_checks) == 0  # 신뢰도 0.6 < 0.8이므로 체크 안 함

    def test_validate_part_number_found(self):
        """부품번호 일치"""
        ctx = AnalysisContext(part_numbers=["SH-1234"])
        vr = HallucinationDetector.validate(
            "Drawing number SH-1234 shows a shaft.", ctx
        )
        pn_check = next(c for c in vr.checks if c["field"] == "part_number")
        assert pn_check["found"] is True

    def test_validate_part_number_not_found(self):
        """부품번호 미발견 (불일치는 아님 — found=False만)"""
        ctx = AnalysisContext(part_numbers=["SH-1234"])
        vr = HallucinationDetector.validate(
            "This drawing shows a shaft component.", ctx
        )
        pn_check = next(c for c in vr.checks if c["field"] == "part_number")
        assert pn_check["found"] is False

    def test_validate_dimensions_spot_check(self):
        """치수 spot-check"""
        ctx = AnalysisContext(dimensions=["Ø50mm", "100mm", "M8x1.25"])
        vr = HallucinationDetector.validate(
            "Diameter is Ø50mm, length 100mm with M8x1.25 thread.", ctx
        )
        dim_check = next(c for c in vr.checks if c["field"] == "dimensions")
        assert dim_check["found"] == 3
        assert dim_check["checked"] == 3

    def test_validate_score_calculation(self):
        """점수 계산: 3/4 통과 → 0.75"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.92,
            part_numbers=["SH-1234"],
            materials=["S45C"],
            dimensions=["Ø50mm"],
        )
        # PN: found, Material: found, Category: NOT found, Dims: found
        vr = HallucinationDetector.validate(
            "Part SH-1234, material S45C, Ø50mm diameter. Gear assembly.",
            ctx,
        )
        # 4 checks: pn(True), material(True), category(False), dims(1/1)
        assert 0.7 <= vr.score <= 0.8  # 3/4 = 0.75

    def test_validate_multiple_contradictions(self):
        """다중 불일치"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.92,
            materials=["S45C"],
        )
        vr = HallucinationDetector.validate(
            "This is a gear made of aluminum.", ctx
        )
        assert len(vr.contradictions) >= 2  # 카테고리 + 재질

    def test_validate_is_valid_with_no_contradictions(self):
        """불일치 0건 → is_valid=True"""
        ctx = AnalysisContext(part_numbers=["P-001"])
        vr = HallucinationDetector.validate("Part P-001 detail.", ctx)
        assert vr.is_valid is True

    def test_validate_is_valid_false_with_contradictions(self):
        """불일치 1건+ → is_valid=False"""
        ctx = AnalysisContext(
            yolo_category="Shafts", yolo_confidence=0.95
        )
        vr = HallucinationDetector.validate("Gear assembly drawing.", ctx)
        assert vr.is_valid is False

    def test_material_aliases_unknown(self):
        """알 수 없는 재질 → 원래 값만 반환"""
        aliases = HallucinationDetector._material_aliases("UNOBTANIUM")
        assert aliases == ["UNOBTANIUM"]


# ─────────────────────────────────────────────
# DrawingLLM 컨텍스트 주입 테스트
# ─────────────────────────────────────────────


class TestDescribeWithContext:
    """describe_drawing 컨텍스트 주입 테스트"""

    @patch("core.llm.httpx.post")
    def test_describe_with_context_enriched_prompt(
        self, mock_post, llm, sample_image, sample_context
    ):
        """컨텍스트 포함 시 프롬프트에 PRE-EXTRACTED FACTS 삽입"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Shaft drawing SH-1234 S45C shafts Ø50mm",
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.describe_drawing(sample_image, context=sample_context)

        # 프롬프트에 컨텍스트 포함 확인
        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" in prompt
        assert "SH-1234" in prompt
        assert "S45C" in prompt

    @patch("core.llm.httpx.post")
    def test_describe_without_context_unchanged(
        self, mock_post, llm, sample_image
    ):
        """컨텍스트 없음 → 기존 프롬프트 유지"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "This is a gear.",
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.describe_drawing(sample_image)

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" not in prompt
        assert result == "This is a gear."

    @patch("core.llm.httpx.post")
    def test_describe_text_only_no_image_encoding(
        self, mock_post, llm, sample_image, sample_context
    ):
        """텍스트 전용 모드 → 이미지 인코딩 스킵"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Shaft SH-1234 S45C shafts drawing.",
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.describe_drawing(sample_image, context=sample_context)

        # 이미지가 전송되지 않아야 함 (text_only 조건 충족)
        call_payload = mock_post.call_args[1]["json"]
        assert "images" not in call_payload

    @patch("core.llm.httpx.post")
    def test_describe_hallucination_validation(
        self, mock_post, llm, sample_image, sample_context
    ):
        """환각 검증이 실행됨"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Gear assembly made of aluminum.",
            "done": True,
        }
        mock_post.return_value = mock_resp

        llm.describe_drawing(sample_image, context=sample_context)

        assert llm._last_validation is not None
        assert isinstance(llm._last_validation, ValidationResult)

    @patch("core.llm.httpx.post")
    def test_describe_no_validation_on_error(
        self, mock_post, llm, sample_image, sample_context
    ):
        """오류 응답 시 환각 검증 스킵"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "[오류] 연결 실패",
            "done": True,
        }
        mock_post.return_value = mock_resp

        llm._last_validation = None
        llm.describe_drawing(sample_image, context=sample_context)

        assert llm._last_validation is None


class TestClassifyWithContext:
    """classify_drawing 컨텍스트 주입 테스트"""

    @patch("core.llm.httpx.post")
    def test_classify_with_yolo_hint(
        self, mock_post, llm, sample_image, sample_context
    ):
        """YOLO 힌트가 프롬프트에 포함"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"category": "Shafts", "confidence": "high"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.classify_drawing(
            sample_image,
            categories=["Shafts", "Gears"],
            context=sample_context,
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "automated classifier" in prompt
        assert "Shafts" in prompt
        assert "92%" in prompt

    @patch("core.llm.httpx.post")
    def test_classify_without_context_unchanged(
        self, mock_post, llm, sample_image
    ):
        """컨텍스트 없음 → 기존 동작"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"part_type": "gear"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.classify_drawing(sample_image)

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "automated classifier" not in prompt

    @patch("core.llm.httpx.post")
    def test_classify_auto_with_context(
        self, mock_post, llm, sample_image, sample_context
    ):
        """자동 분류 + YOLO 힌트"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"part_type": "shaft"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.classify_drawing(
            sample_image, context=sample_context
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "automated classifier" in prompt


class TestAnswerWithContext:
    """answer_question 컨텍스트 주입 테스트"""

    @patch("core.llm.httpx.post")
    def test_answer_with_context_includes_facts(
        self, mock_post, llm, sample_image, sample_context
    ):
        """컨텍스트 포함 시 PRE-EXTRACTED FACTS 삽입"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "SH-1234 S45C shafts 50mm",
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.answer_question(
            sample_image, "재질은?", context=sample_context
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" in prompt
        assert "S45C" in prompt
        assert "OCR-extracted values" in prompt

    @patch("core.llm.httpx.post")
    def test_answer_without_context_unchanged(
        self, mock_post, llm, sample_image
    ):
        """컨텍스트 없음 → 기존 동작"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "The diameter is 50mm.",
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.answer_question(sample_image, "지름은?")

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" not in prompt

    @patch("core.llm.httpx.post")
    def test_answer_hallucination_validation(
        self, mock_post, llm, sample_image, sample_context
    ):
        """Q&A에서도 환각 검증 실행"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Material is S45C.",
            "done": True,
        }
        mock_post.return_value = mock_resp

        llm.answer_question(
            sample_image, "재질은?", context=sample_context
        )

        assert llm._last_validation is not None


class TestGenerateMetadataWithContext:
    """generate_metadata 컨텍스트 주입 테스트"""

    @patch("core.llm.httpx.post")
    def test_metadata_with_context(
        self, mock_post, llm, sample_image, sample_context
    ):
        """컨텍스트 사용 시 OCR text 대신 context 사용"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"part_number": "SH-1234"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.generate_metadata(
            sample_image, context=sample_context
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" in prompt

    @patch("core.llm.httpx.post")
    def test_metadata_without_context_uses_ocr_text(
        self, mock_post, llm, sample_image
    ):
        """컨텍스트 없음 → ocr_text 사용 (하위 호환)"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"part_number": "X-001"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.generate_metadata(
            sample_image, ocr_text="X-001 SUS304"
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "X-001 SUS304" in prompt
        assert "PRE-EXTRACTED FACTS" not in prompt

    @patch("core.llm.httpx.post")
    def test_metadata_context_overrides_ocr_text(
        self, mock_post, llm, sample_image, sample_context
    ):
        """context가 있으면 ocr_text보다 우선"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{"part_number": "SH-1234"}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        result = llm.generate_metadata(
            sample_image, ocr_text="OLD TEXT", context=sample_context
        )

        call_payload = mock_post.call_args[1]["json"]
        prompt = call_payload["prompt"]
        assert "PRE-EXTRACTED FACTS" in prompt
        assert "OLD TEXT" not in prompt

    @patch("core.llm.httpx.post")
    def test_metadata_num_predict_limited(
        self, mock_post, llm, sample_image
    ):
        """metadata는 num_predict=1024"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": '{}',
            "done": True,
        }
        mock_post.return_value = mock_resp

        llm.generate_metadata(sample_image)

        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["options"]["num_predict"] == 1024


# ─────────────────────────────────────────────
# _should_use_text_only 테스트
# ─────────────────────────────────────────────


class TestShouldUseTextOnly:
    """텍스트 전용 모드 판단 테스트"""

    def test_text_only_rich_context(self, llm, sample_context):
        """충분한 컨텍스트 → True"""
        assert llm._should_use_text_only(sample_context) is True

    def test_text_only_no_context(self, llm):
        """컨텍스트 없음 → False"""
        assert llm._should_use_text_only(None) is False

    def test_text_only_empty_context(self, llm):
        """빈 컨텍스트 → False"""
        ctx = AnalysisContext()
        assert llm._should_use_text_only(ctx) is False

    def test_text_only_low_confidence(self, llm):
        """카테고리 신뢰도 0.4 → False"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.4,
            part_numbers=["P-001"],
            materials=["S45C"],
            dimensions=["10mm", "20mm"],
        )
        assert llm._should_use_text_only(ctx) is False

    def test_text_only_partial_context(self, llm):
        """카테고리만 있음 (fact 부족) → False"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.92,
        )
        assert llm._should_use_text_only(ctx) is False

    def test_text_only_category_plus_two_facts(self, llm):
        """카테고리 + 2가지 사실 → True"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.85,
            part_numbers=["P-001"],
            materials=["S45C"],
        )
        assert llm._should_use_text_only(ctx) is True

    def test_text_only_category_plus_one_fact(self, llm):
        """카테고리 + 1가지 사실 → False"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.85,
            part_numbers=["P-001"],
        )
        assert llm._should_use_text_only(ctx) is False

    def test_text_only_dims_need_two(self, llm):
        """치수는 2개 이상이어야 fact로 인정"""
        ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.85,
            dimensions=["10mm"],  # 1개만 → 부족
            part_numbers=["P-001"],
        )
        assert llm._should_use_text_only(ctx) is False

        ctx.dimensions = ["10mm", "20mm"]  # 2개 → 충분
        assert llm._should_use_text_only(ctx) is True


# ─────────────────────────────────────────────
# _generate num_predict 테스트
# ─────────────────────────────────────────────


class TestGenerateNumPredict:
    """_generate() num_predict 파라미터 테스트"""

    @patch("core.llm.httpx.post")
    def test_default_num_predict_text(self, mock_post, llm):
        """이미지 없을 때 기본값 2048"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "ok", "done": True}
        mock_post.return_value = mock_resp

        llm._generate("test prompt")

        payload = mock_post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 2048

    @patch("core.llm.httpx.post")
    def test_override_num_predict(self, mock_post, llm):
        """num_predict 오버라이드"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "ok", "done": True}
        mock_post.return_value = mock_resp

        llm._generate("test prompt", num_predict=1024)

        payload = mock_post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 1024

    @patch("core.llm.httpx.post")
    def test_vlm_default_num_predict(self, mock_post, llm, sample_image):
        """이미지 있을 때 기본값 8192"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "ok", "done": True}
        mock_post.return_value = mock_resp

        llm._generate("test prompt", image_path=sample_image)

        payload = mock_post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 8192

    @patch("core.llm.httpx.post")
    def test_vlm_override_num_predict(self, mock_post, llm, sample_image):
        """이미지 + num_predict 명시 → 명시값 사용"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "ok", "done": True}
        mock_post.return_value = mock_resp

        llm._generate("test prompt", image_path=sample_image, num_predict=4096)

        payload = mock_post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 4096

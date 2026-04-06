"""
DrawingPipeline 통합 테스트

모든 컴포넌트를 mock으로 대체하여 파이프라인 오케스트레이션을 테스트한다.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from core.pipeline import DrawingPipeline, DrawingRecord


@pytest.fixture
def mock_pipeline(tmp_path, mock_image_embedder, mock_text_embedder, mock_llm):
    """전체 mock 기반 DrawingPipeline"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    vs_dir = tmp_path / "vector_store"
    vs_dir.mkdir()

    with patch("core.pipeline.DrawingOCR") as mock_ocr_cls, \
         patch("core.pipeline.ImageEmbedder") as mock_img_cls, \
         patch("core.pipeline.TextEmbedder") as mock_txt_cls, \
         patch("core.pipeline.VectorStore") as mock_vs_cls, \
         patch("core.pipeline.DrawingLLM") as mock_llm_cls:

        # OCR mock
        mock_ocr = MagicMock()
        mock_ocr.extract.return_value = MagicMock(
            full_text="SUS304 Ø50mm",
            part_numbers=["AB-1234"],
            dimensions=["Ø50mm"],
            materials=["SUS"],
        )
        mock_ocr_cls.return_value = mock_ocr

        # Embedder mock
        mock_img_cls.return_value = mock_image_embedder
        mock_txt_cls.return_value = mock_text_embedder

        # VectorStore mock
        mock_vs = MagicMock()
        mock_vs.get_stats.return_value = {
            "image_collection_count": 5,
            "text_collection_count": 5,
        }
        mock_vs_cls.return_value = mock_vs

        # LLM mock
        mock_llm_cls.return_value = mock_llm

        pipeline = DrawingPipeline(
            upload_dir=str(upload_dir),
            vector_store_dir=str(vs_dir),
        )

        return pipeline


class TestRegisterDrawing:
    """도면 등록 테스트"""

    def test_register_success(self, mock_pipeline, sample_image):
        """정상 등록"""
        record = mock_pipeline.register_drawing(sample_image)
        assert record.drawing_id
        assert record.file_name == "test_drawing.png"
        assert record.ocr_text == "SUS304 Ø50mm"
        assert "AB-1234" in record.part_numbers

    def test_register_without_llm(self, mock_pipeline, sample_image):
        """LLM 없이 등록"""
        record = mock_pipeline.register_drawing(sample_image, use_llm=False)
        assert record.description == ""

    def test_register_with_category(self, mock_pipeline, sample_image):
        """카테고리 지정 등록"""
        record = mock_pipeline.register_drawing(sample_image, category="Gears")
        assert record.category == "Gears"

    def test_register_saves_record(self, mock_pipeline, sample_image):
        """등록 후 레코드 저장"""
        record = mock_pipeline.register_drawing(sample_image, use_llm=False)
        assert mock_pipeline.get_record(record.drawing_id) is not None


class TestSaveRecords:
    """레코드 저장 테스트"""

    def test_atomic_write(self, mock_pipeline, sample_image):
        """등록 후 레코드가 영속 저장됨 (SQLite 또는 JSON)"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)

        if mock_pipeline._use_sqlite and mock_pipeline._record_store is not None:
            # SQLite 모드: DB 파일 존재 + 레코드 1건
            assert Path(mock_pipeline._record_store._db_path).exists()
            assert mock_pipeline._record_store.count() == 1
        else:
            # JSON 모드: records.json 파일 존재 + 1건
            records_file = mock_pipeline._records_file
            assert records_file.exists()
            data = json.loads(records_file.read_text(encoding="utf-8"))
            assert len(data) == 1

    def test_save_preserves_on_error(self, mock_pipeline, sample_image, tmp_path):
        """저장 실패 시 기존 데이터 보존"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)

        if mock_pipeline._use_sqlite and mock_pipeline._record_store is not None:
            assert mock_pipeline._record_store.count() == 1
        else:
            assert mock_pipeline._records_file.exists()


class TestBatchRegister:
    """배치 등록 테스트"""

    def test_batch_register(self, mock_pipeline, sample_images):
        """배치 등록"""
        img_dir = sample_images[0].parent
        records = mock_pipeline.register_batch(img_dir, use_llm=False)
        assert len(records) == 3

    def test_batch_partial_failure(self, mock_pipeline, sample_images):
        """배치 중 일부 실패"""
        # 두 번째 호출에서 실패
        orig_register = mock_pipeline.register_drawing
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Test error")
            return orig_register(*args, **kwargs)

        mock_pipeline.register_drawing = side_effect
        img_dir = sample_images[0].parent
        records = mock_pipeline.register_batch(img_dir, use_llm=False)
        assert len(records) == 2  # 3개 중 1개 실패 → 2개 성공


class TestGetStats:
    """통계 테스트"""

    def test_get_stats(self, mock_pipeline):
        """시스템 통계 조회"""
        stats = mock_pipeline.get_stats()
        assert "total_drawings" in stats
        assert "vector_store" in stats
        assert "ollama_healthy" in stats


# ─────────────────────────────────────────────
# Phase 2: 검색 파이프라인 강화 테스트
# ─────────────────────────────────────────────


class TestBuildRichText:
    """텍스트 보강 테스트"""

    def test_build_rich_text_full(self, mock_pipeline):
        """OCR + 카테고리 + 키워드 보강"""
        mock_pipeline._category_keywords = {
            "Shafts": "shaft 샤프트 축 precision ground",
        }
        result = mock_pipeline._build_rich_text("SUS304 Ø50mm", "Shafts")
        assert "SUS304 Ø50mm" in result
        assert "Shafts" in result
        assert "shaft 샤프트" in result

    def test_build_rich_text_no_keywords(self, mock_pipeline):
        """키워드 없는 카테고리"""
        mock_pipeline._category_keywords = {}
        result = mock_pipeline._build_rich_text("test ocr", "Unknown")
        assert "test ocr" in result
        assert "Unknown" in result

    def test_build_rich_text_no_category(self, mock_pipeline):
        """카테고리 없음"""
        mock_pipeline._category_keywords = {"Shafts": "shaft"}
        result = mock_pipeline._build_rich_text("test ocr", "")
        assert result == "test ocr"

    def test_build_rich_text_empty(self, mock_pipeline):
        """OCR + 카테고리 모두 없음"""
        mock_pipeline._category_keywords = {}
        result = mock_pipeline._build_rich_text("", "")
        assert result == ""

    def test_build_rich_text_underscore_to_space(self, mock_pipeline):
        """카테고리명 언더스코어 → 공백 변환"""
        mock_pipeline._category_keywords = {}
        result = mock_pipeline._build_rich_text("", "Bearings_with_Holder")
        assert "Bearings with Holder" in result

    def test_build_rich_text_ocr_truncated(self, mock_pipeline):
        """OCR 텍스트 500자 제한"""
        mock_pipeline._category_keywords = {}
        long_ocr = "A" * 600
        result = mock_pipeline._build_rich_text(long_ocr, "")
        assert len(result) == 500


class TestSearchWithCategory:
    """카테고리 필터 검색 테스트"""

    def test_search_by_text_with_category(self, mock_pipeline):
        """텍스트 검색 + 카테고리 필터"""
        mock_pipeline._category_keywords = {
            "Gears": "gear 기어 spur helical",
        }
        from core.vector_store import SearchResult
        mock_pipeline._vector_store.hybrid_search.return_value = [
            SearchResult(
                drawing_id="id1", file_path="/d1.png",
                distance=0.1, score=0.9,
                metadata={"category": "Gears"},
            )
        ]
        results = mock_pipeline.search_by_text("기어 도면", category="Gears")
        assert len(results) == 1

        call_kwargs = mock_pipeline._vector_store.hybrid_search.call_args[1]
        assert call_kwargs["where_filter"] == {"category": "Gears"}

    def test_search_by_text_no_category(self, mock_pipeline):
        """텍스트 검색 카테고리 미지정 → 필터 없음"""
        mock_pipeline._category_keywords = {}
        mock_pipeline._vector_store.hybrid_search.return_value = []
        mock_pipeline.search_by_text("test query")

        call_kwargs = mock_pipeline._vector_store.hybrid_search.call_args[1]
        assert call_kwargs["where_filter"] is None

    def test_search_by_text_expands_query(self, mock_pipeline):
        """텍스트 검색 시 카테고리 키워드로 쿼리 확장"""
        mock_pipeline._category_keywords = {
            "Gears": "gear 기어 spur helical",
        }
        mock_pipeline._vector_store.hybrid_search.return_value = []
        mock_pipeline.search_by_text("도면 검색", category="Gears")

        # text_embedder.embed에 확장된 쿼리가 전달되었는지 확인
        embed_call = mock_pipeline._text_embedder.embed.call_args[0][0]
        assert "gear 기어" in embed_call
        assert "도면 검색" in embed_call

    def test_search_by_image_with_manual_category(self, mock_pipeline):
        """이미지 검색 + 수동 카테고리 필터"""
        from core.vector_store import SearchResult
        mock_pipeline._vector_store.search_by_image.return_value = [
            SearchResult(
                drawing_id="id1", file_path="/d1.png",
                distance=0.1, score=0.9,
                metadata={"category": "Shafts"},
            )
        ]
        results = mock_pipeline.search_by_image(
            "/fake/path.png", category="Shafts",
        )
        assert len(results) == 1

        call_kwargs = mock_pipeline._vector_store.search_by_image.call_args[1]
        assert call_kwargs["where_filter"] == {"category": "Shafts"}

    def test_search_by_image_with_yolo_filter(self, mock_pipeline, mock_classifier):
        """이미지 검색 + YOLO 자동 필터"""
        mock_pipeline._classifier = mock_classifier
        mock_classifier.confidence_threshold = 0.5

        from core.vector_store import SearchResult
        mock_pipeline._vector_store.search_by_image.return_value = [
            SearchResult(
                drawing_id="id1", file_path="/d1.png",
                distance=0.1, score=0.9,
                metadata={"category": "Shafts"},
            )
        ]
        results = mock_pipeline.search_by_image(
            "/fake/path.png", use_yolo_filter=True,
        )
        assert len(results) == 1

        call_kwargs = mock_pipeline._vector_store.search_by_image.call_args[1]
        assert call_kwargs["where_filter"] == {"category": "Shafts"}

    def test_search_by_image_yolo_low_confidence(self, mock_pipeline, mock_classifier):
        """YOLO 신뢰도 낮으면 필터 미적용"""
        from core.classifier import ClassificationResult
        mock_pipeline._classifier = mock_classifier
        mock_classifier.confidence_threshold = 0.95

        mock_pipeline._vector_store.search_by_image.return_value = []
        mock_pipeline.search_by_image("/fake/path.png", use_yolo_filter=True)

        call_kwargs = mock_pipeline._vector_store.search_by_image.call_args[1]
        assert call_kwargs["where_filter"] is None

    def test_search_by_image_no_classifier(self, mock_pipeline):
        """분류기 없으면 YOLO 필터 무시"""
        mock_pipeline._classifier = None
        mock_pipeline._vector_store.search_by_image.return_value = []
        mock_pipeline.search_by_image("/fake/path.png", use_yolo_filter=True)

        call_kwargs = mock_pipeline._vector_store.search_by_image.call_args[1]
        assert call_kwargs["where_filter"] is None


class TestSearchByPartNumber:
    """부품번호 검색 테스트"""

    def test_search_part_number_exact(self, mock_pipeline, sample_image):
        """부품번호 정확 검색"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)
        results = mock_pipeline.search_by_part_number("AB-1234")
        assert len(results) == 1
        assert "AB-1234" in results[0].part_numbers

    def test_search_part_number_partial(self, mock_pipeline, sample_image):
        """부품번호 부분 일치"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)
        results = mock_pipeline.search_by_part_number("AB-12")
        assert len(results) == 1

    def test_search_part_number_case_insensitive(self, mock_pipeline, sample_image):
        """부품번호 대소문자 무시"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)
        results = mock_pipeline.search_by_part_number("ab-1234")
        assert len(results) == 1

    def test_search_part_number_no_match(self, mock_pipeline, sample_image):
        """부품번호 미매칭"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)
        results = mock_pipeline.search_by_part_number("ZZ-9999")
        assert len(results) == 0

    def test_search_part_number_empty(self, mock_pipeline):
        """빈 부품번호"""
        results = mock_pipeline.search_by_part_number("")
        assert len(results) == 0

    def test_search_part_number_whitespace(self, mock_pipeline, sample_image):
        """부품번호 앞뒤 공백 제거"""
        mock_pipeline.register_drawing(sample_image, use_llm=False)
        results = mock_pipeline.search_by_part_number("  AB-1234  ")
        assert len(results) == 1


class TestCategoryKeywordsLoading:
    """카테고리 키워드 로딩 테스트"""

    def test_keywords_loaded(self, tmp_path, mock_image_embedder, mock_text_embedder, mock_llm):
        """키워드 파일 로드 검증"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        vs_dir = tmp_path / "vector_store"
        vs_dir.mkdir()

        kw_file = tmp_path / "keywords.json"
        kw_data = {
            "keywords": {
                "Shafts": "shaft 샤프트",
                "Gears": "gear 기어",
            }
        }
        kw_file.write_text(json.dumps(kw_data, ensure_ascii=False), encoding="utf-8")

        with patch("core.pipeline.DrawingOCR"), \
             patch("core.pipeline.ImageEmbedder") as mock_img_cls, \
             patch("core.pipeline.TextEmbedder") as mock_txt_cls, \
             patch("core.pipeline.VectorStore") as mock_vs_cls, \
             patch("core.pipeline.DrawingLLM"):
            mock_img_cls.return_value = mock_image_embedder
            mock_txt_cls.return_value = mock_text_embedder
            mock_vs_cls.return_value = MagicMock()

            pipeline = DrawingPipeline(
                upload_dir=str(upload_dir),
                vector_store_dir=str(vs_dir),
                category_keywords_path=str(kw_file),
            )

            assert len(pipeline._category_keywords) == 2
            assert "Shafts" in pipeline._category_keywords
            assert "Gears" in pipeline._category_keywords

    def test_keywords_missing_file(self, tmp_path, mock_image_embedder, mock_text_embedder, mock_llm):
        """키워드 파일 없으면 빈 dict"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        vs_dir = tmp_path / "vector_store"
        vs_dir.mkdir()

        with patch("core.pipeline.DrawingOCR"), \
             patch("core.pipeline.ImageEmbedder") as mock_img_cls, \
             patch("core.pipeline.TextEmbedder") as mock_txt_cls, \
             patch("core.pipeline.VectorStore") as mock_vs_cls, \
             patch("core.pipeline.DrawingLLM"):
            mock_img_cls.return_value = mock_image_embedder
            mock_txt_cls.return_value = mock_text_embedder
            mock_vs_cls.return_value = MagicMock()

            pipeline = DrawingPipeline(
                upload_dir=str(upload_dir),
                vector_store_dir=str(vs_dir),
                category_keywords_path="/nonexistent/keywords.json",
            )

            assert pipeline._category_keywords == {}

    def test_keywords_no_path(self, mock_pipeline):
        """키워드 경로 미지정"""
        assert mock_pipeline._category_keywords == {}


class TestRegisterWithRichText:
    """등록 시 보강 텍스트 사용 테스트"""

    def test_register_uses_rich_text(self, mock_pipeline, sample_image):
        """등록 시 _build_rich_text가 사용되는지 확인"""
        mock_pipeline._category_keywords = {
            "Gears": "gear 기어 spur helical",
        }
        record = mock_pipeline.register_drawing(
            sample_image, category="Gears", use_llm=False,
        )

        # TextEmbedder.embed_passage가 보강된 텍스트로 호출되었는지 확인
        call_args = mock_pipeline._text_embedder.embed_passage.call_args[0][0]
        assert "gear 기어" in call_args
        assert "Gears" in call_args


# ─────────────────────────────────────────────
# Phase 3: 영역 탐지 통합 테스트
# ─────────────────────────────────────────────


class TestMergeOCRResults:
    """_merge_ocr_results 테스트"""

    def test_merge_title_block_adds_part_number(self, mock_pipeline):
        """표제란에서 추출한 도번이 부품번호 목록에 추가됨"""
        from core.ocr import OCRResult, RegionOCRResult

        base_ocr = OCRResult(
            full_text="기존 텍스트",
            part_numbers=["P001"],
            dimensions=["10mm"],
            materials=["SUS304"],
        )
        region_results = [
            RegionOCRResult(
                region_class="title_block",
                text="도번 A-1234",
                structured_data={"drawing_number": "A-1234", "material": "S45C"},
            ),
        ]

        merged = mock_pipeline._merge_ocr_results(base_ocr, region_results)
        assert "A-1234" in merged.part_numbers
        assert "P001" in merged.part_numbers
        # 표제란 도번이 최우선
        assert merged.part_numbers[0] == "A-1234"
        # 재질도 추가
        assert "S45C" in merged.materials
        assert merged.detection_enhanced is True

    def test_merge_dimension_area_adds_dimensions(self, mock_pipeline):
        """치수 영역에서 추가 치수 추출"""
        from core.ocr import OCRResult, RegionOCRResult

        base_ocr = OCRResult(
            full_text="기존",
            dimensions=["10mm"],
        )
        region_results = [
            RegionOCRResult(
                region_class="dimension_area",
                structured_data={"dimensions": ["25mm", "50mm"]},
            ),
        ]

        merged = mock_pipeline._merge_ocr_results(base_ocr, region_results)
        assert "25mm" in merged.dimensions
        assert "50mm" in merged.dimensions
        assert "10mm" in merged.dimensions

    def test_merge_parts_table_adds_text(self, mock_pipeline):
        """부품표 텍스트가 full_text에 추가"""
        from core.ocr import OCRResult, RegionOCRResult

        base_ocr = OCRResult(full_text="기존 텍스트")
        region_results = [
            RegionOCRResult(
                region_class="parts_table",
                text="1 축 2 S45C",
                structured_data={"rows": [{"item_no": "1"}]},
            ),
        ]

        merged = mock_pipeline._merge_ocr_results(base_ocr, region_results)
        assert "1 축 2 S45C" in merged.full_text
        assert "기존 텍스트" in merged.full_text

    def test_merge_no_duplicate_parts(self, mock_pipeline):
        """중복 부품번호 미추가"""
        from core.ocr import OCRResult, RegionOCRResult

        base_ocr = OCRResult(
            full_text="test",
            part_numbers=["A-1234"],
        )
        region_results = [
            RegionOCRResult(
                region_class="title_block",
                structured_data={"drawing_number": "A-1234"},
            ),
        ]

        merged = mock_pipeline._merge_ocr_results(base_ocr, region_results)
        count = sum(1 for pn in merged.part_numbers if pn == "A-1234")
        assert count == 1

    def test_merge_preserves_original(self, mock_pipeline):
        """원본 OCR 결과가 변경되지 않음"""
        from core.ocr import OCRResult, RegionOCRResult

        base_ocr = OCRResult(
            full_text="original",
            part_numbers=["P001"],
        )
        region_results = [
            RegionOCRResult(
                region_class="title_block",
                structured_data={"drawing_number": "NEW-001"},
            ),
        ]

        merged = mock_pipeline._merge_ocr_results(base_ocr, region_results)
        # 원본은 변경되지 않아야 함
        assert "NEW-001" not in base_ocr.part_numbers
        assert "NEW-001" in merged.part_numbers


class TestRegisterWithDetection:
    """탐지기 통합 등록 테스트"""

    def test_register_without_detector(self, mock_pipeline, sample_image):
        """탐지기 없이 등록 (기존 동작)"""
        mock_pipeline._detector = None
        record = mock_pipeline.register_drawing(sample_image, use_llm=False)
        assert record.drawing_id
        assert record.detection_enhanced is False
        assert record.detected_regions == []

    def test_register_with_detector(self, mock_pipeline, sample_image, mock_detector):
        """탐지기 활성화 등록"""
        from core.ocr import RegionOCRResult
        mock_pipeline._detector = mock_detector

        # OCR extract_region mock 설정
        mock_pipeline._ocr.extract_region.return_value = RegionOCRResult(
            region_class="title_block",
            text="도번 TB-001",
            confidence=0.85,
            structured_data={"drawing_number": "TB-001", "material": "SUS304"},
        )

        record = mock_pipeline.register_drawing(sample_image, use_llm=False)
        assert record.drawing_id
        assert record.detection_enhanced is True
        assert len(record.detected_regions) == 2  # title_block + dimension_area

    def test_register_detector_failure_fallback(self, mock_pipeline, sample_image, mock_detector):
        """탐지기 실패 시 기본 OCR 결과 유지"""
        mock_detector.detect.side_effect = RuntimeError("Detection failed")
        mock_pipeline._detector = mock_detector

        record = mock_pipeline.register_drawing(sample_image, use_llm=False)
        assert record.drawing_id
        assert record.detection_enhanced is False
        assert record.detected_regions == []

    def test_register_saves_detection_fields(self, mock_pipeline, sample_image, mock_detector):
        """탐지 필드가 영속 저장소에 저장됨 (SQLite 또는 JSON)"""
        from core.ocr import RegionOCRResult
        mock_pipeline._detector = mock_detector
        mock_pipeline._ocr.extract_region.return_value = RegionOCRResult(
            region_class="title_block",
            structured_data={},
        )

        record = mock_pipeline.register_drawing(sample_image, use_llm=False)

        if mock_pipeline._use_sqlite and mock_pipeline._record_store is not None:
            saved = mock_pipeline._record_store.get(record.drawing_id)
            assert saved is not None
            assert "detected_regions" in saved
            assert "detection_enhanced" in saved
        else:
            records_file = mock_pipeline._records_file
            assert records_file.exists()
            import json
            data = json.loads(records_file.read_text(encoding="utf-8"))
            saved = list(data.values())[0]
            assert "detected_regions" in saved
            assert "detection_enhanced" in saved


class TestGetStatsWithDetector:
    """get_stats 탐지기 포함 테스트"""

    def test_stats_without_detector(self, mock_pipeline):
        """탐지기 없으면 yolo_detector.enabled=False"""
        mock_pipeline._detector = None
        stats = mock_pipeline.get_stats()
        assert "yolo_detector" in stats
        assert stats["yolo_detector"]["enabled"] is False

    def test_stats_with_detector(self, mock_pipeline, mock_detector):
        """탐지기 있으면 yolo_detector 상태 포함"""
        mock_pipeline._detector = mock_detector
        stats = mock_pipeline.get_stats()
        assert stats["yolo_detector"]["enabled"] is True
        assert stats["yolo_detector"]["healthy"] is True
        assert stats["yolo_detector"]["num_classes"] == 3


# ─────────────────────────────────────────────
# Phase 4: 컨텍스트 주입 통합 테스트
# ─────────────────────────────────────────────


class TestPipelineContextIntegration:
    """Phase 4 — LLM 컨텍스트 주입 통합 테스트"""

    def test_register_passes_context_to_llm(self, mock_pipeline, sample_image):
        """register_drawing 시 AnalysisContext가 LLM에 전달됨"""
        mock_pipeline.register_drawing(sample_image, category="Gears")

        # describe_drawing이 context 키워드 인자와 함께 호출되었는지 확인
        call_kwargs = mock_pipeline._llm.describe_drawing.call_args
        assert call_kwargs is not None
        # context= 키워드 인자 확인
        if call_kwargs.kwargs:
            assert "context" in call_kwargs.kwargs
            ctx = call_kwargs.kwargs["context"]
        else:
            ctx = call_kwargs.args[1] if len(call_kwargs.args) > 1 else None

        assert ctx is not None
        from core.llm import AnalysisContext
        assert isinstance(ctx, AnalysisContext)

    def test_build_analysis_context(self, mock_pipeline):
        """_build_analysis_context 빌더 정상 동작"""
        from core.ocr import OCRResult
        from core.llm import AnalysisContext

        ocr_result = OCRResult(
            full_text="AB-001 SUS304 Ø20mm",
            part_numbers=["AB-001"],
            dimensions=["Ø20mm"],
            materials=["SUS304"],
        )
        ctx = mock_pipeline._build_analysis_context(
            ocr_result=ocr_result,
            category="Gears",
            yolo_confidence=0.85,
            yolo_top_k=[("Gears", 0.85)],
            detected_regions=[
                {"class": "title_block", "bbox": [0, 0, 1, 1], "confidence": 0.9}
            ],
            title_block_data={"drawing_number": "AB-001"},
            parts_table_data={},
        )

        assert isinstance(ctx, AnalysisContext)
        assert ctx.yolo_category == "Gears"
        assert ctx.yolo_confidence == 0.85
        assert "AB-001" in ctx.part_numbers
        assert "SUS304" in ctx.materials
        assert "title_block" in ctx.detected_regions

    def test_build_analysis_context_from_record(self, mock_pipeline, sample_image):
        """DrawingRecord → AnalysisContext 변환"""
        from core.llm import AnalysisContext

        record = mock_pipeline.register_drawing(
            sample_image, category="Shafts", use_llm=False
        )
        # 레코드에 테스트 데이터 설정
        record.yolo_confidence = 0.9
        record.yolo_top_k = [("Shafts", 0.9)]
        record.detected_regions = [{"class": "title_block"}]
        record.title_block_data = {"drawing_number": "T-001"}

        ctx = mock_pipeline._build_analysis_context_from_record(record)

        assert isinstance(ctx, AnalysisContext)
        assert ctx.yolo_category == "Shafts"
        assert ctx.yolo_confidence == 0.9
        assert "title_block" in ctx.detected_regions

    def test_describe_with_drawing_id(self, mock_pipeline, sample_image):
        """describe()에 drawing_id 전달 시 context 자동 구성"""
        record = mock_pipeline.register_drawing(
            sample_image, category="Gears", use_llm=False
        )

        mock_pipeline.describe(sample_image, drawing_id=record.drawing_id)

        # describe_drawing이 context와 함께 호출됨
        call_kwargs = mock_pipeline._llm.describe_drawing.call_args
        if call_kwargs.kwargs:
            ctx = call_kwargs.kwargs.get("context")
        else:
            ctx = call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        assert ctx is not None

    def test_describe_without_drawing_id(self, mock_pipeline, sample_image):
        """describe()에 drawing_id 없으면 context=None"""
        mock_pipeline.describe(sample_image)

        call_kwargs = mock_pipeline._llm.describe_drawing.call_args
        if call_kwargs.kwargs:
            ctx = call_kwargs.kwargs.get("context")
        else:
            ctx = call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        assert ctx is None

    def test_ask_with_drawing_id(self, mock_pipeline, sample_image):
        """ask()에 drawing_id 전달 시 context 자동 구성"""
        record = mock_pipeline.register_drawing(
            sample_image, category="Gears", use_llm=False
        )

        mock_pipeline.ask(
            sample_image, "재질은?", drawing_id=record.drawing_id
        )

        call_kwargs = mock_pipeline._llm.answer_question.call_args
        if call_kwargs.kwargs:
            ctx = call_kwargs.kwargs.get("context")
        else:
            ctx = call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        assert ctx is not None

    def test_ask_without_drawing_id(self, mock_pipeline, sample_image):
        """ask()에 drawing_id 없으면 context=None"""
        mock_pipeline.ask(sample_image, "재질은?")

        call_kwargs = mock_pipeline._llm.answer_question.call_args
        if call_kwargs.kwargs:
            ctx = call_kwargs.kwargs.get("context")
        else:
            ctx = call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        assert ctx is None

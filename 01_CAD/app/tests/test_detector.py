"""
YOLO-det DrawingDetector 단위 테스트

mock 기반으로 ultralytics 없이 탐지기의 로직을 검증한다.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict

from core.detector import DetectedRegion, DetectionResult, DrawingDetector


# ─────────────────────────────────────────────
# DetectedRegion 데이터클래스 테스트
# ─────────────────────────────────────────────

class TestDetectedRegion:
    """DetectedRegion 데이터클래스 검증"""

    def test_default_values(self):
        """기본값 초기화"""
        region = DetectedRegion()
        assert region.class_name == ""
        assert region.confidence == 0.0
        assert region.bbox == (0, 0, 0, 0)
        assert region.bbox_normalized == (0.0, 0.0, 0.0, 0.0)

    def test_full_initialization(self):
        """전체 필드 초기화"""
        region = DetectedRegion(
            class_name="title_block",
            confidence=0.92,
            bbox=(100, 200, 500, 400),
            bbox_normalized=(0.1, 0.2, 0.5, 0.4),
        )
        assert region.class_name == "title_block"
        assert region.confidence == 0.92
        assert region.bbox == (100, 200, 500, 400)
        assert region.bbox_normalized == (0.1, 0.2, 0.5, 0.4)

    def test_serialization(self):
        """dict 변환 가능 (JSON 직렬화용)"""
        region = DetectedRegion(
            class_name="parts_table",
            confidence=0.85,
            bbox=(50, 50, 300, 200),
        )
        d = asdict(region)
        assert isinstance(d, dict)
        assert d["class_name"] == "parts_table"
        assert d["confidence"] == 0.85


# ─────────────────────────────────────────────
# DetectionResult 데이터클래스 테스트
# ─────────────────────────────────────────────

class TestDetectionResult:
    """DetectionResult 데이터클래스 검증"""

    def test_default_values(self):
        """기본값 초기화"""
        result = DetectionResult()
        assert result.regions == []
        assert result.image_size == (0, 0)
        assert result.model_name == ""

    def test_get_regions_by_class(self):
        """클래스별 영역 필터링"""
        regions = [
            DetectedRegion(class_name="title_block", confidence=0.9, bbox=(0, 0, 100, 100)),
            DetectedRegion(class_name="dimension_area", confidence=0.8, bbox=(100, 100, 200, 200)),
            DetectedRegion(class_name="title_block", confidence=0.7, bbox=(200, 200, 300, 300)),
        ]
        result = DetectionResult(regions=regions)

        tb = result.get_regions_by_class("title_block")
        assert len(tb) == 2

        da = result.get_regions_by_class("dimension_area")
        assert len(da) == 1

        pt = result.get_regions_by_class("parts_table")
        assert len(pt) == 0

    def test_title_blocks_property(self):
        """title_blocks property"""
        regions = [
            DetectedRegion(class_name="title_block", confidence=0.9),
            DetectedRegion(class_name="dimension_area", confidence=0.8),
        ]
        result = DetectionResult(regions=regions)
        assert len(result.title_blocks) == 1
        assert result.title_blocks[0].class_name == "title_block"

    def test_dimension_areas_property(self):
        """dimension_areas property"""
        regions = [
            DetectedRegion(class_name="dimension_area", confidence=0.8),
            DetectedRegion(class_name="dimension_area", confidence=0.7),
        ]
        result = DetectionResult(regions=regions)
        assert len(result.dimension_areas) == 2

    def test_parts_tables_property(self):
        """parts_tables property"""
        regions = [
            DetectedRegion(class_name="parts_table", confidence=0.85),
        ]
        result = DetectionResult(regions=regions)
        assert len(result.parts_tables) == 1

    def test_empty_result_properties(self):
        """빈 결과의 property 접근"""
        result = DetectionResult()
        assert result.title_blocks == []
        assert result.dimension_areas == []
        assert result.parts_tables == []


# ─────────────────────────────────────────────
# DrawingDetector 테스트 (Mock 기반)
# ─────────────────────────────────────────────

class TestDrawingDetector:
    """DrawingDetector mock 기반 단위 테스트"""

    def test_init_stores_config(self):
        """초기화 시 설정값 저장"""
        det = DrawingDetector(
            model_path="models/test.pt",
            confidence_threshold=0.4,
            iou_threshold=0.6,
            device="cpu",
        )
        assert det.model_path == Path("models/test.pt")
        assert det.confidence_threshold == 0.4
        assert det.iou_threshold == 0.6
        assert det._device == "cpu"
        assert det._model is None  # 지연 로딩

    def test_init_model_file_not_found(self):
        """모델 파일이 없을 때 FileNotFoundError 발생"""
        det = DrawingDetector(model_path="/nonexistent/model.pt")
        with pytest.raises(FileNotFoundError, match="모델 파일 없음"):
            det._init_model()

    @patch("core.detector.DrawingDetector._init_model")
    def test_detect_returns_result(self, mock_init, sample_image):
        """detect()가 DetectionResult를 반환"""
        det = DrawingDetector(model_path="models/test.pt")

        # mock YOLO 모델의 predict 결과 시뮬레이션
        mock_boxes = MagicMock()
        mock_boxes.xyxy = MagicMock()
        mock_boxes.xyxy.cpu.return_value = MagicMock(
            numpy=MagicMock(return_value=np.array([
                [10, 20, 200, 180],  # title_block
                [50, 50, 150, 120],  # dimension_area
            ]))
        )
        mock_boxes.conf = MagicMock()
        mock_boxes.conf.cpu.return_value = MagicMock(
            numpy=MagicMock(return_value=np.array([0.92, 0.85]))
        )
        mock_boxes.cls = MagicMock()
        mock_boxes.cls.cpu.return_value = MagicMock(
            numpy=MagicMock(return_value=np.array([0, 1]))
        )
        mock_boxes.__len__ = MagicMock(return_value=2)

        mock_result = MagicMock()
        mock_result.boxes = mock_boxes
        mock_result.orig_shape = (224, 224)

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result]
        mock_model.names = {0: "title_block", 1: "dimension_area", 2: "parts_table"}

        det._model = mock_model

        result = det.detect(sample_image)

        assert isinstance(result, DetectionResult)
        assert len(result.regions) == 2
        assert result.regions[0].class_name == "title_block"
        assert result.regions[0].confidence == 0.92
        assert result.regions[1].class_name == "dimension_area"
        assert result.regions[1].confidence == 0.85
        assert result.image_size == (224, 224)

    @patch("core.detector.DrawingDetector._init_model")
    def test_detect_empty_results(self, mock_init, sample_image):
        """탐지 결과 없을 때 빈 DetectionResult 반환"""
        det = DrawingDetector(model_path="models/test.pt")

        mock_model = MagicMock()
        mock_model.predict.return_value = []

        det._model = mock_model

        result = det.detect(sample_image)
        assert isinstance(result, DetectionResult)
        assert len(result.regions) == 0

    @patch("core.detector.DrawingDetector._init_model")
    def test_detect_image_not_found(self, mock_init):
        """존재하지 않는 이미지 시 FileNotFoundError"""
        det = DrawingDetector(model_path="models/test.pt")
        det._model = MagicMock()

        with pytest.raises(FileNotFoundError, match="이미지 파일 없음"):
            det.detect("/nonexistent/image.png")

    @patch("core.detector.DrawingDetector._init_model")
    def test_detect_exception_returns_empty_result(self, mock_init, sample_image):
        """추론 예외 시 빈 결과 반환"""
        det = DrawingDetector(model_path="models/test.pt")

        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("GPU error")
        det._model = mock_model

        result = det.detect(sample_image)
        assert isinstance(result, DetectionResult)
        assert len(result.regions) == 0

    @patch("core.detector.DrawingDetector._init_model")
    def test_crop_region(self, mock_init, sample_image):
        """crop_region이 PIL Image를 반환"""
        from PIL import Image

        det = DrawingDetector(model_path="models/test.pt")
        det._model = MagicMock()

        region = DetectedRegion(
            class_name="title_block",
            confidence=0.9,
            bbox=(10, 10, 200, 200),
        )

        cropped = det.crop_region(sample_image, region, padding=5)
        assert isinstance(cropped, Image.Image)
        assert cropped.size[0] > 0
        assert cropped.size[1] > 0

    @patch("core.detector.DrawingDetector._init_model")
    def test_crop_region_with_padding(self, mock_init, sample_image):
        """crop_region 패딩 적용 검증"""
        from PIL import Image

        det = DrawingDetector(model_path="models/test.pt")
        det._model = MagicMock()

        # bbox가 이미지 내부인 경우
        region = DetectedRegion(
            class_name="title_block",
            bbox=(50, 50, 150, 150),
        )

        # padding=0
        cropped_no_pad = det.crop_region(sample_image, region, padding=0)
        # padding=20
        cropped_with_pad = det.crop_region(sample_image, region, padding=20)

        # 패딩이 있는 경우가 더 크거나 같아야 함
        assert cropped_with_pad.size[0] >= cropped_no_pad.size[0]
        assert cropped_with_pad.size[1] >= cropped_no_pad.size[1]

    @patch("core.detector.DrawingDetector._init_model")
    def test_crop_region_boundary_clamping(self, mock_init, sample_image):
        """crop_region 경계 클램핑 — bbox가 이미지 밖으로 나가도 에러 없음"""
        from PIL import Image

        det = DrawingDetector(model_path="models/test.pt")
        det._model = MagicMock()

        # bbox가 이미지 경계를 넘어가는 경우
        region = DetectedRegion(
            class_name="title_block",
            bbox=(0, 0, 300, 300),  # 224x224 이미지인데 300x300
        )

        cropped = det.crop_region(sample_image, region, padding=10)
        assert isinstance(cropped, Image.Image)

    def test_class_names_triggers_init(self):
        """class_names 접근 시 _init_model 호출"""
        det = DrawingDetector(model_path="models/test.pt")
        mock_model = MagicMock()
        mock_model.names = {0: "title_block", 1: "dimension_area", 2: "parts_table"}

        with patch.object(det, "_init_model") as mock_init:
            det._model = mock_model
            names = det.class_names
            assert "title_block" in names
            assert len(names) == 3

    def test_num_classes(self):
        """num_classes 속성 테스트"""
        det = DrawingDetector(model_path="models/test.pt")
        mock_model = MagicMock()
        mock_model.names = {0: "title_block", 1: "dimension_area", 2: "parts_table"}

        with patch.object(det, "_init_model"):
            det._model = mock_model
            assert det.num_classes == 3

    def test_check_health_model_missing(self):
        """모델 파일 없으면 unhealthy"""
        det = DrawingDetector(model_path="/nonexistent/model.pt")
        healthy, msg = det.check_health()
        assert healthy is False
        assert "파일 없음" in msg

    @patch("core.detector.DrawingDetector._init_model")
    def test_check_health_success(self, mock_init, tmp_path):
        """모델 정상 로드 시 healthy"""
        model_path = tmp_path / "test.pt"
        model_path.write_bytes(b"fake model")

        det = DrawingDetector(model_path=str(model_path))
        mock_model = MagicMock()
        mock_model.names = {0: "title_block", 1: "dimension_area", 2: "parts_table"}
        det._model = mock_model

        healthy, msg = det.check_health()
        assert healthy is True
        assert "정상" in msg


# ─────────────────────────────────────────────
# 배치 탐지 테스트
# ─────────────────────────────────────────────

class TestDetectBatch:
    """detect_batch 테스트"""

    @patch("core.detector.DrawingDetector._init_model")
    def test_batch_returns_list(self, mock_init, sample_images):
        """배치 탐지 결과가 리스트로 반환"""
        det = DrawingDetector(model_path="models/test.pt")

        # 각 이미지에 빈 결과 시뮬레이션
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_result.orig_shape = (224, 224)

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result] * 3
        mock_model.names = {0: "title_block"}

        det._model = mock_model

        results = det.detect_batch(sample_images, batch_size=16)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, DetectionResult)

    @patch("core.detector.DrawingDetector._init_model")
    def test_batch_fallback_on_error(self, mock_init, sample_images):
        """배치 실패 시 개별 처리로 폴백"""
        det = DrawingDetector(model_path="models/test.pt")

        # predict가 첫 호출에서 실패
        mock_model = MagicMock()
        call_count = [0]

        def predict_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Batch failed")
            # 개별 호출 시 빈 결과
            mock_result = MagicMock()
            mock_result.boxes = None
            mock_result.orig_shape = (224, 224)
            return [mock_result]

        mock_model.predict.side_effect = predict_side_effect
        mock_model.names = {0: "title_block"}
        det._model = mock_model

        results = det.detect_batch(sample_images, batch_size=16)
        # 폴백으로 개별 처리된 결과
        assert len(results) == 3


# ─────────────────────────────────────────────
# 파이프라인 통합 테스트
# ─────────────────────────────────────────────

class TestPipelineDetectorIntegration:
    """파이프라인에 탐지기가 올바르게 통합되었는지 검증"""

    def test_drawing_record_has_detection_fields(self):
        """DrawingRecord에 탐지 관련 필드가 존재"""
        from core.pipeline import DrawingRecord

        record = DrawingRecord(
            drawing_id="test_id",
            file_path="/test/path.png",
            file_name="path.png",
        )
        # 기본값 확인 (하위 호환)
        assert record.detected_regions == []
        assert record.title_block_data == {}
        assert record.parts_table_data == {}
        assert record.detection_enhanced is False

    def test_drawing_record_with_detection_data(self):
        """탐지 데이터가 포함된 DrawingRecord 생성"""
        from core.pipeline import DrawingRecord

        record = DrawingRecord(
            drawing_id="test_id",
            file_path="/test/path.png",
            file_name="path.png",
            detected_regions=[
                {"class": "title_block", "bbox": [10, 20, 200, 180], "confidence": 0.92},
            ],
            title_block_data={"drawing_number": "A-1234", "material": "SUS304"},
            parts_table_data={"rows": []},
            detection_enhanced=True,
        )
        assert len(record.detected_regions) == 1
        assert record.title_block_data["drawing_number"] == "A-1234"
        assert record.detection_enhanced is True

    def test_drawing_record_backward_compatible(self):
        """기존 JSON 데이터(탐지 필드 없음)로 DrawingRecord 생성 가능"""
        from core.pipeline import DrawingRecord

        old_data = {
            "drawing_id": "abc123",
            "file_path": "/data/drawings/test.png",
            "file_name": "test.png",
            "ocr_text": "some text",
            "part_numbers": ["P001"],
            "dimensions": ["10mm"],
            "materials": ["SUS304"],
            "category": "engine",
            "description": "A gear drawing.",
            # YOLO-cls 필드 포함, 탐지 필드 없음
            "yolo_confidence": 0.9,
            "yolo_needs_review": False,
            "yolo_top_k": [["Shafts", 0.9]],
        }

        # 탐지 필드에 setdefault 적용 시뮬레이션
        old_data.setdefault("detected_regions", [])
        old_data.setdefault("title_block_data", {})
        old_data.setdefault("parts_table_data", {})
        old_data.setdefault("detection_enhanced", False)

        record = DrawingRecord(**old_data)
        assert record.category == "engine"
        assert record.detected_regions == []
        assert record.detection_enhanced is False

    def test_detection_result_import(self):
        """DetectionResult가 pipeline에서 import 가능"""
        from core.pipeline import DetectionResult
        result = DetectionResult()
        assert result.regions == []


# ─────────────────────────────────────────────
# Settings 테스트
# ─────────────────────────────────────────────

class TestSettingsDetector:
    """config/settings.py의 YOLO-det 설정 필드 검증"""

    def test_settings_has_det_fields(self):
        """Settings 클래스에 det 관련 필드가 존재"""
        from config.settings import Settings

        s = Settings()
        assert hasattr(s, "yolo_det_model_path")
        assert hasattr(s, "yolo_det_confidence_threshold")
        assert hasattr(s, "yolo_det_enabled")
        assert hasattr(s, "yolo_det_device")
        assert hasattr(s, "yolo_det_iou_threshold")

    def test_settings_det_defaults(self):
        """det 설정 기본값"""
        from config.settings import Settings

        s = Settings()
        assert s.yolo_det_model_path == "./models/yolo_det_best.pt"
        assert s.yolo_det_confidence_threshold == 0.3
        assert s.yolo_det_enabled is True
        assert s.yolo_det_device == ""
        assert s.yolo_det_iou_threshold == 0.5

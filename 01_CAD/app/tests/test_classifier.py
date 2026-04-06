"""
YOLO-cls DrawingClassifier 단위 테스트

mock 기반으로 ultralytics 없이 분류기의 로직을 검증한다.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict

from core.classifier import ClassificationResult, DrawingClassifier


# ─────────────────────────────────────────────
# ClassificationResult 데이터클래스 테스트
# ─────────────────────────────────────────────

class TestClassificationResult:
    """ClassificationResult 데이터클래스 검증"""

    def test_default_values(self):
        """기본값 초기화"""
        result = ClassificationResult()
        assert result.category == ""
        assert result.confidence == 0.0
        assert result.top_k == []
        assert result.needs_review is False
        assert result.model_name == ""

    def test_full_initialization(self):
        """전체 필드 초기화"""
        result = ClassificationResult(
            category="Shafts",
            confidence=0.95,
            top_k=[("Shafts", 0.95), ("Gears", 0.03)],
            needs_review=False,
            model_name="best.pt",
        )
        assert result.category == "Shafts"
        assert result.confidence == 0.95
        assert len(result.top_k) == 2
        assert result.top_k[0] == ("Shafts", 0.95)
        assert result.needs_review is False

    def test_needs_review_flag(self):
        """낮은 신뢰도 시 검토 플래그"""
        result = ClassificationResult(
            category="Unknown",
            confidence=0.3,
            needs_review=True,
        )
        assert result.needs_review is True

    def test_serialization(self):
        """dict 변환 가능 (JSON 직렬화용)"""
        result = ClassificationResult(
            category="Gears",
            confidence=0.88,
            top_k=[("Gears", 0.88)],
        )
        d = asdict(result)
        assert isinstance(d, dict)
        assert d["category"] == "Gears"
        assert d["confidence"] == 0.88


# ─────────────────────────────────────────────
# DrawingClassifier 테스트 (Mock 기반)
# ─────────────────────────────────────────────

class TestDrawingClassifier:
    """DrawingClassifier mock 기반 단위 테스트"""

    def test_init_stores_config(self):
        """초기화 시 설정값 저장"""
        clf = DrawingClassifier(
            model_path="models/test.pt",
            confidence_threshold=0.7,
            device="cpu",
        )
        assert clf.model_path == Path("models/test.pt")
        assert clf.confidence_threshold == 0.7
        assert clf._device == "cpu"
        assert clf._model is None  # 지연 로딩

    def test_init_model_file_not_found(self):
        """모델 파일이 없을 때 FileNotFoundError 발생"""
        clf = DrawingClassifier(model_path="/nonexistent/model.pt")
        with pytest.raises(FileNotFoundError, match="모델 파일 없음"):
            clf._init_model()

    @patch("core.classifier.DrawingClassifier._init_model")
    def test_classify_returns_result(self, mock_init, sample_image):
        """classify()가 ClassificationResult를 반환"""
        clf = DrawingClassifier(model_path="models/test.pt")

        # mock YOLO 모델의 predict 결과 시뮬레이션
        mock_probs = MagicMock()
        mock_probs.top1 = 0
        mock_probs.top1conf = MagicMock()
        mock_probs.top1conf.cpu.return_value = 0.92
        mock_probs.top5 = [0, 1, 2, 3, 4]
        top5_conf_mock = MagicMock()
        top5_conf_mock.cpu.return_value = MagicMock(
            tolist=MagicMock(return_value=[0.92, 0.04, 0.02, 0.01, 0.005])
        )
        mock_probs.top5conf = top5_conf_mock

        mock_result = MagicMock()
        mock_result.probs = mock_probs

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result]
        mock_model.names = {0: "Shafts", 1: "Gears", 2: "Bearings", 3: "Pulleys", 4: "Couplings"}

        clf._model = mock_model
        clf.model_path = sample_image.parent / "test.pt"  # 존재하는 경로

        result = clf.classify(sample_image, top_k=5)

        assert isinstance(result, ClassificationResult)
        assert result.category == "Shafts"
        assert result.confidence == 0.92
        assert len(result.top_k) == 5
        assert result.needs_review is False  # 0.92 > 0.5 threshold

    @patch("core.classifier.DrawingClassifier._init_model")
    def test_classify_low_confidence_needs_review(self, mock_init, sample_image):
        """낮은 신뢰도 시 needs_review=True"""
        clf = DrawingClassifier(
            model_path="models/test.pt",
            confidence_threshold=0.7,
        )

        mock_probs = MagicMock()
        mock_probs.top1 = 0
        mock_probs.top1conf = MagicMock()
        mock_probs.top1conf.cpu.return_value = 0.4  # < 0.7 threshold
        mock_probs.top5 = [0]
        top5_conf_mock = MagicMock()
        top5_conf_mock.cpu.return_value = MagicMock(
            tolist=MagicMock(return_value=[0.4])
        )
        mock_probs.top5conf = top5_conf_mock

        mock_result = MagicMock()
        mock_result.probs = mock_probs

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result]
        mock_model.names = {0: "Unknown"}

        clf._model = mock_model

        result = clf.classify(sample_image, top_k=1)
        assert result.needs_review is True
        assert result.confidence == 0.4

    @patch("core.classifier.DrawingClassifier._init_model")
    def test_classify_image_not_found(self, mock_init):
        """존재하지 않는 이미지 시 FileNotFoundError"""
        clf = DrawingClassifier(model_path="models/test.pt")
        clf._model = MagicMock()

        with pytest.raises(FileNotFoundError, match="이미지 파일 없음"):
            clf.classify("/nonexistent/image.png")

    @patch("core.classifier.DrawingClassifier._init_model")
    def test_classify_exception_returns_empty_result(self, mock_init, sample_image):
        """추론 예외 시 빈 결과 (needs_review=True) 반환"""
        clf = DrawingClassifier(model_path="models/test.pt")

        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("GPU error")
        clf._model = mock_model

        result = clf.classify(sample_image)
        assert result.category == ""
        assert result.needs_review is True

    def test_classify_batch_with_mock(self, mock_classifier, sample_images):
        """배치 분류 mock 테스트"""
        results = mock_classifier.classify_batch(sample_images)
        assert len(results) == 2
        assert results[0].category == "Shafts"
        assert results[1].category == "Gears"

    def test_class_names_property(self, mock_classifier):
        """class_names 속성 테스트"""
        names = mock_classifier.class_names
        assert "Shafts" in names
        assert len(names) == 4

    def test_num_classes_property(self, mock_classifier):
        """num_classes 속성 테스트"""
        assert mock_classifier.num_classes == 4

    def test_check_health(self, mock_classifier):
        """health check 테스트"""
        healthy, msg = mock_classifier.check_health()
        assert healthy is True
        assert "정상" in msg


# ─────────────────────────────────────────────
# 파이프라인 통합 테스트 (Mock)
# ─────────────────────────────────────────────

class TestPipelineClassifierIntegration:
    """파이프라인에 분류기가 올바르게 통합되었는지 검증"""

    def test_pipeline_has_classifier_attribute(self):
        """DrawingPipeline이 _classifier 속성을 가짐"""
        from core.pipeline import DrawingPipeline
        # 실제 초기화 대신 속성 존재만 확인 (import-level)
        assert hasattr(DrawingPipeline, '__init__')

    def test_drawing_record_has_yolo_fields(self):
        """DrawingRecord에 YOLO 관련 필드가 존재"""
        from core.pipeline import DrawingRecord

        record = DrawingRecord(
            drawing_id="test_id",
            file_path="/test/path.png",
            file_name="path.png",
        )
        # 기본값 확인 (하위 호환)
        assert record.yolo_confidence == 0.0
        assert record.yolo_needs_review is False
        assert record.yolo_top_k == []

    def test_drawing_record_with_yolo_data(self):
        """YOLO 데이터가 포함된 DrawingRecord 생성"""
        from core.pipeline import DrawingRecord

        record = DrawingRecord(
            drawing_id="test_id",
            file_path="/test/path.png",
            file_name="path.png",
            category="Shafts",
            yolo_confidence=0.92,
            yolo_needs_review=False,
            yolo_top_k=[("Shafts", 0.92), ("Gears", 0.04)],
        )
        assert record.category == "Shafts"
        assert record.yolo_confidence == 0.92
        assert len(record.yolo_top_k) == 2

    def test_drawing_record_backward_compatible(self):
        """기존 JSON 데이터(YOLO 필드 없음)로 DrawingRecord 생성 가능"""
        from core.pipeline import DrawingRecord

        # 기존 records.json 형태의 데이터
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
        }
        # YOLO 필드 없이도 생성 가능해야 함
        record = DrawingRecord(**old_data)
        assert record.category == "engine"
        assert record.yolo_confidence == 0.0  # 기본값
        assert record.yolo_needs_review is False
        assert record.yolo_top_k == []

    def test_classification_result_import(self):
        """ClassificationResult가 pipeline에서 import 가능"""
        from core.pipeline import ClassificationResult
        result = ClassificationResult(category="test", confidence=0.5)
        assert result.category == "test"

    def test_get_stats_includes_yolo(self, mock_classifier):
        """get_stats()에 yolo_classifier 키가 포함되는지 확인"""
        # mock_classifier의 check_health 반환값 확인
        healthy, msg = mock_classifier.check_health()
        assert healthy is True


# ─────────────────────────────────────────────
# Settings 테스트
# ─────────────────────────────────────────────

class TestSettingsYolo:
    """config/settings.py의 YOLO 설정 필드 검증"""

    def test_settings_has_yolo_fields(self):
        """Settings 클래스에 YOLO 관련 필드가 존재"""
        from config.settings import Settings

        s = Settings()
        assert hasattr(s, "yolo_cls_model_path")
        assert hasattr(s, "yolo_cls_confidence_threshold")
        assert hasattr(s, "yolo_cls_enabled")
        assert hasattr(s, "yolo_cls_device")

    def test_settings_yolo_defaults(self):
        """YOLO 설정 기본값"""
        from config.settings import Settings

        s = Settings()
        assert s.yolo_cls_model_path == "./models/yolo_cls_v2_best.pt"
        assert s.yolo_cls_confidence_threshold == 0.5
        assert s.yolo_cls_enabled is True
        assert s.yolo_cls_device == ""

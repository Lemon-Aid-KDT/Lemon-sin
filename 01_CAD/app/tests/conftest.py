"""
DrawingLLM 테스트 공통 fixtures

mock 기반으로 외부 의존성(CLIP, E5, ChromaDB, Ollama) 없이 테스트 가능하도록 구성한다.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from PIL import Image


# ─────────────────────────────────────────────
# 이미지 / 파일 Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def sample_image(tmp_path):
    """224x224 RGB 테스트 PNG 이미지 생성"""
    img = Image.new("RGB", (224, 224), color=(128, 128, 128))
    img_path = tmp_path / "test_drawing.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_images(tmp_path):
    """여러 장의 테스트 이미지 생성"""
    paths = []
    for i in range(3):
        img = Image.new("RGB", (224, 224), color=(100 + i * 50, 100, 100))
        img_path = tmp_path / f"drawing_{i}.png"
        img.save(img_path)
        paths.append(img_path)
    return paths


@pytest.fixture
def tmp_records_file(tmp_path):
    """임시 records.json 파일"""
    records_file = tmp_path / "records.json"
    records_file.write_text("{}", encoding="utf-8")
    return records_file


# ─────────────────────────────────────────────
# DXF Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def sample_dxf(tmp_path):
    """테스트용 간단한 DXF 파일 생성"""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0))
    msp.add_line((10, 0), (10, 5))
    msp.add_circle((5, 5), radius=3)
    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))
    return dxf_path


# ─────────────────────────────────────────────
# Mock Embedder Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_image_embedder():
    """OpenCLIP 이미지 임베더 mock (768차원 벡터 반환)"""
    embedder = MagicMock()
    embedder.embed_image.return_value = np.random.randn(768).astype(np.float32)
    embedder.embed_text.return_value = np.random.randn(768).astype(np.float32)
    embedder.embed_images_batch.return_value = [
        np.random.randn(768).astype(np.float32) for _ in range(3)
    ]
    return embedder


@pytest.fixture
def mock_text_embedder():
    """E5 텍스트 임베더 mock (384차원 벡터 반환)"""
    embedder = MagicMock()
    embedder.embed.return_value = np.random.randn(384).astype(np.float32)
    embedder.embed_passage.return_value = np.random.randn(384).astype(np.float32)
    embedder.embed_batch.return_value = [
        np.random.randn(384).astype(np.float32) for _ in range(3)
    ]
    return embedder


# ─────────────────────────────────────────────
# Mock VectorStore Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_chroma_collection():
    """ChromaDB 컬렉션 mock"""
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        "ids": [["id1", "id2", "id3"]],
        "distances": [[0.1, 0.3, 0.5]],
        "metadatas": [[
            {"file_path": "/data/d1.png", "category": "Gears"},
            {"file_path": "/data/d2.png", "category": "Shafts"},
            {"file_path": "/data/d3.png", "category": "Bearings"},
        ]],
    }
    return collection


# ─────────────────────────────────────────────
# Mock LLM Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """Ollama LLM mock"""
    llm = MagicMock()
    llm.describe_drawing.return_value = "This is a gear drawing."
    llm.classify_drawing.return_value = '{"category": "Gears", "confidence": "high"}'
    llm.answer_question.return_value = "The gear has 20 teeth."
    llm.check_health_sync.return_value = True
    return llm


@pytest.fixture
def mock_ollama_response():
    """정상 Ollama API 응답"""
    return {
        "response": "This is a test response.",
        "model": "qwen3.5:9b",
        "done": True,
    }


# ─────────────────────────────────────────────
# Mock Classifier Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_classifier():
    """YOLO-cls 분류기 mock"""
    from core.classifier import ClassificationResult

    classifier = MagicMock()
    classifier.classify.return_value = ClassificationResult(
        category="Shafts",
        confidence=0.92,
        top_k=[
            ("Shafts", 0.92),
            ("Linear_Bushings", 0.04),
            ("Gears", 0.02),
            ("Pulleys_and_Idlers", 0.01),
            ("Couplings", 0.005),
        ],
        needs_review=False,
        model_name="yolo_cls_best.pt",
    )
    classifier.classify_batch.return_value = [
        ClassificationResult(
            category="Shafts",
            confidence=0.92,
            top_k=[("Shafts", 0.92)],
            needs_review=False,
            model_name="yolo_cls_best.pt",
        ),
        ClassificationResult(
            category="Gears",
            confidence=0.85,
            top_k=[("Gears", 0.85)],
            needs_review=False,
            model_name="yolo_cls_best.pt",
        ),
    ]
    classifier.class_names = ["Shafts", "Gears", "Linear_Bushings", "Pulleys_and_Idlers"]
    classifier.num_classes = 4
    classifier.check_health.return_value = (True, "YOLO-cls 정상 (4클래스, yolo_cls_best.pt)")
    classifier.model_path = Path("models/yolo_cls_best.pt")
    return classifier


# ─────────────────────────────────────────────
# Mock Detector Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_detector():
    """YOLO-det 탐지기 mock"""
    from core.detector import DetectionResult, DetectedRegion

    detector = MagicMock()

    # detect() 기본 반환값: title_block 1개 + dimension_area 1개
    detector.detect.return_value = DetectionResult(
        regions=[
            DetectedRegion(
                class_name="title_block",
                confidence=0.92,
                bbox=(600, 700, 1000, 900),
                bbox_normalized=(0.75, 0.78, 1.0, 1.0),
            ),
            DetectedRegion(
                class_name="dimension_area",
                confidence=0.85,
                bbox=(100, 100, 500, 500),
                bbox_normalized=(0.125, 0.11, 0.625, 0.56),
            ),
        ],
        image_size=(1000, 900),
        model_name="yolo_det_best.pt",
    )

    # crop_region() 반환값: 400x200 RGB 이미지
    detector.crop_region.return_value = Image.new("RGB", (400, 200), color=(200, 200, 200))

    # Properties
    detector.class_names = ["title_block", "dimension_area", "parts_table"]
    detector.num_classes = 3
    detector.check_health.return_value = (True, "YOLO-det 정상 (3클래스, yolo_det_best.pt)")
    detector.model_path = Path("models/yolo_det_best.pt")

    return detector


# ─────────────────────────────────────────────
# Mock GNN Embedder Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_gnn_embedder():
    """GNN 구조 임베더 mock (256차원 벡터 반환)"""
    embedder = MagicMock()
    embedder.embed_dxf.return_value = np.random.randn(256).astype(np.float32)
    embedder.embed_dxf_batch.return_value = [
        np.random.randn(256).astype(np.float32) for _ in range(3)
    ]
    return embedder


# ─────────────────────────────────────────────
# Phase 4: AnalysisContext Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def sample_analysis_context():
    """샘플 AnalysisContext (YOLO + OCR 전체 필드)"""
    from core.llm import AnalysisContext
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

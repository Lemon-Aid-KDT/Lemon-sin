"""
CAD Vision REST API 테스트.

FastAPI TestClient로 모든 엔드포인트를 테스트한다.
Pipeline은 mock으로 대체하여 ML 모델 로딩 없이 빠르게 실행.
"""

import io
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Pipeline mock을 주입하여 앱을 import ──

@dataclass
class _MockRecord:
    drawing_id: str = "test-id-001"
    file_path: str = "/tmp/test.png"
    file_name: str = "test.png"
    ocr_text: str = "M5 bolt"
    part_numbers: list = field(default_factory=lambda: ["P001"])
    dimensions: list = field(default_factory=lambda: ["M5"])
    materials: list = field(default_factory=lambda: ["SUS304"])
    category: str = "Shafts"
    description: str = "Test drawing"
    metadata: dict = field(default_factory=dict)
    yolo_confidence: float = 0.95
    yolo_needs_review: bool = False
    yolo_top_k: list = field(default_factory=list)
    detected_regions: list = field(default_factory=list)
    title_block_data: dict = field(default_factory=dict)
    parts_table_data: dict = field(default_factory=dict)
    detection_enhanced: bool = False
    dxf_path: str = ""
    similar_drawings: list = field(default_factory=lambda: [
        {"drawing_id": "similar-001", "score": 0.92, "file_name": "similar.png", "file_path": ""}
    ])


@dataclass
class _MockSearchResult:
    drawing_id: str = "result-001"
    score: float = 0.85
    distance: float = 0.15
    metadata: dict = field(default_factory=lambda: {
        "file_path": "/tmp/result.png",
        "file_name": "result.png",
        "category": "Gears",
    })


@pytest.fixture
def mock_pipeline():
    """Pipeline mock."""
    pipeline = MagicMock()
    pipeline.register_drawing.return_value = _MockRecord()
    pipeline.search_by_text.return_value = [_MockSearchResult()]
    pipeline.search_by_image.return_value = [_MockSearchResult()]
    pipeline.search_by_dxf.return_value = [_MockSearchResult()]
    pipeline.get_record.return_value = _MockRecord()
    pipeline.get_all_records.return_value = [_MockRecord(), _MockRecord(drawing_id="test-id-002")]
    pipeline.delete_drawing.return_value = True
    pipeline.describe.return_value = "This is a shaft drawing."
    pipeline.ask.return_value = "The material is SUS304."
    pipeline.get_stats.return_value = {
        "total_drawings": 100,
        "vector_store": {
            "image_collection_count": 95,
            "text_collection_count": 100,
            "gnn_collection_count": 90,
            "persist_dir": "data/vector_store",
        },
        "categories": ["Shafts", "Gears"],
        "ollama_healthy": True,
        "yolo_classifier": {"enabled": True, "healthy": True},
        "yolo_detector": {"enabled": True, "healthy": True},
        "gnn_embedder": {"enabled": True, "weight": 0.3},
    }
    return pipeline


@pytest.fixture
def client(mock_pipeline):
    """FastAPI TestClient with mocked pipeline."""
    with patch("app.api.main.get_pipeline", return_value=mock_pipeline):
        from app.api.main import app
        yield TestClient(app)


# ── 등록 테스트 ──


class TestRegister:
    def test_register_drawing(self, client, mock_pipeline):
        file_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        response = client.post(
            "/api/v1/drawings/register",
            files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["drawing_id"] == "test-id-001"
        assert data["category"] == "Shafts"
        assert len(data["similar_drawings"]) == 1
        assert data["similar_drawings"][0]["score"] == 0.92

    def test_register_with_category(self, client, mock_pipeline):
        mock_pipeline.register_drawing.reset_mock()
        response = client.post(
            "/api/v1/drawings/register",
            files={"file": ("test.png", io.BytesIO(b"\x89PNG" + b"\x00" * 100), "image/png")},
            params={"category": "Gears"},
        )
        assert response.status_code == 200
        mock_pipeline.register_drawing.assert_called_once()
        call_kwargs = mock_pipeline.register_drawing.call_args
        assert call_kwargs.kwargs.get("category") == "Gears" or call_kwargs[1].get("category") == "Gears"


# ── 검색 테스트 ──


class TestSearch:
    def test_search_by_text(self, client):
        response = client.post(
            "/api/v1/drawings/search/text",
            json={"query": "shaft", "top_k": 5},
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["drawing_id"] == "result-001"
        assert results[0]["score"] == 0.85

    def test_search_by_image(self, client):
        response = client.post(
            "/api/v1/drawings/search/image",
            files={"file": ("test.png", io.BytesIO(b"\x89PNG" + b"\x00" * 100), "image/png")},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_search_by_dxf(self, client):
        response = client.post(
            "/api/v1/drawings/search/dxf",
            files={"file": ("test.dxf", io.BytesIO(b"0\nSECTION\n"), "application/octet-stream")},
        )
        assert response.status_code == 200


# ── 조회/삭제 테스트 ──


class TestCRUD:
    def test_get_drawing(self, client):
        response = client.get("/api/v1/drawings/test-id-001")
        assert response.status_code == 200
        assert response.json()["drawing_id"] == "test-id-001"

    def test_get_drawing_not_found(self, client, mock_pipeline):
        mock_pipeline.get_record.return_value = None
        response = client.get("/api/v1/drawings/nonexistent")
        assert response.status_code == 404

    def test_list_drawings(self, client):
        response = client.get("/api/v1/drawings", params={"page": 1, "page_size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert len(data["items"]) == 2

    def test_list_drawings_pagination(self, client):
        response = client.get("/api/v1/drawings", params={"page": 1, "page_size": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

    def test_delete_drawing(self, client):
        response = client.delete("/api/v1/drawings/test-id-001")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_drawing_not_found(self, client, mock_pipeline):
        mock_pipeline.delete_drawing.return_value = False
        response = client.delete("/api/v1/drawings/nonexistent")
        assert response.status_code == 404


# ── LLM 분석 테스트 ──


class TestLLM:
    def test_describe_drawing(self, client):
        response = client.post("/api/v1/drawings/test-id-001/describe")
        assert response.status_code == 200
        data = response.json()
        assert data["drawing_id"] == "test-id-001"
        assert "shaft" in data["description"].lower()

    def test_ask_drawing(self, client):
        response = client.post(
            "/api/v1/drawings/test-id-001/ask",
            json={"question": "What is the material?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is the material?"
        assert "SUS304" in data["answer"]

    def test_describe_not_found(self, client, mock_pipeline):
        mock_pipeline.get_record.return_value = None
        response = client.post("/api/v1/drawings/nonexistent/describe")
        assert response.status_code == 404


# ── 통계 테스트 ──


class TestStats:
    def test_get_stats(self, client):
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_drawings"] == 100
        assert data["gnn_enabled"] is True
        assert "Shafts" in data["categories"]


# ── CORS 테스트 ──


class TestCORS:
    def test_cors_headers(self, client):
        response = client.options(
            "/api/v1/stats",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # allow_origins=["*"] + allow_credentials=True → origin echo
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert allow_origin in ("*", "http://localhost:3000")

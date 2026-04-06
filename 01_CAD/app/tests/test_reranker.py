"""Reranker (Cross-Encoder) 테스트"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from core.reranker import CrossEncoderReranker
from core.vector_store import SearchResult


# ── Fixtures ──

def _make_result(drawing_id: str, score: float, category: str = "Shafts",
                 ocr_text: str = "S45C shaft") -> SearchResult:
    return SearchResult(
        drawing_id=drawing_id,
        file_path=f"/data/{drawing_id}.png",
        distance=1.0 - score,
        score=score,
        metadata={
            "file_name": f"{drawing_id}.png",
            "category": category,
            "ocr_text": ocr_text,
            "part_numbers": "[]",
        },
    )


@pytest.fixture
def mock_results() -> list[SearchResult]:
    return [
        _make_result("a", 0.9, "Shafts", "S45C shaft 10mm"),
        _make_result("b", 0.8, "Bearings", "SUJ2 bearing"),
        _make_result("c", 0.7, "Shafts", "SUS304 shaft 20mm"),
        _make_result("d", 0.6, "Rollers", "roller conveyor"),
        _make_result("e", 0.5, "Shafts", "S45C rotary shaft"),
    ]


@pytest.fixture
def mock_ce_scores():
    """Cross-encoder가 c(shaft 20mm)를 1위로 올리는 점수"""
    return np.array([0.3, 0.1, 0.9, 0.05, 0.8])  # c가 0.9로 최고


# ── Tests ──


class TestCrossEncoderReranker:
    """Reranker 기본 동작"""

    def test_empty_results(self):
        reranker = CrossEncoderReranker()
        assert reranker.rerank("query", [], top_k=5) == []

    def test_model_unavailable_returns_original(self, mock_results):
        reranker = CrossEncoderReranker()
        reranker._model = None  # 강제 비활성
        # _init_model도 None 반환하도록
        with patch.object(reranker, '_init_model'):
            result = reranker.rerank("shaft", mock_results, top_k=3)
        assert len(result) == 3
        # 원본 순서 유지
        assert result[0].drawing_id == "a"

    def test_rerank_changes_order(self, mock_results, mock_ce_scores):
        reranker = CrossEncoderReranker(reranker_weight=0.7)
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_ce_scores
        reranker._model = mock_model

        result = reranker.rerank("20mm shaft", mock_results, top_k=5)

        # c (ce=0.9)가 a (ce=0.3)보다 위로 올라와야 함
        ids = [r.drawing_id for r in result]
        assert ids.index("c") < ids.index("b")
        assert ids.index("c") < ids.index("d")

    def test_rerank_top_k(self, mock_results, mock_ce_scores):
        reranker = CrossEncoderReranker(reranker_weight=0.7)
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_ce_scores
        reranker._model = mock_model

        result = reranker.rerank("shaft", mock_results, top_k=2)
        assert len(result) == 2

    def test_score_blending(self, mock_results):
        """blended = 0.7 × reranker + 0.3 × hybrid"""
        reranker = CrossEncoderReranker(reranker_weight=0.7)
        mock_model = MagicMock()
        # 모두 동일한 ce score → hybrid 순서 유지
        mock_model.predict.return_value = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        reranker._model = mock_model

        result = reranker.rerank("query", mock_results, top_k=5)

        # ce_scores 동일 → hybrid score 높은 순 유지
        assert result[0].drawing_id == "a"
        assert result[1].drawing_id == "b"


class TestDocumentTextBuild:
    """_build_document_text 로직"""

    def test_all_fields(self):
        reranker = CrossEncoderReranker()
        r = _make_result("x", 0.8, "Shafts", "S45C shaft 10mm")
        text = reranker._build_document_text(r)
        assert "Shafts" in text
        assert "S45C" in text
        assert "x.png" in text

    def test_empty_metadata(self):
        reranker = CrossEncoderReranker()
        r = SearchResult(
            drawing_id="empty",
            file_path="/data/empty.png",
            distance=0.5,
            score=0.5,
            metadata={},
        )
        text = reranker._build_document_text(r)
        assert text == "unknown drawing"

    def test_long_ocr_truncated(self):
        reranker = CrossEncoderReranker()
        r = _make_result("x", 0.8, ocr_text="A" * 500)
        text = reranker._build_document_text(r)
        # OCR 300자로 잘림
        assert len([c for c in text if c == "A"]) == 300


class TestRerankerIntegration:
    """파이프라인 통합 관련"""

    def test_predict_called_with_pairs(self, mock_results):
        reranker = CrossEncoderReranker()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.5] * len(mock_results))
        reranker._model = mock_model

        reranker.rerank("shaft query", mock_results, top_k=5)

        # predict가 [query, doc] 쌍 리스트로 호출됨
        call_args = mock_model.predict.call_args[0][0]
        assert len(call_args) == 5
        assert call_args[0][0] == "shaft query"

    def test_exception_returns_original(self, mock_results):
        reranker = CrossEncoderReranker()
        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("model error")
        reranker._model = mock_model

        result = reranker.rerank("query", mock_results, top_k=3)
        assert len(result) == 3
        assert result[0].drawing_id == "a"  # 원본 순서

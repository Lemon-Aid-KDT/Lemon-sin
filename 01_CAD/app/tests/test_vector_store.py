"""
VectorStore CRUD 및 에러 핸들링 테스트

ChromaDB mock을 사용하여 외부 의존성 없이 테스트한다.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock

from core.vector_store import VectorStore, SearchResult


@pytest.fixture
def mock_vs(tmp_path):
    """Mock ChromaDB 기반 VectorStore"""
    with patch("core.vector_store.chromadb") as mock_chromadb:
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        img_col = MagicMock()
        img_col.count.return_value = 10
        img_col.name = "drawings_image"
        txt_col = MagicMock()
        txt_col.count.return_value = 10
        txt_col.name = "drawings_text"

        gnn_col = MagicMock()
        gnn_col.count.return_value = 10
        gnn_col.name = "drawings_gnn"

        mock_client.get_or_create_collection.side_effect = [img_col, txt_col, gnn_col]

        vs = VectorStore(persist_dir=str(tmp_path / "vs"))
        vs._image_collection = img_col
        vs._text_collection = txt_col
        vs._gnn_collection = gnn_col
        return vs


class TestAddDrawing:
    """도면 등록 테스트"""

    def test_add_with_both_embeddings(self, mock_vs):
        """이미지 + 텍스트 임베딩 모두 등록"""
        img_emb = np.random.randn(768).astype(np.float32)
        txt_emb = np.random.randn(384).astype(np.float32)

        mock_vs.add_drawing(
            drawing_id="test01",
            image_embedding=img_emb,
            text_embedding=txt_emb,
            metadata={"file_path": "/data/test.png"},
        )

        mock_vs._image_collection.upsert.assert_called_once()
        mock_vs._text_collection.upsert.assert_called_once()

    def test_add_image_only(self, mock_vs):
        """이미지 임베딩만 등록"""
        img_emb = np.random.randn(768).astype(np.float32)
        mock_vs.add_drawing(drawing_id="test02", image_embedding=img_emb)
        mock_vs._image_collection.upsert.assert_called_once()
        mock_vs._text_collection.upsert.assert_not_called()

    def test_add_text_only(self, mock_vs):
        """텍스트 임베딩만 등록"""
        txt_emb = np.random.randn(384).astype(np.float32)
        mock_vs.add_drawing(drawing_id="test03", text_embedding=txt_emb)
        mock_vs._image_collection.upsert.assert_not_called()
        mock_vs._text_collection.upsert.assert_called_once()

    def test_add_empty_metadata(self, mock_vs):
        """빈 메타데이터 처리"""
        img_emb = np.random.randn(768).astype(np.float32)
        mock_vs.add_drawing(drawing_id="test04", image_embedding=img_emb, metadata={})
        # 빈 dict → _placeholder 추가됨
        call_args = mock_vs._image_collection.upsert.call_args
        meta = call_args[1]["metadatas"][0] if "metadatas" in call_args[1] else call_args[0][0]
        assert "_placeholder" in str(meta)

    def test_add_image_error_raises(self, mock_vs):
        """이미지 임베딩 저장 실패 시 예외 발생"""
        mock_vs._image_collection.upsert.side_effect = RuntimeError("DB error")
        with pytest.raises(RuntimeError):
            mock_vs.add_drawing(
                drawing_id="test05",
                image_embedding=np.random.randn(768).astype(np.float32),
            )

    def test_add_text_error_continues(self, mock_vs):
        """텍스트 임베딩 저장 실패 시 경고만 (이미지는 보존)"""
        mock_vs._text_collection.upsert.side_effect = RuntimeError("DB error")
        # 예외 발생 안 함
        mock_vs.add_drawing(
            drawing_id="test06",
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
        )
        mock_vs._image_collection.upsert.assert_called_once()


class TestSearch:
    """검색 테스트"""

    def test_search_by_image(self, mock_vs):
        """이미지 검색"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[
                {"file_path": "/data/d1.png"},
                {"file_path": "/data/d2.png"},
            ]],
        }
        results = mock_vs.search_by_image(np.random.randn(768).astype(np.float32))
        assert len(results) == 2
        assert results[0].score > results[1].score

    def test_search_by_text(self, mock_vs):
        """텍스트 검색"""
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/data/d1.png"}]],
        }
        results = mock_vs.search_by_text(np.random.randn(384).astype(np.float32))
        assert len(results) == 1

    def test_search_empty_collection(self, mock_vs):
        """빈 컬렉션 검색 → 빈 결과"""
        mock_vs._image_collection.count.return_value = 0
        results = mock_vs.search_by_image(np.random.randn(768).astype(np.float32))
        assert results == []

    def test_search_query_error_returns_empty(self, mock_vs):
        """검색 쿼리 오류 → 빈 결과 반환"""
        mock_vs._image_collection.query.side_effect = RuntimeError("Query failed")
        results = mock_vs.search_by_image(np.random.randn(768).astype(np.float32))
        assert results == []


class TestHybridSearch:
    """하이브리드 검색 테스트"""

    def test_hybrid_combines_scores(self, mock_vs):
        """이미지 + 텍스트 점수 결합"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.5]],
            "metadatas": [[{"file_path": "/d1.png"}, {"file_path": "/d2.png"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1", "id3"]],
            "distances": [[0.2, 0.4]],
            "metadatas": [[{"file_path": "/d1.png"}, {"file_path": "/d3.png"}]],
        }

        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
            top_k=5,
        )
        assert len(results) >= 1
        # id1은 두 채널 모두 매칭되므로 가장 높은 점수 예상
        assert results[0].drawing_id == "id1"

    def test_hybrid_image_only(self, mock_vs):
        """이미지만 제공 시 이미지 결과만"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
        )
        assert len(results) == 1

    def test_hybrid_graceful_degradation(self, mock_vs):
        """이미지 채널 실패 시 텍스트만 사용"""
        mock_vs._image_collection.query.side_effect = RuntimeError("Failed")
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
        )
        assert len(results) >= 1


class TestWhereFilter:
    """where_filter (카테고리 필터) 테스트"""

    def test_search_by_image_with_where_filter(self, mock_vs):
        """이미지 검색에 where_filter 전달"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png", "category": "Shafts"}]],
        }
        results = mock_vs.search_by_image(
            np.random.randn(768).astype(np.float32),
            where_filter={"category": "Shafts"},
        )
        assert len(results) == 1
        # where 절이 query에 전달되었는지 확인
        call_kwargs = mock_vs._image_collection.query.call_args[1]
        assert call_kwargs["where"] == {"category": "Shafts"}

    def test_search_by_text_with_where_filter(self, mock_vs):
        """텍스트 검색에 where_filter 전달"""
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png", "category": "Gears"}]],
        }
        results = mock_vs.search_by_text(
            np.random.randn(384).astype(np.float32),
            where_filter={"category": "Gears"},
        )
        assert len(results) == 1
        call_kwargs = mock_vs._text_collection.query.call_args[1]
        assert call_kwargs["where"] == {"category": "Gears"}

    def test_search_without_filter_no_where(self, mock_vs):
        """where_filter=None이면 where 절 없음"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs.search_by_image(np.random.randn(768).astype(np.float32))
        call_kwargs = mock_vs._image_collection.query.call_args[1]
        assert "where" not in call_kwargs

    def test_hybrid_search_with_filter(self, mock_vs):
        """하이브리드 검색에 where_filter 전달"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png", "category": "Bearings_with_Holder"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png", "category": "Bearings_with_Holder"}]],
        }
        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
            where_filter={"category": "Bearings_with_Holder"},
        )
        assert len(results) >= 1
        # 양쪽 모두 where 절이 전달됨
        img_kwargs = mock_vs._image_collection.query.call_args[1]
        txt_kwargs = mock_vs._text_collection.query.call_args[1]
        assert img_kwargs["where"] == {"category": "Bearings_with_Holder"}
        assert txt_kwargs["where"] == {"category": "Bearings_with_Holder"}

    def test_hybrid_search_no_filter(self, mock_vs):
        """하이브리드 검색 필터 없으면 기존 동작"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
        )
        img_kwargs = mock_vs._image_collection.query.call_args[1]
        txt_kwargs = mock_vs._text_collection.query.call_args[1]
        assert "where" not in img_kwargs
        assert "where" not in txt_kwargs


class TestDeleteAndReset:
    """삭제 및 초기화 테스트"""

    def test_delete_drawing(self, mock_vs):
        """도면 삭제"""
        mock_vs.delete_drawing("test01")
        mock_vs._image_collection.delete.assert_called_once_with(ids=["test01"])
        mock_vs._text_collection.delete.assert_called_once_with(ids=["test01"])

    def test_delete_partial_error(self, mock_vs):
        """이미지 삭제 실패해도 텍스트 삭제 진행"""
        mock_vs._image_collection.delete.side_effect = RuntimeError("Delete failed")
        mock_vs.delete_drawing("test01")  # 예외 발생 안 함
        mock_vs._text_collection.delete.assert_called_once()

    def test_get_stats(self, mock_vs):
        """통계 조회"""
        stats = mock_vs.get_stats()
        assert "image_collection_count" in stats
        assert "text_collection_count" in stats
        assert stats["image_collection_count"] == 10


class TestParseResults:
    """검색 결과 파싱 테스트"""

    def test_parse_normal_results(self):
        """정상 결과 파싱"""
        raw = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[
                {"file_path": "/data/d1.png"},
                {"file_path": "/data/d2.png"},
            ]],
        }
        results = VectorStore._parse_results(raw)
        assert len(results) == 2
        assert results[0].drawing_id == "id1"
        assert results[0].score == pytest.approx(0.9, abs=0.01)

    def test_parse_empty_results(self):
        """빈 결과 파싱"""
        raw = {"ids": [[]], "distances": [[]], "metadatas": [[]]}
        results = VectorStore._parse_results(raw)
        assert results == []

    def test_parse_none_metadata(self):
        """None 메타데이터 처리"""
        raw = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[None]],
        }
        results = VectorStore._parse_results(raw)
        assert len(results) == 1
        assert results[0].metadata == {}


class TestGNNCollection:
    """GNN 컬렉션 테스트"""

    def test_add_with_gnn_embedding(self, mock_vs):
        """GNN 임베딩 등록"""
        gnn_emb = np.random.randn(256).astype(np.float32)
        mock_vs.add_drawing(
            drawing_id="gnn01",
            gnn_embedding=gnn_emb,
            metadata={"file_path": "/data/test.dxf"},
        )
        mock_vs._gnn_collection.upsert.assert_called_once()
        mock_vs._image_collection.upsert.assert_not_called()
        mock_vs._text_collection.upsert.assert_not_called()

    def test_add_all_three_embeddings(self, mock_vs):
        """이미지 + 텍스트 + GNN 임베딩 모두 등록"""
        mock_vs.add_drawing(
            drawing_id="gnn02",
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
            gnn_embedding=np.random.randn(256).astype(np.float32),
        )
        mock_vs._image_collection.upsert.assert_called_once()
        mock_vs._text_collection.upsert.assert_called_once()
        mock_vs._gnn_collection.upsert.assert_called_once()

    def test_gnn_error_continues(self, mock_vs):
        """GNN 임베딩 저장 실패 시 경고만"""
        mock_vs._gnn_collection.upsert.side_effect = RuntimeError("DB error")
        mock_vs.add_drawing(
            drawing_id="gnn03",
            image_embedding=np.random.randn(768).astype(np.float32),
            gnn_embedding=np.random.randn(256).astype(np.float32),
        )
        mock_vs._image_collection.upsert.assert_called_once()

    def test_search_by_gnn(self, mock_vs):
        """GNN 검색"""
        mock_vs._gnn_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[
                {"file_path": "/data/d1.dxf"},
                {"file_path": "/data/d2.dxf"},
            ]],
        }
        results = mock_vs.search_by_gnn(np.random.randn(256).astype(np.float32))
        assert len(results) == 2
        assert results[0].score > results[1].score

    def test_search_by_gnn_empty_collection(self, mock_vs):
        """빈 GNN 컬렉션 검색"""
        mock_vs._gnn_collection.count.return_value = 0
        results = mock_vs.search_by_gnn(np.random.randn(256).astype(np.float32))
        assert results == []

    def test_delete_includes_gnn(self, mock_vs):
        """삭제 시 GNN 컬렉션도 포함"""
        mock_vs.delete_drawing("gnn04")
        mock_vs._gnn_collection.delete.assert_called_once_with(ids=["gnn04"])

    def test_get_stats_includes_gnn(self, mock_vs):
        """통계에 GNN 컬렉션 포함"""
        stats = mock_vs.get_stats()
        assert "gnn_collection_count" in stats
        assert stats["gnn_collection_count"] == 10


class TestHybridSearch3Channel:
    """3채널 하이브리드 검색 테스트"""

    def test_hybrid_with_gnn(self, mock_vs):
        """이미지 + 텍스트 + GNN 3채널 결합"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs._gnn_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.15]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
            gnn_embedding=np.random.randn(256).astype(np.float32),
            image_weight=0.1,
            text_weight=0.6,
            gnn_weight=0.3,
        )
        assert len(results) == 1
        assert results[0].score > 0

    def test_hybrid_gnn_weight_zero_skips(self, mock_vs):
        """gnn_weight=0이면 GNN 채널 스킵"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
            gnn_embedding=np.random.randn(256).astype(np.float32),
            gnn_weight=0.0,
        )
        mock_vs._gnn_collection.query.assert_not_called()

    def test_hybrid_backward_compatible(self, mock_vs):
        """기존 2채널 호출과 하위 호환"""
        mock_vs._image_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.1]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        mock_vs._text_collection.query.return_value = {
            "ids": [["id1"]],
            "distances": [[0.2]],
            "metadatas": [[{"file_path": "/d1.png"}]],
        }
        # gnn_embedding 미전달 (기존 호출 패턴)
        results = mock_vs.hybrid_search(
            image_embedding=np.random.randn(768).astype(np.float32),
            text_embedding=np.random.randn(384).astype(np.float32),
        )
        assert len(results) >= 1
        mock_vs._gnn_collection.query.assert_not_called()

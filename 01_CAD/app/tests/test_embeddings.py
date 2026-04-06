"""
임베딩 모듈 유닛 테스트

E5 prefix 로직, 디바이스 선택 등 순수 함수 테스트 + mock 기반 통합 테스트
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from core.embeddings import TextEmbedder, ImageEmbedder


class TestE5Prefix:
    """E5 모델 prefix 로직 테스트"""

    def test_query_prefix_e5(self):
        """E5 모델에서 query prefix 추가"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        result = embedder._add_prefix("기어 부품", "query")
        assert result == "query: 기어 부품"

    def test_passage_prefix_e5(self):
        """E5 모델에서 passage prefix 추가"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        result = embedder._add_prefix("기어 부품 OCR 텍스트", "passage")
        assert result == "passage: 기어 부품 OCR 텍스트"

    def test_no_prefix_non_e5(self):
        """비-E5 모델에서 prefix 미적용"""
        embedder = TextEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
        result = embedder._add_prefix("기어 부품", "query")
        assert result == "기어 부품"

    def test_skip_existing_query_prefix(self):
        """이미 query prefix가 있으면 스킵"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        result = embedder._add_prefix("query: 기어 부품", "query")
        assert result == "query: 기어 부품"

    def test_skip_existing_passage_prefix(self):
        """이미 passage prefix가 있으면 스킵"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        result = embedder._add_prefix("passage: 기어 부품", "passage")
        assert result == "passage: 기어 부품"

    def test_e5_large_model(self):
        """E5 large 모델에서도 prefix 적용"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-large")
        assert embedder._needs_prefix is True

    def test_e5_base_model(self):
        """E5 base 모델에서도 prefix 적용"""
        embedder = TextEmbedder(model_name="intfloat/e5-base")
        assert embedder._needs_prefix is True

    def test_non_e5_no_prefix(self):
        """일반 모델에서 prefix 미적용"""
        embedder = TextEmbedder(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        assert embedder._needs_prefix is False

    def test_empty_text_with_prefix(self):
        """빈 텍스트에 prefix 추가"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        result = embedder._add_prefix("", "query")
        assert result == "query: "


class TestSelectDevice:
    """디바이스 선택 테스트"""

    @patch("torch.cuda.is_available", return_value=True)
    def test_cuda_available(self, mock_cuda):
        """CUDA 사용 가능"""
        assert ImageEmbedder._select_device() == "cuda"

    @patch("torch.cuda.is_available", return_value=False)
    @patch("torch.backends.mps.is_available", return_value=True)
    def test_mps_available(self, mock_mps, mock_cuda):
        """MPS (Apple Silicon) 사용 가능"""
        assert ImageEmbedder._select_device() == "mps"

    @patch("torch.cuda.is_available", return_value=False)
    @patch("torch.backends.mps.is_available", return_value=False)
    def test_cpu_fallback(self, mock_mps, mock_cuda):
        """CPU 폴백"""
        assert ImageEmbedder._select_device() == "cpu"


class TestTextEmbedderMock:
    """TextEmbedder mock 기반 테스트"""

    def test_embed_calls_encode(self):
        """embed()가 model.encode()를 호출하는지 검증"""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(384).astype(np.float32)
        mock_model.get_sentence_embedding_dimension.return_value = 384

        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        embedder._model = mock_model  # 직접 주입

        result = embedder.embed("기어 부품")
        assert result.shape == (384,)
        mock_model.encode.assert_called_once()

    def test_embed_passage_uses_passage_prefix(self):
        """embed_passage()가 passage prefix를 사용하는지 검증"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(384).astype(np.float32)
        embedder._model = mock_model

        embedder.embed_passage("기어 부품 텍스트")
        call_args = mock_model.encode.call_args
        assert call_args[0][0].startswith("passage: ")

    def test_embed_query_uses_query_prefix(self):
        """embed()가 query prefix를 사용하는지 검증"""
        embedder = TextEmbedder(model_name="intfloat/multilingual-e5-small")
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(384).astype(np.float32)
        embedder._model = mock_model

        embedder.embed("기어 검색")
        call_args = mock_model.encode.call_args
        assert call_args[0][0].startswith("query: ")

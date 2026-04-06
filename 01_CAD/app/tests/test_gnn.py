"""
GNN 모듈 유닛 테스트

DXF 파싱, 그래프 빌드, GIN 인코더, GNN 임베더의 기능을 테스트한다.
torch-geometric mock 기반으로 외부 의존성 없이 테스트 가능하도록 구성한다.
"""

import math
import pytest
import numpy as np
import torch
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from core.gnn import (
    EntityInfo,
    BBox,
    DXFGraphBuilder,
    NODE_FEATURE_DIM,
    ENTITY_TYPE_MAP,
)

# torch-geometric은 선택적 의존성
_has_pyg = False
try:
    import torch_geometric
    _has_pyg = True
except ImportError:
    pass

requires_pyg = pytest.mark.skipif(not _has_pyg, reason="torch-geometric not installed")


# ─────────────────────────────────────────────
# DXFGraphBuilder 테스트
# ─────────────────────────────────────────────

class TestEntityToFeatures:
    """엔티티 → 특성 벡터 변환 테스트"""

    def setup_method(self):
        self.builder = DXFGraphBuilder()
        self.bbox = BBox(min_x=0, min_y=0, max_x=100, max_y=100)

    def test_line_features_shape(self):
        """LINE 엔티티 특성 벡터가 14-dim인지 확인"""
        entity = EntityInfo(
            entity_type="LINE",
            centroid=(50.0, 50.0),
            size=100.0,
            angle=0.5,
            endpoints=[(0, 0), (100, 100)],
        )
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features.shape == (NODE_FEATURE_DIM,)
        assert features.dtype == np.float32

    def test_line_onehot(self):
        """LINE 엔티티의 one-hot 인코딩"""
        entity = EntityInfo(entity_type="LINE", centroid=(50, 50), size=10)
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features[ENTITY_TYPE_MAP["LINE"]] == 1.0
        assert features[ENTITY_TYPE_MAP["CIRCLE"]] == 0.0

    def test_circle_onehot(self):
        """CIRCLE 엔티티의 one-hot 인코딩"""
        entity = EntityInfo(entity_type="CIRCLE", centroid=(50, 50), size=20)
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features[ENTITY_TYPE_MAP["CIRCLE"]] == 1.0
        assert features[ENTITY_TYPE_MAP["LINE"]] == 0.0

    def test_normalized_centroid(self):
        """중심 좌표가 [0, 1]로 정규화되는지 확인"""
        entity = EntityInfo(entity_type="LINE", centroid=(25, 75), size=10)
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features[8] == pytest.approx(0.25, abs=0.01)  # cx
        assert features[9] == pytest.approx(0.75, abs=0.01)  # cy

    def test_size_normalization(self):
        """크기가 정규화되는지 확인"""
        entity = EntityInfo(entity_type="CIRCLE", centroid=(50, 50), size=50)
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features[10] == pytest.approx(0.5, abs=0.01)

    def test_layer_hash(self):
        """레이어 해시가 [0, 1] 범위인지 확인"""
        entity = EntityInfo(entity_type="LINE", centroid=(50, 50), size=10, layer="Dimension")
        features = self.builder._entity_to_features(entity, self.bbox)
        assert 0.0 <= features[13] <= 1.0

    def test_unknown_entity_type(self):
        """알 수 없는 엔티티 타입 → OTHER"""
        entity = EntityInfo(entity_type="UNKNOWN_TYPE", centroid=(50, 50), size=10)
        features = self.builder._entity_to_features(entity, self.bbox)
        assert features[ENTITY_TYPE_MAP["OTHER"]] == 1.0


class TestBuildEdges:
    """엣지 구성 테스트"""

    def setup_method(self):
        self.builder = DXFGraphBuilder(k_neighbors=2)

    def test_knn_edges_created(self):
        """k-NN 엣지가 생성되는지 확인"""
        entities = [
            EntityInfo(entity_type="LINE", centroid=(0, 0), size=1),
            EntityInfo(entity_type="LINE", centroid=(1, 0), size=1),
            EntityInfo(entity_type="LINE", centroid=(10, 10), size=1),
        ]
        bbox = BBox(0, 0, 10, 10)
        edge_index, edge_attr = self.builder._build_edges(entities, bbox)
        assert edge_index.shape[0] == 2
        assert edge_index.shape[1] > 0
        # k-NN 엣지: is_knn=1
        assert any(edge_attr[:, 1] == 1.0)

    def test_geometric_edges_endpoint(self):
        """endpoint 연결 엣지가 생성되는지 확인"""
        builder = DXFGraphBuilder(k_neighbors=2, endpoint_tolerance=0.05)
        entities = [
            EntityInfo(entity_type="LINE", centroid=(0, 0), size=1,
                       endpoints=[(0, 0), (0.5, 0.5)]),
            EntityInfo(entity_type="LINE", centroid=(0.5, 0.5), size=1,
                       endpoints=[(0.5, 0.5), (1, 1)]),
        ]
        bbox = BBox(0, 0, 1, 1)
        edge_index, edge_attr = builder._build_edges(entities, bbox)
        # 기하학적 엣지 존재: is_geometric=1
        assert any(edge_attr[:, 2] == 1.0)

    def test_single_entity_no_edges(self):
        """엔티티 1개 → 엣지 없음"""
        entities = [EntityInfo(entity_type="LINE", centroid=(0, 0), size=1)]
        bbox = BBox(0, 0, 1, 1)
        edge_index, edge_attr = self.builder._build_edges(entities, bbox)
        assert edge_index.shape[1] == 0

    def test_edge_attr_shape(self):
        """엣지 속성이 3-dim인지 확인"""
        entities = [
            EntityInfo(entity_type="LINE", centroid=(0, 0), size=1),
            EntityInfo(entity_type="CIRCLE", centroid=(1, 1), size=2),
        ]
        bbox = BBox(0, 0, 1, 1)
        edge_index, edge_attr = self.builder._build_edges(entities, bbox)
        if edge_attr.shape[0] > 0:
            assert edge_attr.shape[1] == 3


@requires_pyg
class TestBuildGraph:
    """그래프 빌드 테스트"""

    @patch("core.gnn.DXFGraphBuilder.parse_dxf")
    def test_build_graph_normal(self, mock_parse):
        """정상 엔티티 → 그래프 생성"""
        mock_parse.return_value = [
            EntityInfo(entity_type="LINE", centroid=(0, 0), size=10,
                       endpoints=[(0, 0), (10, 0)]),
            EntityInfo(entity_type="CIRCLE", centroid=(5, 5), size=5),
            EntityInfo(entity_type="ARC", centroid=(8, 2), size=3),
        ]
        builder = DXFGraphBuilder()
        graph = builder.build_graph("dummy.dxf")
        assert graph.x.shape == (3, NODE_FEATURE_DIM)
        assert graph.edge_index.shape[0] == 2

    @patch("core.gnn.DXFGraphBuilder.parse_dxf")
    def test_build_graph_empty_dxf(self, mock_parse):
        """빈 DXF → 더미 노드 1개 그래프"""
        mock_parse.return_value = []
        builder = DXFGraphBuilder()
        graph = builder.build_graph("empty.dxf")
        assert graph.x.shape == (1, NODE_FEATURE_DIM)
        assert graph.edge_index.shape[1] == 0


@requires_pyg
class TestMaxNodes:
    """max_nodes 제한 테스트"""

    @patch("core.gnn.DXFGraphBuilder.parse_dxf")
    def test_max_nodes_truncation(self, mock_parse):
        """max_nodes 초과 시 크기 순 보존"""
        entities = [
            EntityInfo(entity_type="LINE", centroid=(i, i), size=float(i))
            for i in range(100)
        ]
        mock_parse.return_value = entities
        builder = DXFGraphBuilder(max_nodes=10)
        graph = builder.build_graph("large.dxf")
        assert graph.x.shape[0] == 10


# ─────────────────────────────────────────────
# GINEncoder 테스트
# ─────────────────────────────────────────────

@requires_pyg
class TestGINEncoder:
    """GIN 인코더 테스트"""

    def _get_encoder(self):
        from core.gnn import GINEncoder
        return GINEncoder

    def test_forward_shape(self):
        """출력 shape 확인"""
        GINEncoder = self._get_encoder()
        model = GINEncoder(in_channels=NODE_FEATURE_DIM, hidden_channels=32, out_channels=64, num_layers=2)
        x = torch.randn(5, NODE_FEATURE_DIM)
        edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
        out = model(x, edge_index)
        assert out.shape == (1, 64)

    def test_output_normalized(self):
        """출력이 L2 정규화되는지 확인"""
        GINEncoder = self._get_encoder()
        model = GINEncoder(in_channels=NODE_FEATURE_DIM, hidden_channels=32, out_channels=64, num_layers=2)
        x = torch.randn(10, NODE_FEATURE_DIM)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)
        out = model(x, edge_index)
        norm = torch.norm(out, p=2, dim=-1)
        assert norm.item() == pytest.approx(1.0, abs=0.01)

    def test_single_node_graph(self):
        """노드 1개 그래프 처리 (eval 모드 — BatchNorm은 batch_size=1 불가)"""
        GINEncoder = self._get_encoder()
        model = GINEncoder(in_channels=NODE_FEATURE_DIM, hidden_channels=32, out_channels=64, num_layers=2)
        model.eval()
        x = torch.randn(1, NODE_FEATURE_DIM)
        edge_index = torch.zeros(2, 0, dtype=torch.long)
        out = model(x, edge_index)
        assert out.shape == (1, 64)

    def test_batch_inference(self):
        """배치 추론 시 출력 shape"""
        GINEncoder = self._get_encoder()
        model = GINEncoder(in_channels=NODE_FEATURE_DIM, hidden_channels=32, out_channels=64, num_layers=2)
        # 2개 그래프: 그래프0 (3노드), 그래프1 (2노드)
        x = torch.randn(5, NODE_FEATURE_DIM)
        edge_index = torch.tensor([[0, 1, 3], [1, 2, 4]], dtype=torch.long)
        batch = torch.tensor([0, 0, 0, 1, 1], dtype=torch.long)
        out = model(x, edge_index, batch)
        assert out.shape == (2, 64)


# ─────────────────────────────────────────────
# GNNEmbedder 테스트
# ─────────────────────────────────────────────

@requires_pyg
class TestGNNEmbedder:
    """GNN 임베더 테스트"""

    def _get_classes(self):
        from core.gnn import GINEncoder, GNNEmbedder
        return GINEncoder, GNNEmbedder

    def test_lazy_loading(self):
        """모델이 첫 호출 전까지 로드되지 않는지 확인"""
        _, GNNEmbedder = self._get_classes()
        embedder = GNNEmbedder(model_path="nonexistent.pt")
        assert embedder._model is None

    @patch("torch.cuda.is_available", return_value=False)
    @patch("torch.backends.mps.is_available", return_value=False)
    def test_cpu_fallback(self, mock_mps, mock_cuda):
        """디바이스 자동 선택 (CPU 폴백)"""
        _, GNNEmbedder = self._get_classes()
        assert GNNEmbedder._select_device() == "cpu"

    @patch("torch.cuda.is_available", return_value=True)
    def test_cuda_device(self, mock_cuda):
        """CUDA 사용 가능 시 cuda 선택"""
        _, GNNEmbedder = self._get_classes()
        assert GNNEmbedder._select_device() == "cuda"

    @patch("core.gnn.GNNEmbedder._init_model")
    @patch("core.gnn.DXFGraphBuilder.build_graph")
    def test_embed_dxf_returns_ndarray(self, mock_build, mock_init):
        """embed_dxf가 numpy array를 반환하는지 확인"""
        from core.gnn import GINEncoder, GNNEmbedder
        from torch_geometric.data import Data
        mock_graph = Data(
            x=torch.randn(3, NODE_FEATURE_DIM),
            edge_index=torch.tensor([[0, 1], [1, 2]], dtype=torch.long),
            edge_attr=torch.randn(2, 3),
        )
        mock_build.return_value = mock_graph

        GINEncoder, GNNEmbedder = self._get_classes()
        embedder = GNNEmbedder(embedding_dim=64)
        # 수동으로 모델 주입
        embedder._graph_builder = DXFGraphBuilder()
        model = GINEncoder(out_channels=64, hidden_channels=32, num_layers=2)
        model.eval()
        embedder._model = model
        embedder.device = "cpu"

        result = embedder.embed_dxf("test.dxf")
        assert isinstance(result, np.ndarray)
        assert result.shape == (64,)

    def test_model_not_found_warning(self):
        """모델 파일 없을 때 경고 후 랜덤 초기화"""
        _, GNNEmbedder = self._get_classes()
        embedder = GNNEmbedder(model_path="does_not_exist.pt", embedding_dim=64)
        embedder._init_model()
        assert embedder._model is not None  # 랜덤 초기화로 생성됨


class TestDXFParsing:
    """DXF 파싱 엔티티 추출 테스트 (ezdxf mock)"""

    def _make_mock_entity(self, dxf_type, **attrs):
        """간단한 mock DXF 엔티티 생성"""
        entity = MagicMock()
        entity.dxftype.return_value = dxf_type
        dxf_attrs = MagicMock()
        dxf_attrs.layer = attrs.get("layer", "0")

        if dxf_type == "LINE":
            start = MagicMock()
            start.x, start.y = attrs.get("start", (0, 0))
            end = MagicMock()
            end.x, end.y = attrs.get("end", (10, 10))
            dxf_attrs.start = start
            dxf_attrs.end = end
        elif dxf_type == "CIRCLE":
            center = MagicMock()
            center.x, center.y = attrs.get("center", (5, 5))
            dxf_attrs.center = center
            dxf_attrs.radius = attrs.get("radius", 10)
        elif dxf_type == "POINT":
            location = MagicMock()
            location.x, location.y = attrs.get("location", (0, 0))
            dxf_attrs.location = location

        entity.dxf = dxf_attrs
        return entity

    def test_extract_line(self):
        """LINE 엔티티 추출"""
        builder = DXFGraphBuilder()
        entity = self._make_mock_entity("LINE", start=(0, 0), end=(10, 0))
        info = builder._extract_entity(entity)
        assert info is not None
        assert info.entity_type == "LINE"
        assert info.centroid == (5.0, 0.0)
        assert info.size == pytest.approx(10.0, abs=0.01)

    def test_extract_circle(self):
        """CIRCLE 엔티티 추출"""
        builder = DXFGraphBuilder()
        entity = self._make_mock_entity("CIRCLE", center=(5, 5), radius=10)
        info = builder._extract_entity(entity)
        assert info is not None
        assert info.entity_type == "CIRCLE"
        assert info.centroid == (5, 5)
        assert info.size == 20.0  # diameter

    def test_extract_point(self):
        """POINT 엔티티 추출"""
        builder = DXFGraphBuilder()
        entity = self._make_mock_entity("POINT", location=(3, 7))
        info = builder._extract_entity(entity)
        assert info is not None
        assert info.entity_type == "POINT"
        assert info.size == 0.0

    def test_extract_unknown_returns_none(self):
        """알 수 없는 엔티티 → None"""
        builder = DXFGraphBuilder()
        entity = self._make_mock_entity("3DSOLID")
        info = builder._extract_entity(entity)
        assert info is None

    def test_extract_error_returns_none(self):
        """에러 발생 시 None"""
        builder = DXFGraphBuilder()
        entity = MagicMock()
        entity.dxftype.return_value = "LINE"
        entity.dxf.start = None  # AttributeError 유발
        info = builder._extract_entity(entity)
        assert info is None

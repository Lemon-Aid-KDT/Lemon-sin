"""
GNN 기반 DXF 구조 유사도 임베딩 모듈

DXF 파일의 기하학적 엔티티를 그래프로 변환하고,
GIN(Graph Isomorphism Network)으로 고정 차원 임베딩을 생성한다.
ChromaDB 3번째 컬렉션에 저장하여 구조적 유사도 검색에 사용된다.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger

# 엔티티 타입 → one-hot 인덱스
ENTITY_TYPES = ["LINE", "CIRCLE", "ARC", "LWPOLYLINE", "SPLINE", "ELLIPSE", "POINT", "OTHER"]
ENTITY_TYPE_MAP = {t: i for i, t in enumerate(ENTITY_TYPES)}
NUM_ENTITY_TYPES = len(ENTITY_TYPES)
NODE_FEATURE_DIM = NUM_ENTITY_TYPES + 6  # 8 (one-hot) + 2 (cx,cy) + 1 (size) + 1 (angle) + 1 (aspect) + 1 (layer)


@dataclass
class EntityInfo:
    """DXF 엔티티 정보"""
    entity_type: str
    centroid: tuple[float, float]
    size: float
    angle: float = 0.0
    aspect_ratio: float = 1.0
    endpoints: list[tuple[float, float]] = field(default_factory=list)
    layer: str = "0"


@dataclass
class BBox:
    """바운딩 박스"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return max(self.max_x - self.min_x, 1e-8)

    @property
    def height(self) -> float:
        return max(self.max_y - self.min_y, 1e-8)

    @property
    def max_dim(self) -> float:
        return max(self.width, self.height, 1e-8)


class DXFGraphBuilder:
    """DXF 파일을 PyG Data 객체로 변환한다."""

    def __init__(
        self,
        k_neighbors: int = 8,
        endpoint_tolerance: float = 0.01,
        max_nodes: int = 5000,
    ):
        self.k_neighbors = k_neighbors
        self.endpoint_tolerance = endpoint_tolerance
        self.max_nodes = max_nodes

    def parse_dxf(self, dxf_path: str | Path) -> list[EntityInfo]:
        """DXF 파일에서 기하학적 엔티티를 추출한다."""
        import ezdxf

        dxf_path = Path(dxf_path)
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        entities: list[EntityInfo] = []
        for entity in msp:
            info = self._extract_entity(entity)
            if info is not None:
                entities.append(info)

        # max_nodes 제한: 큰 엔티티 우선 보존
        if len(entities) > self.max_nodes:
            entities.sort(key=lambda e: e.size, reverse=True)
            entities = entities[: self.max_nodes]

        return entities

    def _extract_entity(self, entity) -> EntityInfo | None:
        """단일 DXF 엔티티에서 EntityInfo를 추출한다."""
        dxf_type = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "0")

        try:
            if dxf_type == "LINE":
                start = (entity.dxf.start.x, entity.dxf.start.y)
                end = (entity.dxf.end.x, entity.dxf.end.y)
                cx = (start[0] + end[0]) / 2
                cy = (start[1] + end[1]) / 2
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = math.hypot(dx, dy)
                angle = math.atan2(dy, dx) / math.pi
                return EntityInfo(
                    entity_type="LINE",
                    centroid=(cx, cy),
                    size=length,
                    angle=angle,
                    endpoints=[start, end],
                    layer=layer,
                )

            elif dxf_type == "CIRCLE":
                center = (entity.dxf.center.x, entity.dxf.center.y)
                radius = entity.dxf.radius
                return EntityInfo(
                    entity_type="CIRCLE",
                    centroid=center,
                    size=radius * 2,
                    angle=0.0,
                    aspect_ratio=1.0,
                    layer=layer,
                )

            elif dxf_type == "ARC":
                center = (entity.dxf.center.x, entity.dxf.center.y)
                radius = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                mid_angle = (start_angle + end_angle) / 2
                # 호의 양 끝점
                sp = (
                    center[0] + radius * math.cos(start_angle),
                    center[1] + radius * math.sin(start_angle),
                )
                ep = (
                    center[0] + radius * math.cos(end_angle),
                    center[1] + radius * math.sin(end_angle),
                )
                return EntityInfo(
                    entity_type="ARC",
                    centroid=center,
                    size=radius * 2,
                    angle=mid_angle / math.pi,
                    endpoints=[sp, ep],
                    layer=layer,
                )

            elif dxf_type == "LWPOLYLINE":
                points = list(entity.get_points(format="xy"))
                if not points:
                    return None
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                # 둘레 계산
                perimeter = 0.0
                for i in range(len(points) - 1):
                    perimeter += math.hypot(
                        points[i + 1][0] - points[i][0],
                        points[i + 1][1] - points[i][1],
                    )
                if entity.closed and len(points) > 1:
                    perimeter += math.hypot(
                        points[0][0] - points[-1][0],
                        points[0][1] - points[-1][1],
                    )
                w = max(xs) - min(xs) if len(xs) > 1 else 1e-8
                h = max(ys) - min(ys) if len(ys) > 1 else 1e-8
                aspect = w / max(h, 1e-8)
                endpoints = [points[0], points[-1]] if len(points) >= 2 else []
                return EntityInfo(
                    entity_type="LWPOLYLINE",
                    centroid=(cx, cy),
                    size=perimeter,
                    angle=0.0,
                    aspect_ratio=min(aspect, 10.0),
                    endpoints=endpoints,
                    layer=layer,
                )

            elif dxf_type == "SPLINE":
                try:
                    points = list(entity.control_points)
                except Exception:
                    points = []
                if not points:
                    return None
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                # 제어점 간 거리 합
                total_len = 0.0
                for i in range(len(points) - 1):
                    total_len += math.hypot(
                        points[i + 1][0] - points[i][0],
                        points[i + 1][1] - points[i][1],
                    )
                endpoints = [(xs[0], ys[0]), (xs[-1], ys[-1])] if len(points) >= 2 else []
                return EntityInfo(
                    entity_type="SPLINE",
                    centroid=(cx, cy),
                    size=total_len,
                    endpoints=endpoints,
                    layer=layer,
                )

            elif dxf_type == "ELLIPSE":
                center = (entity.dxf.center.x, entity.dxf.center.y)
                major_axis = entity.dxf.major_axis
                ratio = entity.dxf.ratio
                major_len = math.hypot(major_axis.x, major_axis.y)
                angle = math.atan2(major_axis.y, major_axis.x) / math.pi
                return EntityInfo(
                    entity_type="ELLIPSE",
                    centroid=center,
                    size=major_len * 2,
                    angle=angle,
                    aspect_ratio=min(1.0 / max(ratio, 1e-8), 10.0),
                    layer=layer,
                )

            elif dxf_type == "POINT":
                loc = (entity.dxf.location.x, entity.dxf.location.y)
                return EntityInfo(
                    entity_type="POINT",
                    centroid=loc,
                    size=0.0,
                    layer=layer,
                )

            else:
                # INSERT, DIMENSION 등 → OTHER로 처리
                # 바운딩 박스 추출 시도
                return None

        except Exception:
            return None

    def _compute_bbox(self, entities: list[EntityInfo]) -> BBox:
        """엔티티 전체의 바운딩 박스를 계산한다."""
        if not entities:
            return BBox(0, 0, 1, 1)
        xs = [e.centroid[0] for e in entities]
        ys = [e.centroid[1] for e in entities]
        return BBox(
            min_x=min(xs),
            min_y=min(ys),
            max_x=max(xs),
            max_y=max(ys),
        )

    def _entity_to_features(self, entity: EntityInfo, bbox: BBox) -> np.ndarray:
        """엔티티를 14-dim 특성 벡터로 변환한다."""
        features = np.zeros(NODE_FEATURE_DIM, dtype=np.float32)

        # one-hot 엔티티 타입 (0~7)
        type_idx = ENTITY_TYPE_MAP.get(entity.entity_type, ENTITY_TYPE_MAP["OTHER"])
        features[type_idx] = 1.0

        # 정규화 중심 좌표 (8~9)
        features[NUM_ENTITY_TYPES] = (entity.centroid[0] - bbox.min_x) / bbox.width
        features[NUM_ENTITY_TYPES + 1] = (entity.centroid[1] - bbox.min_y) / bbox.height

        # 정규화 크기 (10)
        features[NUM_ENTITY_TYPES + 2] = min(entity.size / bbox.max_dim, 10.0)

        # 각도 (11): [-1, 1]
        features[NUM_ENTITY_TYPES + 3] = np.clip(entity.angle, -1.0, 1.0)

        # 종횡비 (12): [0, 10] → [0, 1]
        features[NUM_ENTITY_TYPES + 4] = min(entity.aspect_ratio / 10.0, 1.0)

        # 레이어 해시 (13): [0, 1]
        features[NUM_ENTITY_TYPES + 5] = (hash(entity.layer) % 8) / 8.0

        return features

    def _build_edges(
        self, entities: list[EntityInfo], bbox: BBox,
    ) -> tuple[np.ndarray, np.ndarray]:
        """k-NN + 기하학적 연결 엣지를 구성한다.

        Returns:
            edge_index: (2, E) int64
            edge_attr: (E, 3) float32 — [distance, is_knn, is_geometric]
        """
        n = len(entities)
        if n <= 1:
            return np.zeros((2, 0), dtype=np.int64), np.zeros((0, 3), dtype=np.float32)

        # 중심점 행렬
        centroids = np.array([e.centroid for e in entities], dtype=np.float32)
        # 정규화
        centroids[:, 0] = (centroids[:, 0] - bbox.min_x) / bbox.width
        centroids[:, 1] = (centroids[:, 1] - bbox.min_y) / bbox.height

        # 거리 행렬
        diff = centroids[:, None, :] - centroids[None, :, :]
        dist_matrix = np.sqrt((diff ** 2).sum(axis=-1))

        edges_src, edges_dst, edges_attr = [], [], []
        k = min(self.k_neighbors, n - 1)

        # k-NN 엣지
        if k > 0:
            for i in range(n):
                neighbors = np.argsort(dist_matrix[i])[1: k + 1]  # 자기 자신 제외
                for j in neighbors:
                    edges_src.append(i)
                    edges_dst.append(j)
                    edges_attr.append([dist_matrix[i, j], 1.0, 0.0])

        # 기하학적 연결 엣지 (endpoint 근접)
        tol = self.endpoint_tolerance
        for i in range(n):
            if not entities[i].endpoints:
                continue
            for j in range(i + 1, n):
                if not entities[j].endpoints:
                    continue
                connected = False
                for ep_i in entities[i].endpoints:
                    for ep_j in entities[j].endpoints:
                        # 정규화 좌표로 비교
                        ni = (
                            (ep_i[0] - bbox.min_x) / bbox.width,
                            (ep_i[1] - bbox.min_y) / bbox.height,
                        )
                        nj = (
                            (ep_j[0] - bbox.min_x) / bbox.width,
                            (ep_j[1] - bbox.min_y) / bbox.height,
                        )
                        if math.hypot(ni[0] - nj[0], ni[1] - nj[1]) < tol:
                            connected = True
                            break
                    if connected:
                        break
                if connected:
                    d = dist_matrix[i, j]
                    # 양방향
                    edges_src.extend([i, j])
                    edges_dst.extend([j, i])
                    edges_attr.extend([[d, 0.0, 1.0], [d, 0.0, 1.0]])

        if not edges_src:
            return np.zeros((2, 0), dtype=np.int64), np.zeros((0, 3), dtype=np.float32)

        edge_index = np.array([edges_src, edges_dst], dtype=np.int64)
        edge_attr = np.array(edges_attr, dtype=np.float32)
        return edge_index, edge_attr

    def build_graph(self, dxf_path: str | Path):
        """DXF 파일을 PyG Data 객체로 변환한다.

        Returns:
            torch_geometric.data.Data with x, edge_index, edge_attr
        """
        from torch_geometric.data import Data

        entities = self.parse_dxf(dxf_path)
        if not entities:
            # 빈 DXF → 단일 더미 노드 그래프
            logger.warning(f"빈 DXF 파일 (엔티티 없음): {dxf_path}")
            return Data(
                x=torch.zeros(1, NODE_FEATURE_DIM),
                edge_index=torch.zeros(2, 0, dtype=torch.long),
                edge_attr=torch.zeros(0, 3),
            )

        # max_nodes 제한: 크기 순 상위 N개 보존
        if len(entities) > self.max_nodes:
            entities = sorted(entities, key=lambda e: e.size, reverse=True)[
                : self.max_nodes
            ]
            logger.info(
                f"엔티티 수 제한 적용: {len(entities)}/{self.max_nodes}"
            )

        bbox = self._compute_bbox(entities)

        # 노드 특성
        node_features = np.stack(
            [self._entity_to_features(e, bbox) for e in entities]
        )

        # 엣지
        edge_index, edge_attr = self._build_edges(entities, bbox)

        return Data(
            x=torch.from_numpy(node_features),
            edge_index=torch.from_numpy(edge_index),
            edge_attr=torch.from_numpy(edge_attr),
        )


class GINEncoder(nn.Module):
    """Graph Isomorphism Network (GIN) 기반 그래프 임베딩 인코더.

    4층 GIN conv + global mean/max pooling → MLP 프로젝션.
    """

    def __init__(
        self,
        in_channels: int = NODE_FEATURE_DIM,
        hidden_channels: int = 128,
        out_channels: int = 256,
        num_layers: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        from torch_geometric.nn import GINConv
        from torch_geometric.nn import global_mean_pool, global_max_pool

        self.num_layers = num_layers
        self.dropout = dropout

        # GIN 레이어
        self.convs = nn.ModuleList()
        self.bns = nn.ModuleList()

        for i in range(num_layers):
            in_ch = in_channels if i == 0 else hidden_channels
            mlp = nn.Sequential(
                nn.Linear(in_ch, hidden_channels),
                nn.ReLU(),
                nn.Linear(hidden_channels, hidden_channels),
            )
            self.convs.append(GINConv(mlp))
            self.bns.append(nn.BatchNorm1d(hidden_channels))

        # 프로젝션 MLP (mean + max concat → out)
        self.projection = nn.Sequential(
            nn.Linear(hidden_channels * 2, hidden_channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels, out_channels),
        )

        self._global_mean_pool = global_mean_pool
        self._global_max_pool = global_max_pool

    def forward(self, x, edge_index, batch=None):
        """
        Args:
            x: (N, in_channels) 노드 특성
            edge_index: (2, E) 엣지 인덱스
            batch: (N,) 배치 인덱스 (None이면 단일 그래프)

        Returns:
            (B, out_channels) L2-normalized 그래프 임베딩
        """
        if batch is None:
            batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)

        for i in range(self.num_layers):
            x = self.convs[i](x, edge_index)
            x = self.bns[i](x)
            x = F.relu(x)
            if i < self.num_layers - 1:
                x = F.dropout(x, p=self.dropout, training=self.training)

        # Global pooling: mean + max concatenation
        x_mean = self._global_mean_pool(x, batch)
        x_max = self._global_max_pool(x, batch)
        x_pool = torch.cat([x_mean, x_max], dim=-1)

        # 프로젝션 + L2 정규화
        out = self.projection(x_pool)
        out = F.normalize(out, p=2, dim=-1)
        return out


class GNNEmbedder:
    """DXF 구조 임베딩 생성기.

    ImageEmbedder와 동일한 lazy-loading 패턴을 따른다.
    """

    def __init__(
        self,
        model_path: str = "",
        embedding_dim: int = 256,
        device: str = "",
        k_neighbors: int = 8,
    ):
        self.model_path = model_path
        self.embedding_dim = embedding_dim
        self.device = device or self._select_device()
        self.k_neighbors = k_neighbors
        self._model: GINEncoder | None = None
        self._graph_builder: DXFGraphBuilder | None = None

    @staticmethod
    def _select_device() -> str:
        """사용 가능한 최적 디바이스를 선택한다."""
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _init_model(self):
        """모델을 지연 로딩한다."""
        if self._model is not None:
            return

        self._graph_builder = DXFGraphBuilder(k_neighbors=self.k_neighbors)

        model = GINEncoder(out_channels=self.embedding_dim)

        if self.model_path and Path(self.model_path).exists():
            try:
                checkpoint = torch.load(
                    self.model_path, map_location=self.device, weights_only=True,
                )
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                model.load_state_dict(state_dict)
                logger.info(f"GNN 모델 로드 완료: {self.model_path}")
            except Exception as e:
                logger.warning(f"GNN 체크포인트 로드 실패 (랜덤 초기화 사용): {e}")
        else:
            logger.info("GNN 학습된 모델 없음 (랜덤 초기화, 학습 필요)")

        model = model.to(self.device)
        model.eval()
        self._model = model

    def embed_dxf(self, dxf_path: str | Path) -> np.ndarray:
        """단일 DXF 파일을 임베딩한다.

        Args:
            dxf_path: DXF 파일 경로

        Returns:
            (embedding_dim,) float32 numpy array
        """
        self._init_model()

        data = self._graph_builder.build_graph(dxf_path)
        data = data.to(self.device)

        with torch.no_grad():
            embedding = self._model(data.x, data.edge_index)

        return embedding.cpu().numpy().flatten()

    def embed_dxf_batch(
        self, dxf_paths: list, batch_size: int = 32,
    ) -> list[np.ndarray]:
        """여러 DXF 파일을 배치 임베딩한다.

        Args:
            dxf_paths: DXF 파일 경로 리스트
            batch_size: 배치 크기

        Returns:
            list of (embedding_dim,) float32 numpy arrays
        """
        self._init_model()
        from torch_geometric.loader import DataLoader

        # 그래프 빌드
        graphs = []
        valid_indices = []
        for i, path in enumerate(dxf_paths):
            try:
                g = self._graph_builder.build_graph(path)
                graphs.append(g)
                valid_indices.append(i)
            except Exception as e:
                logger.warning(f"DXF 그래프 빌드 실패 ({path}): {e}")

        if not graphs:
            return [np.zeros(self.embedding_dim, dtype=np.float32)] * len(dxf_paths)

        # 배치 추론
        loader = DataLoader(graphs, batch_size=batch_size, shuffle=False)
        all_embeddings = []

        with torch.no_grad():
            for batch in loader:
                batch = batch.to(self.device)
                emb = self._model(batch.x, batch.edge_index, batch.batch)
                all_embeddings.append(emb.cpu().numpy())

        embeddings_array = np.concatenate(all_embeddings, axis=0)

        # 실패한 인덱스에 제로 벡터 삽입
        results = [np.zeros(self.embedding_dim, dtype=np.float32)] * len(dxf_paths)
        for idx, valid_idx in enumerate(valid_indices):
            results[valid_idx] = embeddings_array[idx]

        return results

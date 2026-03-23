"""DXF 구조 비교 모듈 테스트"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# EntityInfo를 core.gnn에서 임포트 (torch_geometric 미설치 시 로컬 모의 사용)
try:
    from core.gnn import EntityInfo
except Exception:

    @dataclass
    class EntityInfo:
        """테스트용 EntityInfo 모의 객체"""

        entity_type: str = "LINE"
        centroid: tuple[float, float] = (0.0, 0.0)
        size: float = 1.0
        angle: float = 0.0
        aspect_ratio: float = 1.0
        endpoints: list[tuple[float, float]] = field(default_factory=list)
        layer: str = "0"


from core.dxf_diff import (
    DXFDiffResult,
    EntityMatch,
    _compute_match_score,
    _compute_max_distance,
    _entity_rect,
    compare_dxf,
    render_diff,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_entity(
    entity_type: str = "LINE",
    centroid: tuple[float, float] = (0.0, 0.0),
    size: float = 10.0,
    angle: float = 0.0,
    aspect_ratio: float = 1.0,
    layer: str = "0",
) -> EntityInfo:
    return EntityInfo(
        entity_type=entity_type,
        centroid=centroid,
        size=size,
        angle=angle,
        aspect_ratio=aspect_ratio,
        layer=layer,
    )


# ===========================================================================
# TestCompareDxf
# ===========================================================================


class TestCompareDxf:
    """compare_dxf 함수 테스트"""

    @patch("core.gnn.DXFGraphBuilder")
    def test_identical_entities(self, mock_builder_cls):
        """동일한 엔티티 리스트 비교 시 전부 매칭"""
        entities = [
            _make_entity("LINE", (0, 0), 10.0),
            _make_entity("CIRCLE", (50, 50), 20.0),
        ]
        mock_builder = MagicMock()
        mock_builder.parse_dxf.return_value = list(entities)
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert len(result.matched) == 2
        assert len(result.only_in_a) == 0
        assert len(result.only_in_b) == 0
        assert result.summary["similarity_score"] == 1.0

    @patch("core.gnn.DXFGraphBuilder")
    def test_partial_overlap(self, mock_builder_cls):
        """부분적으로 겹치는 엔티티"""
        entities_a = [
            _make_entity("LINE", (0, 0), 10.0),
            _make_entity("CIRCLE", (100, 100), 5.0),
        ]
        entities_b = [
            _make_entity("LINE", (0, 0), 10.0),
            _make_entity("ARC", (200, 200), 15.0),
        ]
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = [entities_a, entities_b]
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert len(result.matched) == 1
        assert len(result.only_in_a) == 1
        assert len(result.only_in_b) == 1

    @patch("core.gnn.DXFGraphBuilder")
    def test_completely_different(self, mock_builder_cls):
        """완전히 다른 엔티티 (타입이 다르면 매칭 불가)"""
        entities_a = [_make_entity("LINE", (0, 0), 10.0)]
        entities_b = [_make_entity("CIRCLE", (0, 0), 10.0)]
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = [entities_a, entities_b]
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert len(result.matched) == 0
        assert len(result.only_in_a) == 1
        assert len(result.only_in_b) == 1
        assert result.summary["similarity_score"] == 0.0

    @patch("core.gnn.DXFGraphBuilder")
    def test_empty_both(self, mock_builder_cls):
        """양쪽 모두 빈 DXF"""
        mock_builder = MagicMock()
        mock_builder.parse_dxf.return_value = []
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert len(result.matched) == 0
        assert len(result.only_in_a) == 0
        assert len(result.only_in_b) == 0
        assert result.summary["similarity_score"] == 1.0

    @patch("core.gnn.DXFGraphBuilder")
    def test_one_empty(self, mock_builder_cls):
        """한쪽만 비어있는 경우"""
        entities_a = [_make_entity("LINE", (0, 0), 10.0)]
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = [entities_a, []]
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert len(result.matched) == 0
        assert len(result.only_in_a) == 1
        assert len(result.only_in_b) == 0
        assert result.summary["similarity_score"] == 0.0


# ===========================================================================
# TestEntityMatching
# ===========================================================================


class TestEntityMatching:
    """엔티티 매칭 점수 계산 테스트"""

    def test_same_type_same_position(self):
        """동일 타입, 동일 위치 → 점수 1.0"""
        a = _make_entity("LINE", (10, 10), 5.0, angle=0.5)
        b = _make_entity("LINE", (10, 10), 5.0, angle=0.5)
        score = _compute_match_score(a, b, max_dist=100.0)
        assert score == pytest.approx(1.0)

    def test_different_types(self):
        """다른 타입 → 점수 0.0"""
        a = _make_entity("LINE", (10, 10), 5.0)
        b = _make_entity("CIRCLE", (10, 10), 5.0)
        score = _compute_match_score(a, b, max_dist=100.0)
        assert score == 0.0

    def test_same_type_different_position(self):
        """같은 타입, 다른 위치 → 감소된 점수"""
        a = _make_entity("LINE", (0, 0), 5.0)
        b = _make_entity("LINE", (50, 50), 5.0)
        score = _compute_match_score(a, b, max_dist=100.0)
        assert 0.0 < score < 1.0

    def test_threshold_boundary_above(self):
        """임계값 경계 — 0.7 이상이면 매칭됨"""
        a = _make_entity("LINE", (0, 0), 10.0, angle=0.0)
        b = _make_entity("LINE", (5, 5), 10.0, angle=0.0)
        score = _compute_match_score(a, b, max_dist=100.0)
        # 거리 = 7.07, norm_dist = 0.0707, 점수 ≈ 1 - 0.028 = 0.972
        assert score >= 0.7

    def test_threshold_boundary_below(self):
        """임계값 경계 — 매우 먼 거리 → 0.7 미만"""
        a = _make_entity("LINE", (0, 0), 10.0, angle=0.0)
        b = _make_entity("LINE", (90, 90), 2.0, angle=0.5)
        score = _compute_match_score(a, b, max_dist=100.0)
        assert score < 0.7

    def test_score_clamped_at_zero(self):
        """점수가 음수가 되지 않도록 0 클램핑"""
        a = _make_entity("LINE", (0, 0), 1.0, angle=-1.0)
        b = _make_entity("LINE", (100, 100), 100.0, angle=1.0)
        score = _compute_match_score(a, b, max_dist=100.0)
        assert score >= 0.0


# ===========================================================================
# TestLayerDiff
# ===========================================================================


class TestLayerDiff:
    """레이어 비교 테스트"""

    @patch("core.gnn.DXFGraphBuilder")
    def test_layer_added_removed_common(self, mock_builder_cls):
        """추가/제거/공통 레이어 분류"""
        entities_a = [
            _make_entity(layer="Layer1"),
            _make_entity(layer="Layer2"),
            _make_entity(layer="Common"),
        ]
        entities_b = [
            _make_entity(layer="Layer3"),
            _make_entity(layer="Common"),
        ]
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = [entities_a, entities_b]
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert "Common" in result.layer_diff["common"]
        assert "Layer3" in result.layer_diff["added"]
        assert "Layer1" in result.layer_diff["removed"]
        assert "Layer2" in result.layer_diff["removed"]

    @patch("core.gnn.DXFGraphBuilder")
    def test_no_layers_when_empty(self, mock_builder_cls):
        """빈 엔티티 → 빈 레이어"""
        mock_builder = MagicMock()
        mock_builder.parse_dxf.return_value = []
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("a.dxf", "b.dxf")

        assert result.layer_diff["added"] == []
        assert result.layer_diff["removed"] == []
        assert result.layer_diff["common"] == []


# ===========================================================================
# TestRenderDiff
# ===========================================================================


class TestRenderDiff:
    """렌더링 테스트"""

    def test_output_file_created(self, tmp_path):
        """출력 파일이 생성되는지 확인"""
        result = DXFDiffResult(
            matched=[
                EntityMatch(
                    entity_a=_make_entity("LINE", (0, 0), 10.0),
                    entity_b=_make_entity("LINE", (1, 1), 10.0),
                    similarity=0.9,
                ),
            ],
            only_in_a=[_make_entity("CIRCLE", (20, 20), 5.0)],
            only_in_b=[_make_entity("ARC", (30, 30), 8.0)],
            summary={"similarity_score": 0.5},
        )
        out = str(tmp_path / "diff.png")
        path = render_diff(result, "a.dxf", "b.dxf", output_path=out)

        assert Path(path).exists()
        assert Path(path).stat().st_size > 0

    def test_output_tempfile_when_no_path(self):
        """output_path 미지정 시 임시 파일 사용"""
        result = DXFDiffResult(
            matched=[],
            only_in_a=[_make_entity("LINE", (0, 0), 5.0)],
            only_in_b=[],
            summary={"similarity_score": 0.0},
        )
        path = render_diff(result, "a.dxf", "b.dxf")

        assert Path(path).exists()
        assert path.endswith(".png")

    def test_render_empty_result(self, tmp_path):
        """빈 결과 렌더링 (패치 0개)"""
        result = DXFDiffResult(summary={"similarity_score": 1.0})
        out = str(tmp_path / "empty.png")
        path = render_diff(result, "a.dxf", "b.dxf", output_path=out)

        assert Path(path).exists()
        assert Path(path).stat().st_size > 0


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @patch("core.gnn.DXFGraphBuilder")
    def test_parse_failure_a(self, mock_builder_cls):
        """파일 A 파싱 실패 시 빈 리스트 처리"""
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = [
            Exception("File not found"),
            [_make_entity("LINE", (0, 0), 5.0)],
        ]
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("bad.dxf", "good.dxf")

        assert result.summary["entity_count_a"] == 0
        assert result.summary["entity_count_b"] == 1
        assert len(result.only_in_b) == 1

    @patch("core.gnn.DXFGraphBuilder")
    def test_parse_failure_both(self, mock_builder_cls):
        """양쪽 모두 파싱 실패"""
        mock_builder = MagicMock()
        mock_builder.parse_dxf.side_effect = Exception("Corrupt DXF")
        mock_builder_cls.return_value = mock_builder

        result = compare_dxf("bad1.dxf", "bad2.dxf")

        assert result.summary["entity_count_a"] == 0
        assert result.summary["entity_count_b"] == 0
        assert result.summary["similarity_score"] == 1.0

    def test_max_distance_empty(self):
        """엔티티 없으면 기본 거리 1.0"""
        assert _compute_max_distance([], []) == 1.0

    def test_entity_rect_zero_size(self):
        """크기 0 엔티티의 바운딩 박스"""
        e = _make_entity("POINT", (5.0, 5.0), 0.0)
        x, y, w, h = _entity_rect(e)
        assert w > 0
        assert h > 0

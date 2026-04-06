"""DXF 구조 비교 및 시각화 모듈

두 DXF 파일의 기하학적 엔티티를 비교하고,
차이점을 시각적으로 렌더링한다.
"""

from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger


@dataclass
class EntityMatch:
    """매칭된 엔티티 쌍"""

    entity_a: object  # EntityInfo
    entity_b: object  # EntityInfo
    similarity: float  # 0~1


@dataclass
class DXFDiffResult:
    """DXF 비교 결과"""

    matched: list[EntityMatch] = field(default_factory=list)
    only_in_a: list = field(default_factory=list)  # list[EntityInfo]
    only_in_b: list = field(default_factory=list)  # list[EntityInfo]
    layer_diff: dict = field(default_factory=dict)  # {"added", "removed", "common"}
    summary: dict = field(default_factory=dict)


def _compute_match_score(a, b, max_dist: float) -> float:
    """두 엔티티 간 유사도 점수를 계산한다.

    Args:
        a: EntityInfo (파일 A)
        b: EntityInfo (파일 B)
        max_dist: 정규화에 사용할 최대 거리

    Returns:
        0~1 사이 유사도 점수 (1이 완전 일치)
    """
    if a.entity_type != b.entity_type:
        return 0.0

    # 중심점 거리 (정규화)
    dist = math.hypot(a.centroid[0] - b.centroid[0], a.centroid[1] - b.centroid[1])
    norm_dist = dist / max_dist if max_dist > 1e-8 else 0.0

    # 크기 차이 (정규화)
    max_size = max(a.size, b.size, 1e-8)
    size_diff = abs(a.size - b.size) / max_size

    # 각도 차이 (angle은 [-1, 1] 범위, pi로 나눈 값)
    angle_diff = abs(a.angle - b.angle) * 180.0  # degree 환산
    angle_diff = min(angle_diff, 360.0 - angle_diff)  # 순환 보정

    score = 1.0 - norm_dist * 0.4 - size_diff * 0.3 - (angle_diff / 180.0) * 0.3
    return max(score, 0.0)


def _compute_max_distance(entities_a: list, entities_b: list) -> float:
    """두 엔티티 리스트의 전체 영역에서 최대 거리를 계산한다."""
    all_entities = entities_a + entities_b
    if not all_entities:
        return 1.0
    xs = [e.centroid[0] for e in all_entities]
    ys = [e.centroid[1] for e in all_entities]
    dx = max(xs) - min(xs) if len(xs) > 1 else 1.0
    dy = max(ys) - min(ys) if len(ys) > 1 else 1.0
    return math.hypot(dx, dy) if math.hypot(dx, dy) > 1e-8 else 1.0


def compare_dxf(path_a: str, path_b: str) -> DXFDiffResult:
    """두 DXF 파일의 구조를 비교한다.

    Args:
        path_a: 첫 번째 DXF 파일 경로
        path_b: 두 번째 DXF 파일 경로

    Returns:
        DXFDiffResult: 비교 결과
    """
    from core.gnn import DXFGraphBuilder

    builder = DXFGraphBuilder()
    result = DXFDiffResult()

    # 1. 엔티티 추출
    try:
        entities_a = builder.parse_dxf(path_a)
    except Exception as e:
        logger.error(f"DXF 파싱 실패 (A): {path_a} — {e}")
        entities_a = []

    try:
        entities_b = builder.parse_dxf(path_b)
    except Exception as e:
        logger.error(f"DXF 파싱 실패 (B): {path_b} — {e}")
        entities_b = []

    # 2. 레이어 비교
    layers_a = {e.layer for e in entities_a}
    layers_b = {e.layer for e in entities_b}
    result.layer_diff = {
        "added": sorted(layers_b - layers_a),
        "removed": sorted(layers_a - layers_b),
        "common": sorted(layers_a & layers_b),
    }

    # 3. 그리디 이분 매칭
    max_dist = _compute_max_distance(entities_a, entities_b)
    threshold = 0.7

    used_b = set()
    matched_indices_a = set()

    for i, ea in enumerate(entities_a):
        best_score = -1.0
        best_j = -1
        for j, eb in enumerate(entities_b):
            if j in used_b:
                continue
            score = _compute_match_score(ea, eb, max_dist)
            if score >= threshold and score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0:
            result.matched.append(
                EntityMatch(entity_a=ea, entity_b=entities_b[best_j], similarity=best_score)
            )
            used_b.add(best_j)
            matched_indices_a.add(i)

    result.only_in_a = [e for i, e in enumerate(entities_a) if i not in matched_indices_a]
    result.only_in_b = [e for j, e in enumerate(entities_b) if j not in used_b]

    # 4. 요약
    total = len(entities_a) + len(entities_b)
    similarity_score = (2 * len(result.matched)) / total if total > 0 else 1.0
    result.summary = {
        "entity_count_a": len(entities_a),
        "entity_count_b": len(entities_b),
        "matched_count": len(result.matched),
        "only_in_a_count": len(result.only_in_a),
        "only_in_b_count": len(result.only_in_b),
        "similarity_score": round(similarity_score, 4),
    }

    logger.info(
        f"DXF 비교 완료: A={len(entities_a)}개, B={len(entities_b)}개, "
        f"매칭={len(result.matched)}개, 유사도={similarity_score:.4f}"
    )

    return result


def _entity_rect(entity) -> tuple[float, float, float, float]:
    """엔티티의 바운딩 박스 (x, y, w, h)를 추정한다."""
    cx, cy = entity.centroid
    half = max(entity.size / 2.0, 0.5)
    if entity.aspect_ratio > 1e-8:
        w = half
        h = half / entity.aspect_ratio
    else:
        w = h = half
    return cx - w, cy - h, w * 2, h * 2


def render_diff(
    result: DXFDiffResult,
    path_a: str,
    path_b: str,
    output_path: str = "",
) -> str:
    """비교 결과를 시각적으로 렌더링한다.

    Args:
        result: DXFDiffResult 비교 결과
        path_a: 첫 번째 DXF 파일 경로 (라벨용)
        path_b: 두 번째 DXF 파일 경로 (라벨용)
        output_path: 출력 이미지 경로 (빈 문자열이면 임시 파일)

    Returns:
        생성된 이미지 파일 경로
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    def _draw_entity(entity, color: str, alpha: float = 0.6, label: str = "") -> None:
        """엔티티를 축 위에 그린다."""
        cx, cy = entity.centroid
        if entity.entity_type == "CIRCLE":
            radius = entity.size / 2.0 if entity.size > 0 else 0.5
            circle = plt.Circle((cx, cy), radius, fill=False, edgecolor=color, linewidth=1.5, alpha=alpha)
            ax.add_patch(circle)
        else:
            x, y, w, h = _entity_rect(entity)
            rect = mpatches.FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0",
                fill=False,
                edgecolor=color,
                linewidth=1.5,
                alpha=alpha,
            )
            ax.add_patch(rect)

    # 매칭 엔티티 (gray)
    for m in result.matched:
        _draw_entity(m.entity_a, color="gray", alpha=0.4)

    # A에만 있는 엔티티 (red)
    for e in result.only_in_a:
        _draw_entity(e, color="red", alpha=0.7)

    # B에만 있는 엔티티 (blue)
    for e in result.only_in_b:
        _draw_entity(e, color="blue", alpha=0.7)

    # 범례
    legend_items = [
        mpatches.Patch(edgecolor="gray", facecolor="none", label=f"Matched ({len(result.matched)})"),
        mpatches.Patch(edgecolor="red", facecolor="none", label=f"Only in A ({len(result.only_in_a)})"),
        mpatches.Patch(edgecolor="blue", facecolor="none", label=f"Only in B ({len(result.only_in_b)})"),
    ]
    ax.legend(handles=legend_items, loc="upper right", fontsize=9)

    # 축 설정
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.set_title(
        f"DXF Diff: {Path(path_a).name} vs {Path(path_b).name}\n"
        f"Similarity: {result.summary.get('similarity_score', 0):.2%}",
        fontsize=11,
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, alpha=0.3)

    # 출력 경로
    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = tmp.name
        tmp.close()

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"DXF 비교 이미지 저장: {output_path}")
    return output_path

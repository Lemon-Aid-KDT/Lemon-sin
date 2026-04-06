"""
DXF 구조 검색 후처리 리랭커.

GNN 코사인 유사도만으로는 엔티티 분포·개수·비율이 크게 다른 도면도
높은 점수를 받을 수 있다. 쿼리 DXF의 구조 통계와 결과의 메타데이터를
비교하여 점수를 보정한다.
"""

from __future__ import annotations

import math
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class DXFProfile:
    """DXF 파일의 구조 프로파일 (리랭킹용 경량 통계)."""
    entity_count: int = 0
    entity_types: dict[str, int] = field(default_factory=dict)
    aspect_ratio: float = 1.0  # width / height
    layer_count: int = 1


def extract_dxf_profile(dxf_path: str | Path) -> DXFProfile:
    """DXF 파일에서 경량 프로파일을 추출한다."""
    try:
        from core.gnn import DXFGraphBuilder
        builder = DXFGraphBuilder()
        entities = builder.parse_dxf(str(dxf_path))
        if not entities:
            return DXFProfile()

        etypes: dict[str, int] = {}
        layers: set[str] = set()
        for e in entities:
            t = e.get("entity_type", "UNKNOWN")
            etypes[t] = etypes.get(t, 0) + 1
            layers.add(e.get("layer", "0"))

        # bbox aspect ratio
        xs = [e["centroid"][0] for e in entities if "centroid" in e]
        ys = [e["centroid"][1] for e in entities if "centroid" in e]
        if xs and ys:
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            aspect = w / max(h, 0.01)
        else:
            aspect = 1.0

        return DXFProfile(
            entity_count=len(entities),
            entity_types=etypes,
            aspect_ratio=aspect,
            layer_count=len(layers),
        )
    except Exception as e:
        logger.debug(f"DXF 프로파일 추출 실패: {e}")
        return DXFProfile()


def _entity_distribution_similarity(a: dict[str, int], b: dict[str, int]) -> float:
    """두 엔티티 타입 분포 간 코사인 유사도 (0~1)."""
    all_types = set(a) | set(b)
    if not all_types:
        return 1.0
    dot = sum(a.get(t, 0) * b.get(t, 0) for t in all_types)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values())) or 1.0
    mag_b = math.sqrt(sum(v ** 2 for v in b.values())) or 1.0
    return dot / (mag_a * mag_b)


def _count_penalty(query_count: int, result_count: int) -> float:
    """엔티티 개수 차이에 따른 페널티 (0~1, 1=동일)."""
    if query_count == 0 or result_count == 0:
        return 0.5
    ratio = min(query_count, result_count) / max(query_count, result_count)
    return ratio  # 0.5배~2배면 penalty=0.5~1.0


def _aspect_penalty(query_aspect: float, result_aspect: float) -> float:
    """종횡비 차이 페널티 (0~1, 1=동일)."""
    if query_aspect <= 0 or result_aspect <= 0:
        return 0.8
    ratio = min(query_aspect, result_aspect) / max(query_aspect, result_aspect)
    return max(ratio, 0.3)


def rerank_dxf_results(
    query_profile: DXFProfile,
    results: list,
    result_profiles: dict[str, DXFProfile] | None = None,
    gnn_weight: float = 0.6,
    dist_weight: float = 0.2,
    count_weight: float = 0.1,
    aspect_weight: float = 0.1,
) -> list:
    """DXF 검색 결과를 구조 프로파일 기반으로 리랭킹한다.

    Args:
        query_profile: 쿼리 DXF 프로파일
        results: SearchResult 리스트 (score 속성 필요)
        result_profiles: drawing_id → DXFProfile 매핑 (None이면 메타데이터에서 추출)
        gnn_weight: GNN 원본 점수 가중치
        dist_weight: 엔티티 분포 유사도 가중치
        count_weight: 엔티티 개수 유사도 가중치
        aspect_weight: 종횡비 유사도 가중치

    Returns:
        리랭킹된 결과 리스트 (score 보정됨)
    """
    if not results or query_profile.entity_count == 0:
        return results

    reranked = []
    for r in results:
        gnn_score = r.score

        # 결과 도면의 프로파일 (캐시 or 메타데이터)
        if result_profiles and r.drawing_id in result_profiles:
            rp = result_profiles[r.drawing_id]
        else:
            # 메타데이터에서 간이 추출
            meta = r.metadata if hasattr(r, "metadata") else {}
            rp = DXFProfile(
                entity_count=meta.get("entity_count", 0),
                entity_types=meta.get("entity_types", {}),
                aspect_ratio=meta.get("aspect_ratio", 1.0),
                layer_count=meta.get("layer_count", 1),
            )

        # 프로파일 비교
        if rp.entity_count > 0 and rp.entity_types:
            dist_sim = _entity_distribution_similarity(query_profile.entity_types, rp.entity_types)
            cnt_sim = _count_penalty(query_profile.entity_count, rp.entity_count)
            asp_sim = _aspect_penalty(query_profile.aspect_ratio, rp.aspect_ratio)
        else:
            # 메타데이터 없으면 GNN 점수만 사용 (페널티 없음)
            dist_sim = 1.0
            cnt_sim = 1.0
            asp_sim = 1.0

        combined = (
            gnn_weight * gnn_score
            + dist_weight * dist_sim
            + count_weight * cnt_sim
            + aspect_weight * asp_sim
        )

        # score 보정 (원본 결과 객체의 score를 덮어쓰지 않고 새 속성 추가)
        r.score = round(combined, 4)
        reranked.append(r)

    reranked.sort(key=lambda x: x.score, reverse=True)
    logger.debug(
        f"DXF 리랭킹 완료: top1={reranked[0].score:.3f} "
        f"(gnn={gnn_weight}, dist={dist_weight}, cnt={count_weight}, asp={aspect_weight})"
    )
    return reranked

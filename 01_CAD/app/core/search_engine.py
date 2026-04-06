"""Unified Search Engine — 4종 검색을 단일 인터페이스로 통합.

AS-IS:
    pipeline.search_by_text(query)
    pipeline.search_by_image(image)
    pipeline.search_by_dxf(dxf)
    pipeline.search_by_part_number(pn)

TO-BE:
    engine.search(SearchQuery(text="shaft", channels=[TEXT, IMAGE]))
    engine.search(SearchQuery(dxf_path="a.dxf", channels=[GNN]))
    engine.search(SearchQuery(part_number="SFB20", channels=[PART_NUMBER]))
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from core.models import (
    SearchChannel,
    SearchQuery,
    UnifiedSearchResult,
)

if TYPE_CHECKING:
    from core.pipeline import DrawingPipeline


class UnifiedSearchEngine:
    """4채널 검색 통합 엔진.

    기존 DrawingPipeline의 검색 메서드를 내부적으로 호출하면서,
    채널 조합과 결과 포맷을 통일합니다.
    """

    # 기본 채널 가중치 (설정에서 오버라이드 가능)
    DEFAULT_WEIGHTS = {
        SearchChannel.TEXT: 0.6,
        SearchChannel.IMAGE: 0.1,
        SearchChannel.GNN: 0.3,
        SearchChannel.PART_NUMBER: 1.0,  # 정확 매치이므로 1.0
    }

    def __init__(self, pipeline: DrawingPipeline):
        """기존 파이프라인을 래핑합니다."""
        self._pipeline = pipeline

    def search(self, query: SearchQuery) -> list[UnifiedSearchResult]:
        """통합 검색을 수행합니다.

        Args:
            query: SearchQuery DTO (채널, 가중치, 필터 포함)

        Returns:
            통합 점수로 정렬된 UnifiedSearchResult 목록
        """
        if not query.channels:
            logger.warning("검색 채널이 지정되지 않았습니다.")
            return []

        weights = query.channel_weights or self.DEFAULT_WEIGHTS
        category = query.filters.get("category", "")

        # 채널별 검색 결과 수집
        channel_results: dict[SearchChannel, list] = {}

        for channel in query.channels:
            try:
                results = self._search_channel(channel, query, category)
                if results:
                    channel_results[channel] = results
            except Exception as e:
                logger.error(f"채널 {channel.value} 검색 실패: {e}")

        if not channel_results:
            return []

        # 부품번호 검색은 별도 처리 (정확 매치)
        if SearchChannel.PART_NUMBER in channel_results:
            return self._format_part_number_results(
                channel_results[SearchChannel.PART_NUMBER]
            )

        # 채널 결과 통합 (가중 합산)
        merged = self._merge_channel_results(channel_results, weights)

        # top_k 적용
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[: query.top_k]

    # ------------------------------------------------------------------
    # Channel dispatchers
    # ------------------------------------------------------------------

    def _search_channel(
        self,
        channel: SearchChannel,
        query: SearchQuery,
        category: str,
    ) -> list:
        """채널별 검색을 파이프라인에 위임."""
        if channel == SearchChannel.TEXT and query.text:
            return self._pipeline.search_by_text(
                query.text,
                top_k=query.top_k * 3,  # 병합 전 오버샘플링
                category=category,
            )
        elif channel == SearchChannel.IMAGE and query.image_path:
            return self._pipeline.search_by_image(
                query.image_path,
                top_k=query.top_k * 3,
                category=category,
            )
        elif channel == SearchChannel.GNN and query.dxf_path:
            return self._pipeline.search_by_dxf(
                query.dxf_path,
                top_k=query.top_k * 3,
                category=category,
            )
        elif channel == SearchChannel.PART_NUMBER and query.part_number:
            return self._pipeline.search_by_part_number(query.part_number)
        return []

    # ------------------------------------------------------------------
    # Result merging
    # ------------------------------------------------------------------

    def _merge_channel_results(
        self,
        channel_results: dict[SearchChannel, list],
        weights: dict,
    ) -> list[UnifiedSearchResult]:
        """다중 채널 결과를 가중 합산으로 병합."""
        # record_id별 채널 점수 수집
        scores_by_id: dict[str, dict] = defaultdict(
            lambda: {"channel_scores": {}, "metadata": {}, "thumbnail": None}
        )

        for channel, results in channel_results.items():
            for r in results:
                rid = getattr(r, "drawing_id", getattr(r, "record_id", ""))
                if not rid:
                    continue

                score = getattr(r, "score", 0.0)
                meta = getattr(r, "metadata", {})

                entry = scores_by_id[rid]
                entry["channel_scores"][channel.value] = score
                # 메타데이터 병합 (첫 번째 것 우선)
                if not entry["metadata"]:
                    entry["metadata"] = meta if isinstance(meta, dict) else {}
                # 썸네일 (file_path에서)
                if not entry["thumbnail"]:
                    fp = getattr(r, "file_path", "") or meta.get("file_path", "")
                    if fp:
                        entry["thumbnail"] = fp

        # 가중 합산
        results = []
        total_weight = sum(
            weights.get(ch, 0) for ch in channel_results.keys()
        )
        if total_weight == 0:
            total_weight = 1.0

        for rid, data in scores_by_id.items():
            weighted_sum = 0.0
            for ch_name, ch_score in data["channel_scores"].items():
                ch_enum = SearchChannel(ch_name)
                w = weights.get(ch_enum, 0)
                weighted_sum += ch_score * w

            unified_score = weighted_sum / total_weight

            results.append(
                UnifiedSearchResult(
                    record_id=rid,
                    score=unified_score,
                    channel_scores=data["channel_scores"],
                    metadata=data["metadata"],
                    thumbnail_path=data["thumbnail"],
                )
            )

        return results

    def _format_part_number_results(
        self, records: list,
    ) -> list[UnifiedSearchResult]:
        """부품번호 검색 결과를 UnifiedSearchResult로 변환."""
        results = []
        for rec in records:
            rid = getattr(rec, "drawing_id", "")
            results.append(
                UnifiedSearchResult(
                    record_id=rid,
                    score=1.0,  # 정확 매치
                    channel_scores={"part_number": 1.0},
                    metadata={
                        "file_path": getattr(rec, "file_path", ""),
                        "file_name": getattr(rec, "file_name", ""),
                        "category": getattr(rec, "category", ""),
                        "part_numbers": getattr(rec, "part_numbers", []),
                    },
                    thumbnail_path=getattr(rec, "file_path", ""),
                )
            )
        return results

"""
Cross-Encoder Reranker — 2차 정밀 정렬

1차 검색(hybrid_search, bi-encoder)의 top-k 결과를
cross-encoder로 query-document 쌍을 직접 비교하여 재정렬.

사용 모델: cross-encoder/ms-marco-MiniLM-L-6-v2 (22MB, 빠름)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from core.vector_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """Reranker 출력"""

    drawing_id: str
    file_path: str
    score: float  # blended final score
    hybrid_score: float  # 원본 hybrid 점수
    reranker_score: float  # cross-encoder 점수
    metadata: dict


class CrossEncoderReranker:
    """Cross-Encoder 기반 2차 정밀 정렬기.

    Lazy loading 패턴: 첫 rerank() 호출 시 모델 로딩.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "",
        reranker_weight: float = 0.7,
    ):
        self._model_name = model_name
        self._device = device
        self._reranker_weight = reranker_weight
        self._model = None

    def _init_model(self) -> None:
        """Lazy 모델 로딩."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            device = self._device or None  # 빈 문자열이면 자동 선택
            self._model = CrossEncoder(self._model_name, device=device)
            logger.info("Reranker 로딩 완료: %s", self._model_name)
        except Exception as e:
            logger.warning("Reranker 로딩 실패: %s", e)
            self._model = None

    @property
    def is_available(self) -> bool:
        """모델 사용 가능 여부."""
        self._init_model()
        return self._model is not None

    def _build_document_text(self, result: SearchResult) -> str:
        """SearchResult에서 cross-encoder 입력용 문서 텍스트 생성."""
        parts: list[str] = []

        meta = result.metadata or {}

        # 카테고리
        category = meta.get("category", "")
        if category:
            parts.append(category.replace("_", " "))

        # OCR 텍스트
        ocr_text = meta.get("ocr_text", "")
        if ocr_text:
            parts.append(ocr_text[:300])

        # 부품번호
        part_numbers = meta.get("part_numbers", "")
        if part_numbers and part_numbers != "[]":
            parts.append(part_numbers)

        # 파일명
        file_name = meta.get("file_name", "")
        if file_name:
            parts.append(file_name)

        return " ".join(parts).strip() or "unknown drawing"

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """검색 결과를 cross-encoder로 재정렬.

        Args:
            query: 검색 쿼리
            results: 1차 검색 결과 (hybrid_search 출력)
            top_k: 반환할 결과 수

        Returns:
            재정렬된 SearchResult 리스트 (score가 blended score로 갱신)
        """
        if not results:
            return results

        self._init_model()
        if self._model is None:
            logger.warning("Reranker 사용 불가 — 원본 순서 유지")
            return results[:top_k]

        # Cross-encoder 입력 쌍 생성
        pairs: list[list[str]] = []
        for r in results:
            doc_text = self._build_document_text(r)
            pairs.append([query, doc_text])

        try:
            # Cross-encoder 점수 계산
            ce_scores = self._model.predict(pairs)

            # Sigmoid 정규화 (0~1 범위)
            ce_scores_norm = 1.0 / (1.0 + np.exp(-np.array(ce_scores)))

            # Blended score: α × reranker + (1-α) × hybrid
            α = self._reranker_weight
            reranked: list[tuple[float, SearchResult]] = []

            from core.vector_store import SearchResult as SR

            for i, r in enumerate(results):
                blended = α * ce_scores_norm[i] + (1 - α) * r.score
                new_r = SR(
                    drawing_id=r.drawing_id,
                    file_path=r.file_path,
                    distance=r.distance,
                    score=float(blended),
                    metadata=r.metadata,
                )
                reranked.append((float(blended), new_r))

            # 점수 내림차순 정렬
            reranked.sort(key=lambda x: x[0], reverse=True)

            return [r for _, r in reranked[:top_k]]

        except Exception as e:
            logger.warning("Reranker 실행 실패: %s — 원본 순서 유지", e)
            return results[:top_k]

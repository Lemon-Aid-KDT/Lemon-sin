"""
벡터 데이터베이스 관리 모듈

ChromaDB를 사용하여 도면 임베딩을 저장하고 유사도 검색을 수행한다.
이미지 임베딩과 텍스트 임베딩을 별도 컬렉션으로 관리하며,
하이브리드 검색 시 두 결과를 가중 결합한다.
"""

from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import chromadb
from loguru import logger


@dataclass
class SearchResult:
    """검색 결과 단건"""
    drawing_id: str          # 도면 고유 ID
    file_path: str           # 도면 파일 경로
    distance: float          # 유사도 거리 (낮을수록 유사)
    score: float             # 유사도 점수 (0~1, 높을수록 유사)
    metadata: dict = field(default_factory=dict)  # 도면 메타데이터


class VectorStore:
    """ChromaDB 기반 벡터 저장소"""

    def __init__(self, persist_dir: str = "./data/vector_store", collection_name: str = "drawings"):
        """
        Args:
            persist_dir: ChromaDB 데이터 영속화 경로
            collection_name: 기본 컬렉션 이름
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))

            # 이미지 임베딩용 컬렉션
            self._image_collection = self._client.get_or_create_collection(
                name=f"{collection_name}_image",
                metadata={"hnsw:space": "cosine"},
            )

            # 텍스트(OCR) 임베딩용 컬렉션
            self._text_collection = self._client.get_or_create_collection(
                name=f"{collection_name}_text",
                metadata={"hnsw:space": "cosine"},
            )

            # GNN 구조 임베딩용 컬렉션
            self._gnn_collection = self._client.get_or_create_collection(
                name=f"{collection_name}_gnn",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.error(f"ChromaDB 초기화 실패 (경로: {self.persist_dir}): {e}")
            raise RuntimeError(
                f"벡터 DB 초기화 실패: {e}. "
                f"'{persist_dir}' 경로의 권한 및 디스크 공간을 확인하세요."
            ) from e

        logger.info(
            f"VectorStore 초기화 완료: "
            f"이미지 {self._image_collection.count()}건, "
            f"텍스트 {self._text_collection.count()}건, "
            f"GNN {self._gnn_collection.count()}건"
        )

    def add_drawing(
        self,
        drawing_id: str,
        image_embedding: np.ndarray | None = None,
        text_embedding: np.ndarray | None = None,
        gnn_embedding: np.ndarray | None = None,
        metadata: dict | None = None,
    ):
        """
        도면 임베딩을 벡터 DB에 등록한다.

        Args:
            drawing_id: 도면 고유 ID
            image_embedding: CLIP 이미지 임베딩 벡터
            text_embedding: 텍스트 임베딩 벡터
            gnn_embedding: GNN 구조 임베딩 벡터
            metadata: 도면 메타데이터 (file_path, category, part_numbers 등)
        """
        meta = metadata or {}
        # ChromaDB는 metadata value로 str, int, float, bool만 허용
        safe_meta = {k: str(v) if isinstance(v, (list, dict)) else v for k, v in meta.items()}
        # ChromaDB는 빈 dict를 허용하지 않음
        if not safe_meta:
            safe_meta = {"_placeholder": "true"}

        if image_embedding is not None:
            try:
                emb = image_embedding.tolist() if hasattr(image_embedding, "tolist") else list(image_embedding)
                self._image_collection.upsert(
                    ids=[drawing_id],
                    embeddings=[emb],
                    metadatas=[safe_meta],
                )
            except Exception as e:
                logger.error(f"이미지 임베딩 저장 실패 ({drawing_id}): {e}")
                raise

        if text_embedding is not None:
            try:
                emb = text_embedding.tolist() if hasattr(text_embedding, "tolist") else list(text_embedding)
                self._text_collection.upsert(
                    ids=[drawing_id],
                    embeddings=[emb],
                    metadatas=[safe_meta],
                )
            except Exception as e:
                logger.warning(f"텍스트 임베딩 저장 실패 ({drawing_id}), 이미지만 저장됨: {e}")

        if gnn_embedding is not None:
            try:
                emb = gnn_embedding.tolist() if hasattr(gnn_embedding, "tolist") else list(gnn_embedding)
                self._gnn_collection.upsert(
                    ids=[drawing_id],
                    embeddings=[emb],
                    metadatas=[safe_meta],
                )
            except Exception as e:
                logger.warning(f"GNN 임베딩 저장 실패 ({drawing_id}), 다른 채널은 보존됨: {e}")

        logger.debug(f"도면 등록: {drawing_id}")

    def search_by_image(
        self, query_embedding: np.ndarray, top_k: int = 10,
        where_filter: dict | None = None,
    ) -> list[SearchResult]:
        """
        이미지 임베딩으로 유사 도면을 검색한다.

        Args:
            query_embedding: 쿼리 이미지 또는 CLIP 텍스트 임베딩
            top_k: 반환 결과 수
            where_filter: ChromaDB where 절 (예: {"category": "Shafts"})

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        if self._image_collection.count() == 0:
            logger.warning("이미지 컬렉션이 비어있습니다.")
            return []

        try:
            emb = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)
            query_kwargs: dict = {
                "query_embeddings": [emb],
                "n_results": min(top_k, self._image_collection.count()),
            }
            if where_filter:
                query_kwargs["where"] = where_filter
            results = self._image_collection.query(**query_kwargs)
            return self._parse_results(results)
        except Exception as e:
            logger.error(f"이미지 검색 실패: {e}")
            return []

    def search_by_text(
        self, query_embedding: np.ndarray, top_k: int = 10,
        where_filter: dict | None = None,
    ) -> list[SearchResult]:
        """
        텍스트 임베딩으로 도면을 검색한다.

        Args:
            query_embedding: 쿼리 텍스트 임베딩
            top_k: 반환 결과 수
            where_filter: ChromaDB where 절 (예: {"category": "Shafts"})

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        if self._text_collection.count() == 0:
            logger.warning("텍스트 컬렉션이 비어있습니다.")
            return []

        try:
            emb = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)
            query_kwargs: dict = {
                "query_embeddings": [emb],
                "n_results": min(top_k, self._text_collection.count()),
            }
            if where_filter:
                query_kwargs["where"] = where_filter
            results = self._text_collection.query(**query_kwargs)
            return self._parse_results(results)
        except Exception as e:
            logger.error(f"텍스트 검색 실패: {e}")
            return []

    def search_by_gnn(
        self, query_embedding: np.ndarray, top_k: int = 10,
        where_filter: dict | None = None,
    ) -> list[SearchResult]:
        """
        GNN 구조 임베딩으로 유사 도면을 검색한다.

        Args:
            query_embedding: GNN 구조 임베딩 벡터
            top_k: 반환 결과 수
            where_filter: ChromaDB where 절

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        if self._gnn_collection.count() == 0:
            logger.warning("GNN 컬렉션이 비어있습니다.")
            return []

        try:
            emb = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)
            query_kwargs: dict = {
                "query_embeddings": [emb],
                "n_results": min(top_k, self._gnn_collection.count()),
            }
            if where_filter:
                query_kwargs["where"] = where_filter
            results = self._gnn_collection.query(**query_kwargs)
            return self._parse_results(results)
        except Exception as e:
            logger.error(f"GNN 검색 실패: {e}")
            return []

    def hybrid_search(
        self,
        image_embedding: np.ndarray | None = None,
        text_embedding: np.ndarray | None = None,
        gnn_embedding: np.ndarray | None = None,
        top_k: int = 10,
        image_weight: float = 0.5,
        text_weight: float = 0.5,
        gnn_weight: float = 0.0,
        where_filter: dict | None = None,
    ) -> list[SearchResult]:
        """
        이미지 + 텍스트 + GNN 하이브리드 검색을 수행한다.
        각 채널 검색 결과의 점수를 가중 결합하여 최종 순위를 결정한다.

        Args:
            image_embedding: 이미지 쿼리 임베딩
            text_embedding: 텍스트 쿼리 임베딩
            gnn_embedding: GNN 구조 쿼리 임베딩
            top_k: 반환 결과 수
            image_weight: 이미지 검색 가중치
            text_weight: 텍스트 검색 가중치
            gnn_weight: GNN 구조 검색 가중치
            where_filter: ChromaDB where 절 (예: {"category": "Shafts"})

        Returns:
            list[SearchResult]: 하이브리드 스코어 순 검색 결과
        """
        score_map: dict[str, dict] = {}

        def _init_entry(drawing_id: str, r) -> None:
            if drawing_id not in score_map:
                score_map[drawing_id] = {
                    "file_path": r.file_path,
                    "metadata": r.metadata,
                    "image_score": 0.0,
                    "text_score": 0.0,
                    "gnn_score": 0.0,
                }

        # 이미지 검색 결과 수집 (실패 시 다른 채널만 사용)
        if image_embedding is not None:
            try:
                image_results = self.search_by_image(
                    image_embedding, top_k=top_k * 2, where_filter=where_filter,
                )
            except Exception as e:
                logger.warning(f"하이브리드 검색 중 이미지 채널 실패: {e}")
                image_results = []
            for r in image_results:
                _init_entry(r.drawing_id, r)
                score_map[r.drawing_id]["image_score"] = r.score

        # 텍스트 검색 결과 수집 (실패 시 다른 채널만 사용)
        if text_embedding is not None:
            try:
                text_results = self.search_by_text(
                    text_embedding, top_k=top_k * 2, where_filter=where_filter,
                )
            except Exception as e:
                logger.warning(f"하이브리드 검색 중 텍스트 채널 실패: {e}")
                text_results = []
            for r in text_results:
                _init_entry(r.drawing_id, r)
                score_map[r.drawing_id]["text_score"] = r.score

        # GNN 구조 검색 결과 수집 (실패 시 다른 채널만 사용)
        if gnn_embedding is not None and gnn_weight > 0:
            try:
                gnn_results = self.search_by_gnn(
                    gnn_embedding, top_k=top_k * 2, where_filter=where_filter,
                )
            except Exception as e:
                logger.warning(f"하이브리드 검색 중 GNN 채널 실패: {e}")
                gnn_results = []
            for r in gnn_results:
                _init_entry(r.drawing_id, r)
                score_map[r.drawing_id]["gnn_score"] = r.score

        # 가중 결합
        combined_results = []
        for drawing_id, data in score_map.items():
            combined_score = (
                image_weight * data["image_score"]
                + text_weight * data["text_score"]
                + gnn_weight * data["gnn_score"]
            )
            combined_results.append(SearchResult(
                drawing_id=drawing_id,
                file_path=data.get("file_path", ""),
                distance=1.0 - combined_score,
                score=combined_score,
                metadata=data.get("metadata", {}),
            ))

        # 점수 내림차순 정렬
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:top_k]

    @staticmethod
    def _parse_results(raw_results: dict) -> list[SearchResult]:
        """ChromaDB 쿼리 결과를 SearchResult 리스트로 변환"""
        results = []
        if not raw_results["ids"] or not raw_results["ids"][0]:
            return results

        ids = raw_results["ids"][0]
        distances = raw_results["distances"][0] if raw_results.get("distances") else [0.0] * len(ids)
        metadatas = raw_results["metadatas"][0] if raw_results.get("metadatas") else [{}] * len(ids)

        for drawing_id, distance, metadata in zip(ids, distances, metadatas):
            if metadata is None:
                metadata = {}
            # cosine 거리 → 유사도 점수 변환 (ChromaDB cosine: distance = 1 - similarity)
            score = max(0.0, 1.0 - distance)
            results.append(SearchResult(
                drawing_id=drawing_id,
                file_path=metadata.get("file_path", ""),
                distance=distance,
                score=score,
                metadata=metadata,
            ))

        return results

    def get_stats(self) -> dict:
        """벡터 DB 통계 정보 반환"""
        return {
            "image_collection_count": self._image_collection.count(),
            "text_collection_count": self._text_collection.count(),
            "gnn_collection_count": self._gnn_collection.count(),
            "persist_dir": str(self.persist_dir),
        }

    def delete_drawing(self, drawing_id: str):
        """도면 삭제"""
        try:
            self._image_collection.delete(ids=[drawing_id])
        except Exception as e:
            logger.warning(f"이미지 컬렉션에서 삭제 실패 ({drawing_id}): {e}")
        try:
            self._text_collection.delete(ids=[drawing_id])
        except Exception as e:
            logger.warning(f"텍스트 컬렉션에서 삭제 실패 ({drawing_id}): {e}")
        try:
            self._gnn_collection.delete(ids=[drawing_id])
        except Exception as e:
            logger.warning(f"GNN 컬렉션에서 삭제 실패 ({drawing_id}): {e}")
        logger.debug(f"도면 삭제: {drawing_id}")

    def reset(self):
        """전체 벡터 DB 초기화 (주의: 모든 데이터 삭제)"""
        try:
            img_name = self._image_collection.name
            txt_name = self._text_collection.name
            gnn_name = self._gnn_collection.name
            self._client.delete_collection(img_name)
            self._client.delete_collection(txt_name)
            self._client.delete_collection(gnn_name)
            self._image_collection = self._client.get_or_create_collection(
                name=img_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._text_collection = self._client.get_or_create_collection(
                name=txt_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._gnn_collection = self._client.get_or_create_collection(
                name=gnn_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.warning("벡터 DB 초기화 완료")
        except Exception as e:
            logger.error(f"벡터 DB 초기화 실패: {e}")
            raise RuntimeError(f"벡터 DB 초기화 실패: {e}") from e

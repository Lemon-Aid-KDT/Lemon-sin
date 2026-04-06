"""
Pipeline 싱글톤 모듈.

Streamlit과 FastAPI가 동일한 DrawingPipeline 인스턴스를 공유하도록 한다.
Thread-safe lazy initialization.
"""

import threading
from pathlib import Path

from loguru import logger

_pipeline = None
_lock = threading.Lock()


def get_pipeline():
    """프로세스 전역 DrawingPipeline 싱글톤을 반환한다.

    처음 호출 시 settings 기반으로 초기화하며, 이후는 캐시된 인스턴스를 반환.
    Thread-safe (threading.Lock).
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    with _lock:
        if _pipeline is not None:
            return _pipeline

        from config.settings import settings
        from core.pipeline import DrawingPipeline

        logger.info("DrawingPipeline 싱글톤 초기화 시작")

        _pipeline = DrawingPipeline(
            vector_store_dir=str(settings.chroma_persist_dir),
            upload_dir=str(settings.upload_dir),
            ollama_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
            clip_model=settings.clip_model,
            clip_pretrained=settings.clip_pretrained,
            clip_finetuned_path=settings.clip_finetuned_path,
            image_weight=settings.image_weight,
            text_weight=settings.text_weight,
            yolo_cls_model=settings.yolo_cls_model_path if settings.yolo_cls_enabled else "",
            yolo_cls_confidence=settings.yolo_cls_confidence_threshold,
            yolo_cls_device=settings.yolo_cls_device,
            yolo_cls_sha256=settings.yolo_cls_sha256,
            yolo_det_model=settings.yolo_det_model_path if settings.yolo_det_enabled else "",
            yolo_det_confidence=settings.yolo_det_confidence_threshold,
            yolo_det_device=settings.yolo_det_device,
            yolo_det_iou=settings.yolo_det_iou_threshold,
            yolo_det_sha256=settings.yolo_det_sha256,
            llm_rate_limit_rpm=settings.llm_rate_limit_rpm,
            category_keywords_path=settings.category_keywords_path,
            gnn_model=settings.gnn_model_path if settings.gnn_enabled else "",
            gnn_embedding_dim=settings.gnn_embedding_dim,
            gnn_weight=settings.gnn_weight,
            gnn_device=settings.gnn_device,
            gnn_k_neighbors=settings.gnn_k_neighbors,
            reranker_enabled=settings.reranker_enabled,
            reranker_model=settings.reranker_model,
            reranker_weight=settings.reranker_weight,
            reranker_top_k_multiplier=settings.reranker_top_k_multiplier,
            use_sqlite=True,
            sqlite_db_path=settings.sqlite_db_path,
        )

        logger.info("DrawingPipeline 싱글톤 초기화 완료")
        return _pipeline


def reset_pipeline():
    """테스트용: 싱글톤 초기화."""
    global _pipeline
    with _lock:
        _pipeline = None

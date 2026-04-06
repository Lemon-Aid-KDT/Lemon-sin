"""
CAD Vision API — 통계 라우터.

시스템 통계 조회.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_pipeline
from app.api.schemas import (
    ModelInfo,
    ModelListResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    StatsResponse,
)
from app.api.utils import safe_error

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(pipeline=Depends(get_pipeline)):
    """시스템 통계를 반환한다."""
    try:
        stats = pipeline.get_stats()
        vs = stats.get("vector_store", {})
        yolo_cls = stats.get("yolo_classifier", {})
        yolo_det = stats.get("yolo_detector", {})
        gnn = stats.get("gnn_embedder", {})
        ollama_healthy = bool(stats.get("ollama_healthy"))
        ollama_model = ""
        try:
            ollama_model = getattr(pipeline._llm, "model", "")
        except Exception:
            pass
        return StatsResponse(
            total_drawings=stats.get("total_drawings", 0),
            image_collection_count=vs.get("image_collection_count", 0),
            text_collection_count=vs.get("text_collection_count", 0),
            gnn_collection_count=vs.get("gnn_collection_count", 0),
            categories=stats.get("categories", []),
            category_counts=stats.get("category_counts", {}),
            ollama_status="healthy" if ollama_healthy else "unavailable",
            ollama_model=ollama_model,
            ollama_healthy=ollama_healthy,
            yolo_cls_enabled=yolo_cls.get("enabled", False),
            yolo_det_enabled=yolo_det.get("enabled", False),
            gnn_enabled=gnn.get("enabled", False),
        )
    except Exception as e:
        raise safe_error(e, "통계 조회")


@router.get("/models", response_model=ModelListResponse)
async def list_models(pipeline=Depends(get_pipeline)):
    """사용 가능한 Ollama 모델 목록을 반환한다."""
    try:
        llm = pipeline._llm
        raw_models = llm.get_available_models()
        models = [
            ModelInfo(
                name=m.get("name", ""),
                size=m.get("size", ""),
                modified=m.get("modified", ""),
            )
            for m in raw_models
        ]
        return ModelListResponse(models=models)
    except Exception as e:
        raise safe_error(e, "모델 목록 조회")


@router.put("/settings/model", response_model=SettingsUpdateResponse)
async def update_model(req: SettingsUpdateRequest, pipeline=Depends(get_pipeline)):
    """활성 LLM 모델을 변경한다."""
    try:
        pipeline._llm.model = req.model
        return SettingsUpdateResponse(status="ok", model=req.model)
    except Exception as e:
        raise safe_error(e, "모델 변경")

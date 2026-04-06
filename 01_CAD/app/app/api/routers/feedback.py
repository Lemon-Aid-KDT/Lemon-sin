"""
CAD Vision API — 피드백 라우터.

검색 결과 피드백 제출, 통계, 내보내기.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_feedback_store
from app.api.utils import safe_error

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback")
async def submit_feedback(
    query_text: str = Query(...),
    query_type: str = Query("text"),
    drawing_id: str = Query(...),
    score: float = Query(0.0),
    relevance: int = Query(..., ge=-1, le=1),
    category: str = Query(""),
    comment: str = Query(""),
    store=Depends(get_feedback_store),
):
    """검색 결과에 대한 피드백을 제출한다."""
    try:
        feedback_id = store.add_feedback(
            query_text=query_text,
            query_type=query_type,
            drawing_id=drawing_id,
            score=score,
            relevance=relevance,
            category=category,
            comment=comment,
        )
        return {"status": "ok", "feedback_id": feedback_id}
    except Exception as e:
        raise safe_error(e, "피드백 제출")


@router.get("/feedback/stats")
async def get_feedback_stats(store=Depends(get_feedback_store)):
    """피드백 통계를 반환한다."""
    try:
        return store.get_feedback_stats()
    except Exception as e:
        raise safe_error(e, "피드백 통계 조회")


@router.post("/feedback/export")
async def export_feedback(
    format: str = Query("jsonl"),
    store=Depends(get_feedback_store),
):
    """피드백을 학습 데이터로 내보낸다.

    format: "jsonl" (학습 쌍) 또는 "csv" (전체 피드백)
    """
    try:
        if format == "csv":
            path = store.export_csv()
        else:
            path = store.export_training_pairs()
        return {"status": "ok", "format": format, "path": path}
    except Exception as e:
        raise safe_error(e, "피드백 내보내기")

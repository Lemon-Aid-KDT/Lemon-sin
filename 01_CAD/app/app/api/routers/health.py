"""
CAD Vision API — 헬스체크 라우터.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """API 서버 헬스체크."""
    return {"status": "ok"}


@router.get("/api/v1/health")
async def health_check_v1():
    """API v1 헬스체크."""
    return {"status": "ok", "version": "5.0"}

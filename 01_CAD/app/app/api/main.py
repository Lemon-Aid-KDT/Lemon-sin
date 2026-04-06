"""
CAD Vision REST API — FastAPI 애플리케이션.

라우터 기반 모듈 구조. 각 기능별 엔드포인트는 routers/ 에서 관리.

실행:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
    또는: python run_api.py
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.routers import analysis, drawings, feedback, health, stats, tools, viewer, viewer_3d

# ── Rate Limiter (in-memory, IP 기반) ──

_rate_limit_store: dict[str, list[float]] = {}
API_RATE_LIMIT_RPM = 60  # 분당 최대 요청 수


def _check_rate_limit(client_ip: str) -> bool:
    """IP 기반 간단한 rate limiting. True면 허용, False면 차단."""
    now = time.time()
    window = 60.0  # 1분

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # 1분 이전 기록 제거
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < window
    ]

    if len(_rate_limit_store[client_ip]) >= API_RATE_LIMIT_RPM:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


# ── FastAPI 앱 ──

app = FastAPI(
    title="CAD Vision API",
    description="AI 기반 산업 도면 검색 및 분류 시스템",
    version="5.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ── Rate Limit 미들웨어 ──


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """IP 기반 Rate Limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도하세요."},
        )
    return await call_next(request)


# ── 라우터 등록 ──

app.include_router(health.router)
app.include_router(drawings.router)
app.include_router(analysis.router)
app.include_router(stats.router)
app.include_router(tools.router)
app.include_router(feedback.router)
app.include_router(viewer.router)
app.include_router(viewer_3d.router)

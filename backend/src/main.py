"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """애플리케이션 시작·종료 라이프사이클.

    Yields:
        None: 애플리케이션 실행 중.
    """
    setup_logging()
    # TODO(Phase 1): DB 연결 풀 초기화
    # TODO(Phase 2): Redis 연결
    yield
    # TODO: 정리 작업


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리.

    Returns:
        설정이 완료된 FastAPI 인스턴스.
    """
    settings = get_settings()
    app = FastAPI(
        title="Lemon Healthcare API",
        description="만성질환자 중심의 AI 헬스케어 플랫폼 API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """헬스 체크 엔드포인트.

        Returns:
            서비스 상태 정보.
        """
        return {"status": "ok", "version": "0.1.0"}

    # TODO(Phase 1): 라우터 등록 — e.g. app.include_router(activity.router, prefix="/api/v1")

    return app


app = create_app()

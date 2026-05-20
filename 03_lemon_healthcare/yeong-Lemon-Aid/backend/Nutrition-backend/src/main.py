"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api.v1.examples import HEALTH_RESPONSE_EXAMPLES
from src.api.v1.router import api_router
from src.config import Settings, get_settings
from src.db.session import dispose_engine
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import SecureHeadersMiddleware
from src.models.schemas.readiness import ReadinessResponse
from src.services.readiness import build_readiness_response
from src.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 시작과 종료 라이프사이클을 관리한다.

    Args:
        _app: FastAPI 애플리케이션 인스턴스.

    Yields:
        애플리케이션 실행 구간 제어권.
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    # TODO: Phase 2에서 Redis/OCR/LLM adapter readiness check를 분리한다.
    try:
        yield
    finally:
        await dispose_engine()


def configure_security_middleware(app: FastAPI, settings: Settings) -> None:
    """Register HTTP security middleware.

    Args:
        app: FastAPI app to configure.
        settings: Loaded application settings.

    Returns:
        None.
    """
    if settings.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
        )
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(SecureHeadersMiddleware)


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI 앱 인스턴스를 생성한다.

    Args:
        settings: 테스트와 명시적 구성에 사용할 설정 객체. None이면 환경에서 로드한다.

    Returns:
        설정과 기본 라우트가 등록된 FastAPI 앱.
    """
    app_settings = settings or get_settings()
    docs_url = "/docs" if app_settings.environment != "production" else None
    redoc_url = "/redoc" if app_settings.environment != "production" else None

    app = FastAPI(
        title="Lemon Healthcare API",
        description="만성질환자 중심의 AI 헬스케어 플랫폼 API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )
    configure_security_middleware(app, app_settings)

    @app.get(
        "/health",
        tags=["health"],
        responses={200: {"content": {"application/json": {"examples": HEALTH_RESPONSE_EXAMPLES}}}},
    )
    async def health_check() -> dict[str, str]:
        """서비스 상태를 반환한다.

        Returns:
            서비스 상태와 API 버전.
        """
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/ready", tags=["health"], response_model=ReadinessResponse)
    async def readiness_check() -> ReadinessResponse:
        """Return sanitized runtime readiness status.

        Returns:
            Sanitized readiness status for release gates.
        """
        return build_readiness_response(app_settings)

    app.include_router(api_router)

    return app


app = create_app()

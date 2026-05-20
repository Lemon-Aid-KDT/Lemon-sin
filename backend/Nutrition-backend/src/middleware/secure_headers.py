"""HTTP security response headers middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.config import Settings

BASELINE_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-site",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

PRODUCTION_HSTS_HEADER: tuple[str, str] = (
    "Strict-Transport-Security",
    "max-age=63072000; includeSubDomains; preload",
)


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security response headers to every HTTP response."""

    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        super().__init__(app)
        self._is_production = settings.environment == "production"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in BASELINE_SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if self._is_production:
            header, value = PRODUCTION_HSTS_HEADER
            response.headers.setdefault(header, value)
        return response

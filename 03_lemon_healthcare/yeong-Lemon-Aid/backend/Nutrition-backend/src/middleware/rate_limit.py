"""In-memory HTTP rate limiting middleware.

This middleware is intentionally dependency-light for the Phase 6 release gate.
It is suitable for single-process local/staging smoke tests. Multi-worker or
multi-instance production deployments should replace the store with Redis so
limits are shared across processes.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from src.config import Settings

WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class RateLimitRule:
    """Resolved rate limit rule for a request.

    Attributes:
        bucket: Stable route bucket label.
        limit_per_minute: Request count allowed per rolling minute.
    """

    bucket: str
    limit_per_minute: int


@dataclass
class _RateLimitWindow:
    """Mutable in-memory request window.

    Attributes:
        starts_at: Monotonic timestamp when the current window started.
        count: Number of requests seen in the current window.
    """

    starts_at: float
    count: int


class InMemoryRateLimiter:
    """Simple per-key fixed-window rate limiter.

    The store deliberately keeps only bucket ids and hashed caller identifiers.
    Raw Authorization tokens are never stored.
    """

    def __init__(self) -> None:
        """Initialize the limiter."""
        self._windows: dict[tuple[str, str], _RateLimitWindow] = {}

    def allow(self, *, key: str, rule: RateLimitRule, now: float | None = None) -> bool:
        """Return whether a request is allowed.

        Args:
            key: Hashed caller key.
            rule: Resolved rate limit rule.
            now: Optional monotonic time override for tests.

        Returns:
            True when the request is within the current limit.
        """
        current_time = time.monotonic() if now is None else now
        window_key = (rule.bucket, key)
        window = self._windows.get(window_key)
        if window is None or current_time - window.starts_at >= WINDOW_SECONDS:
            self._windows[window_key] = _RateLimitWindow(starts_at=current_time, count=1)
            return True
        if window.count >= rule.limit_per_minute:
            return False
        window.count += 1
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply coarse route-bucket rate limits to public HTTP traffic."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: Wrapped ASGI application.
            settings: Runtime settings containing rate limit values.
            limiter: Optional limiter store for tests.
        """
        super().__init__(app)
        self._settings = settings
        self._limiter = limiter or InMemoryRateLimiter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Apply the configured rate limit before routing.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response, or a 429 response when the caller exceeds the limit.
        """
        if not self._settings.rate_limit_enabled or _is_exempt_path(request.url.path):
            return await call_next(request)

        rule = _resolve_rule(request, self._settings)
        key = _caller_key(request)
        if not self._limiter.allow(key=key, rule=rule):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry later.",
                        "bucket": rule.bucket,
                    }
                },
            )
        return await call_next(request)


def _resolve_rule(request: Request, settings: Settings) -> RateLimitRule:
    """Resolve a route bucket and limit for the request.

    Args:
        request: Incoming request.
        settings: Runtime settings.

    Returns:
        Rate limit rule.
    """
    path = request.url.path
    method = request.method.upper()
    if method == "POST" and path == "/api/v1/supplements/analyze":
        return RateLimitRule(
            bucket="supplement_image_upload",
            limit_per_minute=settings.rate_limit_image_upload_per_minute,
        )
    if method == "POST" and path == "/api/v1/supplements/recommendations/explain":
        return RateLimitRule(
            bucket="supplement_llm_explain",
            limit_per_minute=settings.rate_limit_llm_explain_per_minute,
        )
    return RateLimitRule(
        bucket="default",
        limit_per_minute=settings.rate_limit_default_per_minute,
    )


def _caller_key(request: Request) -> str:
    """Build a privacy-preserving caller key.

    Args:
        request: Incoming request.

    Returns:
        Hashed bearer token key when present, otherwise client host key.
    """
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        digest = hashlib.sha256(authorization.encode("utf-8")).hexdigest()
        return f"bearer:{digest}"
    client_host = request.client.host if request.client is not None else "unknown"
    return f"ip:{client_host}"


def _is_exempt_path(path: str) -> bool:
    """Return whether a path should skip rate limiting.

    Args:
        path: Request path.

    Returns:
        True for liveness/readiness and documentation assets.
    """
    return path in {"/health", "/ready", "/openapi.json", "/docs", "/redoc"}

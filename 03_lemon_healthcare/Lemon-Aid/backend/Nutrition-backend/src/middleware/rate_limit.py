"""Process-local fixed-window rate limiting middleware."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from threading import Lock

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config import Settings

SUPPLEMENT_IMAGE_UPLOAD_BUCKET = "supplement_image_upload"
"""Rate-limit bucket name for high-cost supplement image intake."""


@dataclass(frozen=True)
class _RateLimitRule:
    """Route-specific fixed-window rate-limit rule."""

    bucket: str
    method: str
    path: str
    limit: int


@dataclass
class _Window:
    """Mutable in-memory counter for one subject and rate-limit rule."""

    count: int
    reset_at: float


@dataclass(frozen=True)
class _RateLimitDecision:
    """Decision returned after consuming a rate-limit token."""

    allowed: bool
    retry_after_seconds: int


class RateLimitMiddleware:
    """Apply process-local rate limits before expensive API handlers run.

    The middleware intentionally stores only hashed client-derived keys. Raw
    client identifiers are never persisted in the in-memory map.
    """

    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        """Initialize route limits from runtime settings.

        Args:
            app: Downstream ASGI application.
            settings: Runtime settings controlling limits and enablement.
        """
        self.app = app
        self._enabled = settings.rate_limit_enabled
        self._window_seconds = settings.rate_limit_window_seconds
        self._rules = (
            _RateLimitRule(
                bucket=SUPPLEMENT_IMAGE_UPLOAD_BUCKET,
                method="POST",
                path="/api/v1/supplements/analyze",
                limit=settings.supplement_image_upload_rate_limit,
            ),
        )
        self._windows: dict[str, _Window] = {}
        self._lock = Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI call and reject requests that exceed a configured rule.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None.
        """
        if scope["type"] != "http" or not self._enabled:
            await self.app(scope, receive, send)
            return

        rule = self._match_rule(scope)
        if rule is None:
            await self.app(scope, receive, send)
            return

        decision = self._consume(rule, scope)
        if decision.allowed:
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "code": "too_many_requests",
                    "message": "Too many requests. Please retry later.",
                    "bucket": rule.bucket,
                    "retry_after_seconds": decision.retry_after_seconds,
                }
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
        await response(scope, receive, send)

    def _match_rule(self, scope: Scope) -> _RateLimitRule | None:
        """Return the configured rule matching an ASGI request.

        Args:
            scope: ASGI request scope.

        Returns:
            Matching rule or None when the request is outside rate-limited paths.
        """
        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        for rule in self._rules:
            if rule.method == method and rule.path == path:
                return rule
        return None

    def _consume(self, rule: _RateLimitRule, scope: Scope) -> _RateLimitDecision:
        """Consume one token for the request subject.

        Args:
            rule: Matching rate-limit rule.
            scope: ASGI request scope used to identify the subject.

        Returns:
            Allow/deny decision with a retry-after duration for denied requests.
        """
        now = time.monotonic()
        key = self._subject_key(rule, scope)
        with self._lock:
            self._purge_expired(now)
            window = self._windows.get(key)
            if window is None or window.reset_at <= now:
                self._windows[key] = _Window(
                    count=1,
                    reset_at=now + self._window_seconds,
                )
                return _RateLimitDecision(
                    allowed=True,
                    retry_after_seconds=self._window_seconds,
                )
            if window.count >= rule.limit:
                retry_after_seconds = max(1, math.ceil(window.reset_at - now))
                return _RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=retry_after_seconds,
                )
            window.count += 1
            return _RateLimitDecision(
                allowed=True,
                retry_after_seconds=max(1, math.ceil(window.reset_at - now)),
            )

    def _subject_key(self, rule: _RateLimitRule, scope: Scope) -> str:
        """Build a privacy-preserving rate-limit key.

        Args:
            rule: Matching rate-limit rule.
            scope: ASGI request scope containing client metadata.

        Returns:
            SHA-256 hex digest scoped to the rule bucket and request subject.
        """
        subject = self._subject_identifier(scope)
        return hashlib.sha256(f"{rule.bucket}\0{subject}".encode()).hexdigest()

    def _subject_identifier(self, scope: Scope) -> str:
        """Return a hashed client identifier.

        Args:
            scope: ASGI request scope.

        Returns:
            Non-secret subject identifier suitable for hashing into the limiter key.
        """
        client = scope.get("client")
        client_host = ""
        if isinstance(client, tuple) and client:
            raw_host = client[0]
            if isinstance(raw_host, str):
                client_host = raw_host
        return "client:" + hashlib.sha256(client_host.encode("utf-8")).hexdigest()

    def _purge_expired(self, now: float) -> None:
        """Remove expired windows to keep process memory bounded.

        Args:
            now: Current monotonic timestamp.

        Returns:
            None.
        """
        expired_keys = [key for key, window in self._windows.items() if window.reset_at <= now]
        for key in expired_keys:
            del self._windows[key]

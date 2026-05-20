"""HTTP response security headers middleware."""

from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecureHeadersMiddleware:
    """Attach conservative HTTP security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: Downstream ASGI application.
        """
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Add headers to HTTP response start messages.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            """Set security headers before the response is sent.

            Args:
                message: ASGI response message.

            Returns:
                None.
            """
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self._app(scope, receive, send_with_security_headers)

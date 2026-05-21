"""애플리케이션 로깅 설정 + PII redaction.

Logs that flow through the standard :mod:`logging` module are passed through
a :class:`RedactingFilter` that masks common PII payloads (bearer tokens,
email addresses, opaque hex identifiers) before formatting. The filter
targets the *rendered* message string so it works regardless of how caller
code interpolates arguments.
"""

from __future__ import annotations

import logging
import re
import sys

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]+", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "***EMAIL***"),
    (re.compile(r"\b[a-f0-9]{32,}\b"), "***HASH***"),
)
"""Ordered ``(pattern, replacement)`` pairs applied to every log message."""


class RedactingFilter(logging.Filter):
    """Mask common PII patterns in log records before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Replace any PII-shaped substrings in the rendered message.

        Args:
            record: Log record about to be emitted.

        Returns:
            ``True`` so the record continues through the logging pipeline.
        """
        try:
            message = record.getMessage()
        except Exception:
            return True
        for pattern, replacement in _PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = None
        return True


def setup_logging(level: str = "INFO") -> None:
    """루트 로거를 설정한다.

    Args:
        level: 로그 레벨 문자열.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

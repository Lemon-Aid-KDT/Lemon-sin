"""OCR exception types."""

from __future__ import annotations

from src.ocr.base import OCRError


class OCRApiError(OCRError):
    """Raised when an OCR provider call fails.

    Args:
        provider: Bounded OCR provider label.
        message: Error message safe for logs and tests.
    """

    def __init__(self, provider: str, message: str) -> None:
        """Build an OCR API error with provider context.

        Args:
            provider: Bounded OCR provider label.
            message: Provider error summary.
        """
        self.provider = provider
        super().__init__(f"{provider}: {message}")


__all__ = ["OCRApiError", "OCRError"]

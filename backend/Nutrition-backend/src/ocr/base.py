"""OCR adapter contracts for supplement label image analysis.

The OCR layer owns text extraction only. It does not persist raw images, call
LLMs, or make health decisions. Callers must enforce consent and storage policy
before passing images into an adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.vision.base import BoundingBox


class OCRError(RuntimeError):
    """Raised when OCR input validation or text extraction fails."""


@dataclass(frozen=True)
class OCRImageInput:
    """Validated image payload passed to OCR providers.

    Attributes:
        image_bytes: Bounded image bytes. The caller must validate size and MIME type first.
        mime_type: Detected MIME type such as ``image/png``.
        width: Decoded image width in pixels.
        height: Decoded image height in pixels.
        label_region: Optional supplement-label ROI detected by the vision layer.
    """

    image_bytes: bytes
    mime_type: str
    width: int
    height: int
    label_region: BoundingBox | None = None


@dataclass(frozen=True)
class OCRResult:
    """Text extracted from a supplement label image.

    Attributes:
        text: Extracted text. Empty text means the adapter did not produce usable OCR output.
        provider: Bounded provider label for audit and preview metadata.
        confidence: Optional OCR confidence from 0.0 to 1.0.
    """

    text: str
    provider: str
    confidence: float | None = None


class OCRAdapter(ABC):
    """Abstract OCR provider interface.

    Implementations convert validated image bytes into text. They must not store raw
    images or emit medical advice.
    """

    @abstractmethod
    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Extract text from a validated supplement label image.

        Args:
            image: Validated image payload and optional label-region ROI.

        Returns:
            OCR text and provider metadata.

        Raises:
            OCRError: If extraction fails or the provider returns invalid metadata.
        """
        ...

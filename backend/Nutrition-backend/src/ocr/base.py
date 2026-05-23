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
class OCRVertex:
    """Single OCR coordinate vertex.

    Attributes:
        x: Horizontal coordinate in provider-normalized image space.
        y: Vertical coordinate in provider-normalized image space.
    """

    x: float
    y: float


@dataclass(frozen=True)
class OCRBoundingPoly:
    """OCR word bounding polygon.

    Attributes:
        vertices: Polygon vertices around the detected OCR word.
    """

    vertices: tuple[OCRVertex, ...]


@dataclass(frozen=True)
class OCRWord:
    """Coordinate-bearing OCR word.

    Attributes:
        text: Word text emitted by the OCR provider.
        bounding_box: Optional bounding polygon. Missing boxes degrade layout parsing.
        confidence: Optional provider word confidence from 0.0 to 1.0.
    """

    text: str
    bounding_box: OCRBoundingPoly | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class OCRParagraph:
    """OCR paragraph containing words.

    Attributes:
        words: Provider-normalized OCR words.
    """

    words: tuple[OCRWord, ...]


@dataclass(frozen=True)
class OCRBlock:
    """OCR block containing paragraphs.

    Attributes:
        paragraphs: Provider-normalized OCR paragraphs.
        block_type: Optional provider block type.
    """

    paragraphs: tuple[OCRParagraph, ...]
    block_type: str | None = None


@dataclass(frozen=True)
class OCRPage:
    """OCR page layout metadata.

    Attributes:
        blocks: OCR blocks on the page.
        width: Optional page width in provider coordinate units.
        height: Optional page height in provider coordinate units.
    """

    blocks: tuple[OCRBlock, ...]
    width: int | None = None
    height: int | None = None


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
        pages: Optional coordinate-bearing OCR layout pages.
    """

    text: str
    provider: str
    confidence: float | None = None
    pages: tuple[OCRPage, ...] = ()


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

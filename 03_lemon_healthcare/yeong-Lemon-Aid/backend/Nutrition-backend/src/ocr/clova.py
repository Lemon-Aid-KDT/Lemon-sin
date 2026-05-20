"""Compatibility exports for the NAVER Cloud CLOVA OCR adapter."""

from __future__ import annotations

from src.ocr.providers.clova import ClovaOCRAdapter

ClovaOCR = ClovaOCRAdapter

__all__ = ["ClovaOCR", "ClovaOCRAdapter"]

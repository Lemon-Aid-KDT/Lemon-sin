"""Compatibility exports for the Google Vision OCR adapter."""

from __future__ import annotations

from src.ocr.providers.google_vision import GoogleVisionOCRAdapter

GoogleVisionOCR = GoogleVisionOCRAdapter

__all__ = ["GoogleVisionOCR", "GoogleVisionOCRAdapter"]

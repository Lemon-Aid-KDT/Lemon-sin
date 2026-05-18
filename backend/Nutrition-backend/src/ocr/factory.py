"""OCR adapter factory helpers."""

from __future__ import annotations

import logging

from src.config import Settings
from src.llm.ollama_vision import OllamaVisionAssistAdapter
from src.ocr.base import OCRAdapter
from src.ocr.providers.clova import ClovaOCRAdapter
from src.ocr.providers.google_vision import (
    GoogleVisionOCRAdapter,
    build_google_vision_endpoint,
)
from src.ocr.providers.google_vision_auth import (
    GoogleVisionADCAuthHeaders,
    GoogleVisionApiKeyAuthHeaders,
    GoogleVisionAuthHeadersProvider,
)
from src.ocr.providers.paddle import PaddleOCRAdapter
from src.services.supplement_image_analysis import SupplementImageAnalysisAdapters
from src.vision.yolo import YoloLabelDetector

logger = logging.getLogger(__name__)


class OCRConfigurationError(RuntimeError):
    """Raised when OCR settings request a provider that cannot be built."""


def build_supplement_ocr_adapter(settings: Settings) -> OCRAdapter | None:
    """Build the configured supplement-label OCR adapter.

    Args:
        settings: Runtime settings.

    Returns:
        OCR adapter, or None when OCR is intentionally disabled.

    Raises:
        OCRConfigurationError: If the selected provider is missing its required gates.
    """
    if settings.ocr_primary_provider == "none":
        return None
    if settings.ocr_primary_provider == "paddleocr":
        return _build_paddleocr_primary_adapter(settings)
    if settings.ocr_primary_provider == "google_vision":
        return _build_google_vision_adapter(settings)
    raise OCRConfigurationError(
        f"Unsupported OCR_PRIMARY_PROVIDER: {settings.ocr_primary_provider}"
    )


def build_supplement_image_analysis_adapters(settings: Settings) -> SupplementImageAnalysisAdapters:
    """Build the complete supplement image analysis adapter set.

    Args:
        settings: Runtime settings.

    Returns:
        Service adapter bundle for OCR, ROI detection, vision assist, and fallback OCR.

    Raises:
        OCRConfigurationError: If requested adapter settings are incomplete or unsafe.
    """
    return SupplementImageAnalysisAdapters(
        ocr=build_supplement_ocr_adapter(settings),
        vision=_build_vision_adapter(settings),
        multimodal_ocr=_build_multimodal_ocr_adapter(settings),
        fallback_ocr_adapters=tuple(_build_fallback_ocr_adapters(settings)),
    )


def _build_vision_adapter(settings: Settings) -> YoloLabelDetector | None:
    """Build the gated YOLO ROI adapter when enabled.

    Args:
        settings: Runtime settings.

    Returns:
        YOLO ROI detector or None.
    """
    if not settings.enable_vision_classifier:
        return None
    return YoloLabelDetector(settings)


def _build_multimodal_ocr_adapter(settings: Settings) -> OllamaVisionAssistAdapter | None:
    """Build the local Ollama vision assist adapter when a policy can call it.

    Args:
        settings: Runtime settings.

    Returns:
        Ollama vision assist adapter or None.

    Raises:
        OCRConfigurationError: If a multimodal policy is enabled without the gate.
    """
    wants_fallback = settings.multimodal_ocr_assist_policy != "disabled"
    wants_verification = settings.enable_multimodal_verification
    if not wants_fallback and not wants_verification:
        return None
    if not settings.enable_multimodal_llm:
        raise OCRConfigurationError(
            "ENABLE_MULTIMODAL_LLM=true is required for Ollama vision assist."
        )
    return OllamaVisionAssistAdapter(settings)


def _build_paddleocr_primary_adapter(settings: Settings) -> PaddleOCRAdapter:
    """Build PaddleOCR as the primary OCR adapter.

    Args:
        settings: Runtime settings.

    Returns:
        PaddleOCR adapter.

    Raises:
        OCRConfigurationError: If local OCR is disabled.
    """
    if not settings.enable_local_ocr:
        raise OCRConfigurationError(
            "ENABLE_LOCAL_OCR=true is required when OCR_PRIMARY_PROVIDER=paddleocr."
        )
    return PaddleOCRAdapter(settings)


def _build_fallback_ocr_adapters(settings: Settings) -> list[OCRAdapter]:
    """Build optional secondary OCR fallback adapters in configured order.

    PaddleOCR is omitted from the secondary list when it is already the primary
    provider, so the same adapter is never invoked twice in a single pipeline.

    Args:
        settings: Runtime settings.

    Returns:
        OCR fallback adapters.
    """
    adapters: list[OCRAdapter] = []
    if settings.enable_local_ocr and settings.ocr_primary_provider != "paddleocr":
        adapters.append(PaddleOCRAdapter(settings))
    if settings.enable_clova_ocr:
        adapters.append(ClovaOCRAdapter(settings))
    return adapters


def _build_google_vision_adapter(settings: Settings) -> GoogleVisionOCRAdapter:
    """Build a Google Vision OCR adapter from settings.

    Args:
        settings: Runtime settings.

    Returns:
        Google Vision OCR adapter.

    Raises:
        OCRConfigurationError: If required Google Vision settings are missing.
    """
    if not settings.allow_external_ocr:
        raise OCRConfigurationError("ALLOW_EXTERNAL_OCR=true is required for Google Vision.")
    if settings.environment == "production" and settings.google_vision_auth_mode != "adc":
        raise OCRConfigurationError("GOOGLE_VISION_AUTH_MODE=adc is required in production.")
    if settings.google_vision_auth_mode == "api_key":
        if settings.google_cloud_api_key is None:
            raise OCRConfigurationError("GOOGLE_CLOUD_API_KEY is required for Google Vision.")
        if settings.environment == "staging":
            logger.warning(
                "Google Vision api_key mode active in staging; ADC migration recommended.",
            )
        auth_headers: GoogleVisionAuthHeadersProvider = GoogleVisionApiKeyAuthHeaders(
            settings.google_cloud_api_key
        )
    else:
        if settings.google_cloud_project is None:
            raise OCRConfigurationError(
                "GOOGLE_CLOUD_PROJECT is required for Google Vision ADC mode."
            )
        auth_headers = GoogleVisionADCAuthHeaders(project_id=settings.google_cloud_project)

    try:
        endpoint = build_google_vision_endpoint(
            project_id=settings.google_cloud_project,
            location=settings.google_vision_location,
        )
    except ValueError as exc:
        raise OCRConfigurationError(str(exc)) from exc

    return GoogleVisionOCRAdapter(
        auth_headers=auth_headers,
        endpoint=endpoint,
        feature=settings.google_vision_feature,
        language_hints=settings.google_vision_language_hints,
        timeout_seconds=settings.google_vision_timeout_seconds,
        max_retries=settings.google_vision_max_retries,
    )

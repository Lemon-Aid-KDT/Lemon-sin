"""OCR adapter factory helpers."""

from __future__ import annotations

from typing import Literal

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


class OCRConfigurationError(RuntimeError):
    """Raised when OCR settings request a provider that cannot be built."""


SupplementOCRProviderSelector = Literal["configured", "google_vision", "paddleocr"]


def is_external_ocr_pipeline_enabled(
    settings: Settings,
    provider_selector: SupplementOCRProviderSelector = "configured",
) -> bool:
    """Return whether the configured OCR chain may call an external provider.

    Args:
        settings: Runtime settings.
        provider_selector: Per-request provider selector. ``configured`` uses
            the settings-driven provider chain.

    Returns:
        True when Google Vision primary or CLOVA fallback may send image bytes
        to an external OCR provider.
    """
    if provider_selector == "google_vision":
        return True
    if provider_selector == "paddleocr":
        return False
    return settings.ocr_primary_provider == "google_vision" or settings.enable_clova_ocr


def build_supplement_ocr_adapter(settings: Settings) -> OCRAdapter | None:
    """Build the configured supplement-label OCR adapter.

    Args:
        settings: Runtime settings.

    Returns:
        OCR adapter, or None when OCR is intentionally disabled.

    Raises:
        OCRConfigurationError: If the requested OCR provider is not configured.
    """
    if settings.ocr_primary_provider == "none":
        return None
    if settings.ocr_primary_provider == "paddleocr":
        return _build_paddleocr_adapter(settings)
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


def build_supplement_image_analysis_adapters_for_provider(
    settings: Settings,
    provider_selector: SupplementOCRProviderSelector,
    *,
    configured_adapters: SupplementImageAnalysisAdapters | None = None,
) -> SupplementImageAnalysisAdapters:
    """Build adapters for a request-selected OCR provider.

    Args:
        settings: Runtime settings.
        provider_selector: Provider requested by the client.
        configured_adapters: Already-built default adapter bundle used when
            ``provider_selector`` is ``configured``.

    Returns:
        Adapter bundle constrained to the selected OCR provider.

    Raises:
        OCRConfigurationError: If the requested provider is not configured.
    """
    if provider_selector == "configured":
        return configured_adapters or build_supplement_image_analysis_adapters(settings)
    if provider_selector == "google_vision":
        return SupplementImageAnalysisAdapters(
            ocr=_build_google_vision_adapter(settings),
            vision=_build_vision_adapter(settings),
            multimodal_ocr=_build_multimodal_ocr_adapter(settings),
            fallback_ocr_adapters=(),
        )
    if provider_selector == "paddleocr":
        return SupplementImageAnalysisAdapters(
            ocr=_build_paddleocr_adapter(settings),
            vision=_build_vision_adapter(settings),
            multimodal_ocr=_build_multimodal_ocr_adapter(settings),
            fallback_ocr_adapters=(),
        )
    raise OCRConfigurationError(f"Unsupported OCR provider selector: {provider_selector}")


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


def _build_fallback_ocr_adapters(settings: Settings) -> list[OCRAdapter]:
    """Build optional secondary OCR fallback adapters in P1-2 fallback order.

    Args:
        settings: Runtime settings.

    Returns:
        OCR fallback adapters.
    """
    adapters: list[OCRAdapter] = []
    if settings.enable_clova_ocr:
        _validate_clova_fallback_settings(settings)
        adapters.append(ClovaOCRAdapter(settings))
    if settings.enable_local_ocr and settings.ocr_primary_provider != "paddleocr":
        adapters.append(PaddleOCRAdapter(settings))
    return adapters


def _build_paddleocr_adapter(settings: Settings) -> PaddleOCRAdapter:
    """Build a local PaddleOCR adapter from settings.

    Args:
        settings: Runtime settings.

    Returns:
        PaddleOCR adapter.

    Raises:
        OCRConfigurationError: If local OCR is disabled.
    """
    if not settings.enable_local_ocr:
        raise OCRConfigurationError("ENABLE_LOCAL_OCR=true is required for PaddleOCR.")
    return PaddleOCRAdapter(settings)


def _validate_clova_fallback_settings(settings: Settings) -> None:
    """Validate CLOVA fallback settings before image bytes are read.

    Args:
        settings: Runtime settings.

    Raises:
        OCRConfigurationError: If external OCR gate or credentials are missing.
    """
    if not settings.allow_external_ocr:
        raise OCRConfigurationError("ALLOW_EXTERNAL_OCR=true is required for CLOVA OCR.")
    if not settings.clova_ocr_api_url:
        raise OCRConfigurationError("CLOVA_OCR_API_URL is required for CLOVA OCR.")
    if settings.clova_ocr_secret is None:
        raise OCRConfigurationError("CLOVA_OCR_SECRET is required for CLOVA OCR.")


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

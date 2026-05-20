"""OCR adapter factory tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.llm.ollama_vision import OllamaVisionAssistAdapter
from src.ocr.factory import (
    OCRConfigurationError,
    build_supplement_image_analysis_adapters,
    build_supplement_image_analysis_adapters_for_provider,
    build_supplement_ocr_adapter,
    is_external_ocr_pipeline_enabled,
)
from src.ocr.providers.clova import ClovaOCRAdapter
from src.ocr.providers.google_vision import GoogleVisionOCRAdapter
from src.ocr.providers.paddle import PaddleOCRAdapter
from src.vision.yolo import YoloLabelDetector


def test_factory_builds_paddleocr_primary_by_default() -> None:
    """Verify PaddleOCR is the default primary OCR adapter."""
    assert isinstance(build_supplement_ocr_adapter(Settings(_env_file=None)), PaddleOCRAdapter)


def test_factory_requires_local_ocr_gate_for_paddleocr_primary() -> None:
    """Verify PaddleOCR primary fails closed when local OCR is disabled."""
    settings = Settings(_env_file=None, ocr_primary_provider="paddleocr", enable_local_ocr=False)

    with pytest.raises(OCRConfigurationError, match="ENABLE_LOCAL_OCR"):
        build_supplement_ocr_adapter(settings)


def test_factory_returns_none_when_primary_provider_disabled() -> None:
    """Verify OCR can still be disabled explicitly."""
    assert (
        build_supplement_ocr_adapter(Settings(_env_file=None, ocr_primary_provider="none")) is None
    )


def test_factory_requires_external_ocr_gate_for_google_vision() -> None:
    """Verify Google Vision cannot be built while external OCR is disabled."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        google_cloud_api_key=SecretStr("test-key"),
    )

    with pytest.raises(OCRConfigurationError, match="ALLOW_EXTERNAL_OCR"):
        build_supplement_ocr_adapter(settings)


def test_factory_requires_api_key_for_api_key_mode() -> None:
    """Verify API-key mode fails closed without a key."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
    )

    with pytest.raises(OCRConfigurationError, match="GOOGLE_CLOUD_API_KEY"):
        build_supplement_ocr_adapter(settings)


def test_factory_builds_google_vision_adapter_for_api_key_mode() -> None:
    """Verify local Google Vision opt-in builds an adapter."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_cloud_api_key=SecretStr("test-key"),
        google_vision_language_hints=["ko", "en"],
    )

    adapter = build_supplement_ocr_adapter(settings)

    assert isinstance(adapter, GoogleVisionOCRAdapter)


def test_factory_requires_project_for_adc_mode() -> None:
    """Verify ADC mode requires a quota project."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_vision_auth_mode="adc",
    )

    with pytest.raises(OCRConfigurationError, match="GOOGLE_CLOUD_PROJECT"):
        build_supplement_ocr_adapter(settings)


def test_analysis_factory_builds_paddleocr_bundle_by_default() -> None:
    """Verify the complete analysis bundle uses local PaddleOCR by default."""
    adapters = build_supplement_image_analysis_adapters(Settings(_env_file=None))

    assert isinstance(adapters.ocr, PaddleOCRAdapter)
    assert adapters.vision is None
    assert adapters.multimodal_ocr is None
    assert adapters.fallback_ocr_adapters == ()


def test_analysis_factory_builds_yolo_adapter_when_gate_enabled() -> None:
    """Verify the analysis factory wires the gated YOLO detector."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(_env_file=None, enable_vision_classifier=True)
    )

    assert isinstance(adapters.vision, YoloLabelDetector)


def test_analysis_factory_requires_multimodal_gate_for_policy() -> None:
    """Verify multimodal policy cannot silently run while the gate is off."""
    settings = Settings(_env_file=None, multimodal_ocr_assist_policy="low_confidence")

    with pytest.raises(OCRConfigurationError, match="ENABLE_MULTIMODAL_LLM"):
        build_supplement_image_analysis_adapters(settings)


def test_analysis_factory_builds_multimodal_adapter_when_policy_enabled() -> None:
    """Verify the local vision assist adapter is injected when gated."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(
            _env_file=None,
            enable_multimodal_llm=True,
            multimodal_ocr_assist_policy="ocr_empty_only",
        )
    )

    assert isinstance(adapters.multimodal_ocr, OllamaVisionAssistAdapter)


def test_analysis_factory_builds_optional_fallback_adapters() -> None:
    """Verify optional fallback adapters prefer CLOVA for P1-2 confidence fallback."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            enable_clova_ocr=True,
            allow_external_ocr=True,
            ocr_primary_provider="none",
            clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
            clova_ocr_secret=SecretStr("secret"),
        )
    )

    assert isinstance(adapters.fallback_ocr_adapters[0], ClovaOCRAdapter)
    assert isinstance(adapters.fallback_ocr_adapters[1], PaddleOCRAdapter)


def test_analysis_factory_builds_local_only_paddle_fallback_without_external_gate() -> None:
    """Verify PaddleOCR fallback can be configured without external OCR consent."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(_env_file=None, ocr_primary_provider="none", enable_local_ocr=True)
    )

    assert adapters.ocr is None
    assert len(adapters.fallback_ocr_adapters) == 1
    assert isinstance(adapters.fallback_ocr_adapters[0], PaddleOCRAdapter)


def test_analysis_factory_builds_google_vision_as_request_selected_provider() -> None:
    """Verify request-selected Google Vision does not include fallback providers."""
    adapters = build_supplement_image_analysis_adapters_for_provider(
        Settings(
            _env_file=None,
            allow_external_ocr=True,
            google_cloud_api_key=SecretStr("test-key"),
            enable_local_ocr=True,
        ),
        "google_vision",
    )

    assert isinstance(adapters.ocr, GoogleVisionOCRAdapter)
    assert adapters.fallback_ocr_adapters == ()


def test_analysis_factory_builds_paddleocr_as_request_selected_provider() -> None:
    """Verify request-selected PaddleOCR runs as the only OCR provider."""
    adapters = build_supplement_image_analysis_adapters_for_provider(
        Settings(_env_file=None, enable_local_ocr=True),
        "paddleocr",
    )

    assert isinstance(adapters.ocr, PaddleOCRAdapter)
    assert adapters.fallback_ocr_adapters == ()


def test_factory_detects_external_ocr_when_clova_fallback_enabled() -> None:
    """Verify external OCR consent is required for CLOVA fallback too."""
    settings = Settings(_env_file=None, enable_clova_ocr=True)

    assert is_external_ocr_pipeline_enabled(settings) is True


def test_factory_detects_external_ocr_for_request_selected_google_only() -> None:
    """Verify request-level provider selection drives external consent routing."""
    settings = Settings(_env_file=None, enable_clova_ocr=True)

    assert is_external_ocr_pipeline_enabled(settings, "google_vision") is True
    assert is_external_ocr_pipeline_enabled(settings, "paddleocr") is False


def test_factory_rejects_clova_fallback_without_external_gate() -> None:
    """Verify CLOVA cannot be built without the external OCR gate."""
    settings = Settings(
        _env_file=None,
        enable_clova_ocr=True,
        clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
        clova_ocr_secret=SecretStr("secret"),
    )

    with pytest.raises(OCRConfigurationError, match="ALLOW_EXTERNAL_OCR"):
        build_supplement_image_analysis_adapters(settings)


def test_factory_rejects_clova_fallback_without_credentials() -> None:
    """Verify CLOVA fallback fails closed before request image bytes are used."""
    settings = Settings(
        _env_file=None,
        enable_clova_ocr=True,
        allow_external_ocr=True,
    )

    with pytest.raises(OCRConfigurationError, match="CLOVA_OCR_API_URL"):
        build_supplement_image_analysis_adapters(settings)

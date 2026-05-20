"""OCR adapter factory tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.llm.ollama_vision import OllamaVisionAssistAdapter
from src.ocr import factory as ocr_factory
from src.ocr.factory import (
    OCRConfigurationError,
    build_supplement_image_analysis_adapters,
    build_supplement_ocr_adapter,
)
from src.ocr.providers.clova import ClovaOCRAdapter
from src.ocr.providers.google_vision import GoogleVisionOCRAdapter
from src.ocr.providers.paddle import PaddleOCRAdapter
from src.vision.yolo import YoloLabelDetector


def test_factory_returns_none_when_primary_provider_disabled() -> None:
    """Verify OCR remains intake-only by default."""
    assert build_supplement_ocr_adapter(Settings(_env_file=None)) is None


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


def test_analysis_factory_returns_empty_bundle_by_default() -> None:
    """Verify the complete analysis bundle preserves intake-only defaults."""
    adapters = build_supplement_image_analysis_adapters(Settings(_env_file=None))

    assert adapters.ocr is None
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


def test_factory_warns_when_api_key_mode_used_in_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify staging api_key mode emits the ADC migration warning."""
    settings = Settings(
        _env_file=None,
        environment="staging",
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_vision_auth_mode="api_key",
        allow_google_api_key_auth=True,
        google_cloud_project="staging-project",
        google_cloud_api_key=SecretStr("test-key"),
    )
    warnings: list[str] = []

    def _record_warning(message: str) -> None:
        warnings.append(message)

    monkeypatch.setattr(ocr_factory.logger, "warning", _record_warning)

    adapter = ocr_factory.build_supplement_ocr_adapter(settings)

    assert isinstance(adapter, GoogleVisionOCRAdapter)
    assert any("ADC migration recommended" in message for message in warnings)


def test_analysis_factory_builds_optional_fallback_adapters() -> None:
    """Verify optional fallback adapters are appended in local-before-external order."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(
            _env_file=None,
            enable_local_ocr=True,
            enable_clova_ocr=True,
            allow_external_ocr=True,
            clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
            clova_ocr_secret=SecretStr("secret"),
        )
    )

    assert isinstance(adapters.fallback_ocr_adapters[0], PaddleOCRAdapter)
    assert isinstance(adapters.fallback_ocr_adapters[1], ClovaOCRAdapter)

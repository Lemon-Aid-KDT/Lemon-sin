"""OCR adapter factory tests."""

from __future__ import annotations

import logging

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.llm.ollama_vision import OllamaVisionAssistAdapter
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
    """Verify intake-only mode is reachable via an explicit opt-out."""
    settings = Settings(_env_file=None, ocr_primary_provider="none")
    assert build_supplement_ocr_adapter(settings) is None


def test_factory_builds_paddleocr_primary_by_default() -> None:
    """Verify PaddleOCR is the default primary OCR adapter."""
    adapter = build_supplement_ocr_adapter(Settings(_env_file=None))
    assert isinstance(adapter, PaddleOCRAdapter)


def test_factory_builds_paddleocr_primary_when_selected() -> None:
    """Verify explicit PaddleOCR selection returns PaddleOCRAdapter."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="paddleocr",
        enable_local_ocr=True,
    )
    adapter = build_supplement_ocr_adapter(settings)
    assert isinstance(adapter, PaddleOCRAdapter)


def test_factory_paddleocr_primary_requires_local_ocr_gate() -> None:
    """Verify PaddleOCR primary cannot run while local OCR is disabled."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="paddleocr",
        enable_local_ocr=False,
    )
    with pytest.raises(OCRConfigurationError, match="ENABLE_LOCAL_OCR"):
        build_supplement_ocr_adapter(settings)


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
    """Verify API-key mode fails closed without a key.

    API-key mode now requires ALLOW_GOOGLE_API_KEY_AUTH=true at the Settings
    layer; this test focuses on the factory-level GOOGLE_CLOUD_API_KEY guard.
    """
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_vision_auth_mode="api_key",
        allow_google_api_key_auth=True,
    )

    with pytest.raises(OCRConfigurationError, match="GOOGLE_CLOUD_API_KEY"):
        build_supplement_ocr_adapter(settings)


def test_factory_builds_google_vision_adapter_for_api_key_mode() -> None:
    """Verify local Google Vision opt-in builds an adapter."""
    settings = Settings(
        _env_file=None,
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_vision_auth_mode="api_key",
        allow_google_api_key_auth=True,
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
    """Verify the default bundle wires PaddleOCR as the primary OCR adapter."""
    adapters = build_supplement_image_analysis_adapters(Settings(_env_file=None))

    assert isinstance(adapters.ocr, PaddleOCRAdapter)
    assert adapters.vision is None
    assert adapters.multimodal_ocr is None
    assert adapters.fallback_ocr_adapters == ()


def test_analysis_factory_returns_intake_only_bundle_when_provider_disabled() -> None:
    """Verify the analysis bundle preserves intake-only when explicitly opted out."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(_env_file=None, ocr_primary_provider="none", enable_local_ocr=False)
    )

    assert adapters.ocr is None
    assert adapters.vision is None
    assert adapters.multimodal_ocr is None
    assert adapters.fallback_ocr_adapters == ()


def test_analysis_factory_skips_paddleocr_fallback_when_primary() -> None:
    """Verify PaddleOCR is not duplicated in the fallback list when already primary."""
    adapters = build_supplement_image_analysis_adapters(
        Settings(
            _env_file=None,
            ocr_primary_provider="paddleocr",
            enable_local_ocr=True,
        )
    )

    assert isinstance(adapters.ocr, PaddleOCRAdapter)
    assert all(not isinstance(item, PaddleOCRAdapter) for item in adapters.fallback_ocr_adapters)


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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify staging api_key mode emits the ADC migration warning.

    Staging is the only environment that still permits api_key auth via an
    explicit opt-in gate; an audit-grade warning at build time keeps the
    migration debt visible to operators.
    """
    settings = Settings(
        _env_file=None,
        environment="staging",
        auth_mode="jwt",
        allowed_hosts=["staging.example.com"],
        ocr_primary_provider="google_vision",
        allow_external_ocr=True,
        google_vision_auth_mode="api_key",
        allow_google_api_key_auth=True,
        google_cloud_project="staging-project",
        google_cloud_api_key=SecretStr("test-key"),
    )

    with caplog.at_level(logging.WARNING, logger="src.ocr.factory"):
        adapter = build_supplement_ocr_adapter(settings)

    assert isinstance(adapter, GoogleVisionOCRAdapter)
    warnings = [
        record.getMessage()
        for record in caplog.records
        if "ADC migration recommended" in record.getMessage()
    ]
    assert warnings, "Expected staging api_key warning to be emitted"


def test_analysis_factory_builds_optional_fallback_adapters() -> None:
    """Verify optional fallback adapters are appended in local-before-external order.

    PaddleOCR is opted out as primary here so the legacy local-before-external
    fallback ordering can be exercised.
    """
    adapters = build_supplement_image_analysis_adapters(
        Settings(
            _env_file=None,
            ocr_primary_provider="none",
            enable_local_ocr=True,
            enable_clova_ocr=True,
            allow_external_ocr=True,
            clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
            clova_ocr_secret=SecretStr("secret"),
        )
    )

    assert isinstance(adapters.fallback_ocr_adapters[0], PaddleOCRAdapter)
    assert isinstance(adapters.fallback_ocr_adapters[1], ClovaOCRAdapter)

"""Sanitized runtime readiness checks."""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.models.schemas.readiness import (
    ReadinessComponent,
    ReadinessOverallStatus,
    ReadinessResponse,
)
from src.services.governance import build_governance_readiness_component


def build_readiness_response(settings: Settings) -> ReadinessResponse:
    """Build a sanitized readiness response.

    This check is intentionally configuration-oriented. It does not call vendor
    APIs or expose secrets. Live provider smoke tests belong in deployment
    pipelines with explicit credentials and audit controls.

    Args:
        settings: Runtime settings.

    Returns:
        Sanitized readiness response.
    """
    components = [
        _auth_component(settings),
        _cors_host_component(settings),
        _rate_limit_component(settings),
        _google_vision_component(settings),
        _clova_component(settings),
        _local_ocr_component(settings),
        _ollama_component(settings),
        _kdris_component(settings),
        build_governance_readiness_component(settings),
    ]
    return ReadinessResponse(
        status=_overall_status(components),
        environment=settings.environment,
        deployment_exposure=settings.deployment_exposure,
        components=components,
    )


def _overall_status(components: list[ReadinessComponent]) -> ReadinessOverallStatus:
    """Resolve overall readiness from component statuses.

    Args:
        components: Component readiness list.

    Returns:
        Overall readiness status.
    """
    statuses = {component.status for component in components}
    if "blocked" in statuses or "not_ready" in statuses:
        return "not_ready"
    if "not_configured" in statuses:
        return "degraded"
    return "ready"


def _auth_component(settings: Settings) -> ReadinessComponent:
    """Return auth readiness.

    Args:
        settings: Runtime settings.

    Returns:
        Auth readiness component.
    """
    public_runtime = settings.environment == "production" or (
        settings.environment == "staging" and settings.deployment_exposure == "public"
    )
    if public_runtime and settings.auth_mode != "jwt":
        return ReadinessComponent(
            name="auth",
            status="blocked",
            message_code="jwt_required_for_public_runtime",
        )
    if settings.auth_mode == "jwt":
        missing = [
            name
            for name, value in (
                ("jwt_issuer", settings.jwt_issuer),
                ("jwt_audience", settings.jwt_audience),
                ("jwt_jwks_url", settings.jwt_jwks_url),
            )
            if not value
        ]
        return ReadinessComponent(
            name="auth",
            status="not_ready" if missing else "ready",
            message_code="jwt_missing_fields" if missing else "jwt_configured",
            details={"missing_count": len(missing)},
        )
    return ReadinessComponent(
        name="auth",
        status="ready",
        message_code="development_auth_disabled",
    )


def _cors_host_component(settings: Settings) -> ReadinessComponent:
    """Return CORS and trusted-host readiness.

    Args:
        settings: Runtime settings.

    Returns:
        CORS/host readiness component.
    """
    public_runtime = settings.environment == "production" or (
        settings.environment == "staging" and settings.deployment_exposure == "public"
    )
    if public_runtime and not settings.allowed_hosts:
        return ReadinessComponent(
            name="cors_trusted_host",
            status="not_ready",
            message_code="allowed_hosts_required",
        )
    return ReadinessComponent(
        name="cors_trusted_host",
        status="ready",
        message_code="cors_trusted_host_configured",
        details={
            "allowed_hosts_count": len(settings.allowed_hosts),
            "allowed_origins_count": len(settings.allowed_origins),
        },
    )


def _rate_limit_component(settings: Settings) -> ReadinessComponent:
    """Return rate limit readiness.

    Args:
        settings: Runtime settings.

    Returns:
        Rate limit readiness component.
    """
    public_runtime = settings.environment == "production" or (
        settings.environment == "staging" and settings.deployment_exposure == "public"
    )
    if public_runtime and not settings.rate_limit_enabled:
        return ReadinessComponent(
            name="rate_limit",
            status="not_ready",
            message_code="rate_limit_required_for_public_runtime",
        )
    return ReadinessComponent(
        name="rate_limit",
        status="ready" if settings.rate_limit_enabled else "not_configured",
        message_code="rate_limit_enabled" if settings.rate_limit_enabled else "rate_limit_disabled",
    )


def _google_vision_component(settings: Settings) -> ReadinessComponent:
    """Return Google Vision readiness.

    Args:
        settings: Runtime settings.

    Returns:
        Google Vision readiness component.
    """
    if settings.ocr_primary_provider != "google_vision":
        return ReadinessComponent(
            name="google_vision_ocr",
            status="not_configured",
            message_code="primary_google_vision_disabled",
        )
    configured = settings.allow_external_ocr and (
        settings.google_vision_auth_mode == "adc" or settings.google_cloud_api_key is not None
    )
    return ReadinessComponent(
        name="google_vision_ocr",
        status="ready" if configured else "not_ready",
        message_code=(
            "google_vision_configured"
            if configured
            else "google_vision_missing_credentials_or_consent"
        ),
        details={
            "auth_mode": settings.google_vision_auth_mode,
            "location": settings.google_vision_location,
        },
    )


def _clova_component(settings: Settings) -> ReadinessComponent:
    """Return CLOVA OCR readiness.

    Args:
        settings: Runtime settings.

    Returns:
        CLOVA readiness component.
    """
    if not settings.enable_clova_ocr:
        return ReadinessComponent(
            name="clova_ocr",
            status="not_configured",
            message_code="clova_disabled",
        )
    configured = (
        settings.allow_external_ocr
        and bool(settings.clova_ocr_api_url)
        and settings.clova_ocr_secret is not None
    )
    return ReadinessComponent(
        name="clova_ocr",
        status="ready" if configured else "not_ready",
        message_code="clova_configured" if configured else "clova_missing_config",
    )


def _local_ocr_component(settings: Settings) -> ReadinessComponent:
    """Return local OCR readiness.

    Args:
        settings: Runtime settings.

    Returns:
        Local OCR readiness component.
    """
    recognition_model_dir = settings.local_ocr_text_recognition_model_dir
    detection_model_dir = settings.local_ocr_text_detection_model_dir
    return ReadinessComponent(
        name="local_ocr",
        status="ready" if settings.enable_local_ocr else "not_configured",
        message_code="local_ocr_enabled" if settings.enable_local_ocr else "local_ocr_disabled",
        details={
            "primary_provider": settings.ocr_primary_provider,
            "provider": settings.local_ocr_provider,
            "language": settings.local_ocr_language,
            "engine": settings.local_ocr_engine,
            "device_configured": bool(settings.local_ocr_device),
            "paddlex_configured": bool(settings.local_ocr_paddlex_config),
            "recognition_model_dir_configured": bool(recognition_model_dir),
            "detection_model_dir_configured": bool(detection_model_dir),
            "recognition_model_dir_exists": _configured_path_exists(recognition_model_dir),
            "detection_model_dir_exists": _configured_path_exists(detection_model_dir),
            "runtime_probe": "not_run",
        },
    )


def _configured_path_exists(path_value: str | None) -> bool:
    """Return whether an optional configured path exists.

    Args:
        path_value: Optional filesystem path string.

    Returns:
        True only when a non-empty path is configured and exists.
    """
    if not path_value:
        return False
    return Path(path_value).exists()


def _ollama_component(settings: Settings) -> ReadinessComponent:
    """Return Ollama readiness.

    Args:
        settings: Runtime settings.

    Returns:
        Ollama readiness component.
    """
    configured = bool(settings.ollama_base_url and settings.ollama_model)
    return ReadinessComponent(
        name="ollama",
        status="ready" if configured else "not_ready",
        message_code="ollama_configured" if configured else "ollama_missing_config",
        details={"external_llm_allowed": settings.allow_external_llm},
    )


def _kdris_component(settings: Settings) -> ReadinessComponent:
    """Return KDRI dataset readiness.

    Args:
        settings: Runtime settings.

    Returns:
        KDRI readiness component.
    """
    official_ready = settings.kdris_data_version == "2025" and bool(settings.kdris_data_path)
    if settings.environment == "production" and not official_ready:
        return ReadinessComponent(
            name="kdri_reference",
            status="not_ready",
            message_code="official_2025_kdri_required",
        )
    return ReadinessComponent(
        name="kdri_reference",
        status="ready" if official_ready else "not_configured",
        message_code=(
            "official_2025_kdri_configured" if official_ready else "sample_kdri_or_missing_path"
        ),
        details={"data_version": settings.kdris_data_version},
    )

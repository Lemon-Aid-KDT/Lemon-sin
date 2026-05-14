"""Application settings security tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src.config import DEFAULT_DATABASE_URL, DEFAULT_PRIVACY_HASH_SECRET, Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
READINESS_SETTINGS_PATH = PROJECT_ROOT / "config" / "implementation-readiness.settings.json"


def _load_json_object(path: Path) -> dict[str, object]:
    """Load a JSON document and verify it is an object.

    Args:
        path: JSON file path.

    Returns:
        Parsed JSON object with string keys.
    """
    raw_value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw_value, dict)
    parsed: dict[str, object] = {}
    for key, value in raw_value.items():
        assert isinstance(key, str)
        parsed[key] = value
    return parsed


def _object_field(mapping: dict[str, object], key: str) -> dict[str, object]:
    """Return a nested JSON object field.

    Args:
        mapping: Parent JSON object.
        key: Nested object key.

    Returns:
        Nested JSON object with string keys.
    """
    raw_value = mapping[key]
    assert isinstance(raw_value, dict)
    parsed: dict[str, object] = {}
    for nested_key, nested_value in raw_value.items():
        assert isinstance(nested_key, str)
        parsed[nested_key] = nested_value
    return parsed


def _valid_production_kwargs() -> dict[str, Any]:
    """Return a valid production settings baseline.

    Returns:
        Keyword arguments accepted by Settings.
    """
    return {
        "environment": "production",
        "database_url": "postgresql+asyncpg://lemon_prod:secret@db.example.com:5432/lemon",
        "allowed_origins": ["https://app.example.com"],
        "allowed_hosts": ["api.example.com"],
        "auth_mode": "jwt",
        "jwt_issuer": "https://auth.example.com/",
        "jwt_audience": "lemon-api",
        "jwt_jwks_url": "https://auth.example.com/.well-known/jwks.json",
        "jwt_expected_token_type": "at+jwt",
        "privacy_hash_secret": "prod-privacy-hash-secret-at-least-32",
        "kdris_data_version": "2025",
        "kdris_data_path": "data/kdris/kdris_2025.csv",
        "allow_sample_kdris": False,
    }


def test_default_development_settings_load() -> None:
    """Verify development defaults remain usable for local work."""
    settings = Settings()

    assert settings.environment == "development"
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "testserver" in settings.allowed_hosts
    assert settings.auth_mode == "disabled"
    assert settings.supplement_image_max_bytes == 5 * 1024 * 1024
    assert settings.supplement_image_max_pixels == 12_000_000
    assert settings.supplement_preview_ttl_minutes == 30
    assert not settings.feature_hall_lite_weight_prediction
    assert settings.weight_prediction_engine == "static_7step"
    assert settings.feature_prescription_ocr_intake is False
    assert settings.feature_lab_result_ocr_intake is False
    assert settings.feature_dosage_change_recommendation is False
    assert settings.feature_medication_safety_alert is False
    assert settings.enable_multimodal_llm is False
    assert settings.multimodal_ocr_assist_policy == "disabled"
    assert settings.enable_vision_classifier is False
    assert settings.vision_roi_min_confidence == 0.50
    assert settings.vision_roi_allowed_classes == [
        "supplement_label",
        "supplement_bottle",
        "blister_pack",
    ]


@pytest.mark.parametrize(
    "database_url",
    (
        "sqlite+aiosqlite:///tmp/lemon.db",
        "sqlite:///tmp/lemon.db",
        "postgresql://lemon:lemon@localhost:5432/lemon",
        "mysql+aiomysql://lemon:lemon@localhost:3306/lemon",
    ),
)
def test_database_url_must_use_postgresql_asyncpg(database_url: str) -> None:
    """Verify every runtime environment is pinned to PostgreSQL asyncpg."""
    with pytest.raises(ValidationError, match=r"postgresql\+asyncpg"):
        Settings(database_url=database_url)


def test_production_rejects_development_database_url() -> None:
    """Verify production cannot boot with the development database URL."""
    kwargs = _valid_production_kwargs()
    kwargs["database_url"] = DEFAULT_DATABASE_URL

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(**kwargs)


def test_production_rejects_debug_logging() -> None:
    """Verify production cannot boot with DEBUG logging."""
    kwargs = _valid_production_kwargs()
    kwargs["log_level"] = "DEBUG"

    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(**kwargs)


def test_production_rejects_external_llm() -> None:
    """Verify production cannot enable external LLM calls by default."""
    kwargs = _valid_production_kwargs()
    kwargs["allow_external_llm"] = True

    with pytest.raises(ValidationError, match="ALLOW_EXTERNAL_LLM"):
        Settings(**kwargs)


def test_production_rejects_wildcard_origins_and_hosts() -> None:
    """Verify production requires explicit origins and hosts."""
    kwargs = _valid_production_kwargs()
    kwargs["allowed_origins"] = ["*"]
    kwargs["allowed_hosts"] = ["*"]

    with pytest.raises(ValidationError, match="wildcards"):
        Settings(**kwargs)


def test_production_requires_jwt_configuration() -> None:
    """Verify production user apps must be configured for OAuth/OIDC JWT."""
    kwargs = _valid_production_kwargs()
    kwargs["auth_mode"] = "disabled"
    kwargs["jwt_issuer"] = None

    with pytest.raises(ValidationError, match="AUTH_MODE=jwt"):
        Settings(**kwargs)


def test_production_rejects_sample_kdris_fixture() -> None:
    """Verify production cannot use the local KDRIs sample fixture."""
    kwargs = _valid_production_kwargs()
    kwargs["kdris_data_version"] = "2020-sample"
    kwargs["allow_sample_kdris"] = True

    with pytest.raises(ValidationError, match="KDRIS_DATA_VERSION=2025"):
        Settings(**kwargs)


def test_production_requires_explicit_kdris_data_path() -> None:
    """Verify production must explicitly pin the reviewed KDRIs dataset path."""
    kwargs = _valid_production_kwargs()
    kwargs["kdris_data_path"] = None

    with pytest.raises(ValidationError, match="KDRIS_DATA_PATH"):
        Settings(**kwargs)


def test_production_rejects_default_privacy_hash_secret() -> None:
    """Verify production audit hashes cannot use the development HMAC secret."""
    kwargs = _valid_production_kwargs()
    kwargs["privacy_hash_secret"] = DEFAULT_PRIVACY_HASH_SECRET

    with pytest.raises(ValidationError, match="PRIVACY_HASH_SECRET"):
        Settings(**kwargs)


def test_production_rejects_hall_lite_weight_prediction_without_signoff() -> None:
    """Verify production cannot enable Hall-lite before validation sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs["feature_hall_lite_weight_prediction"] = True

    with pytest.raises(ValidationError, match="FEATURE_HALL_LITE_WEIGHT_PREDICTION"):
        Settings(**kwargs)


def test_production_rejects_multimodal_llm_without_signoff() -> None:
    """Verify production cannot enable multimodal LLM before gate sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs["enable_multimodal_llm"] = True

    with pytest.raises(ValidationError, match="ENABLE_MULTIMODAL_LLM"):
        Settings(**kwargs)


def test_production_rejects_vision_classifier_without_signoff() -> None:
    """Verify production cannot enable YOLO ROI detection before gate sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs["enable_vision_classifier"] = True

    with pytest.raises(ValidationError, match="ENABLE_VISION_CLASSIFIER"):
        Settings(**kwargs)


@pytest.mark.parametrize(
    ("setting_name", "error_message"),
    (
        ("enable_image_learning_pipeline", "ENABLE_IMAGE_LEARNING_PIPELINE"),
        ("enable_pgvector_storage", "ENABLE_PGVECTOR_STORAGE"),
    ),
)
def test_production_rejects_learning_storage_flags_without_signoff(
    setting_name: str,
    error_message: str,
) -> None:
    """Verify production cannot enable learning storage gates before sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs[setting_name] = True

    with pytest.raises(ValidationError, match=error_message):
        Settings(**kwargs)


@pytest.mark.parametrize(
    ("setting_name", "error_message"),
    (
        ("feature_prescription_ocr_intake", "FEATURE_PRESCRIPTION_OCR_INTAKE"),
        ("feature_lab_result_ocr_intake", "FEATURE_LAB_RESULT_OCR_INTAKE"),
        ("feature_medication_safety_alert", "FEATURE_MEDICATION_SAFETY_ALERT"),
    ),
)
def test_production_rejects_regulated_feature_flags_without_signoff(
    setting_name: str,
    error_message: str,
) -> None:
    """Verify production cannot enable non-P1 regulated flags before sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs[setting_name] = True

    with pytest.raises(ValidationError, match=error_message):
        Settings(**kwargs)


def test_implementation_readiness_regulated_flags_default_off() -> None:
    """Verify the readiness manifest matches P1 default-off policy."""
    manifest = _load_json_object(READINESS_SETTINGS_PATH)
    environment_variables = _object_field(manifest, "environment_variables")
    feature_flags = _object_field(environment_variables, "feature_flags")

    for flag_name in (
        "FEATURE_PRESCRIPTION_OCR_INTAKE",
        "FEATURE_LAB_RESULT_OCR_INTAKE",
        "FEATURE_HOSPITAL_MOCK_FHIR",
        "FEATURE_MEDICATION_SAFETY_ALERT",
    ):
        flag_config = _object_field(feature_flags, flag_name)
        assert flag_config["default"] is False


def test_production_rejects_non_https_jwks_url() -> None:
    """Verify production JWKS URL must use HTTPS."""
    kwargs = _valid_production_kwargs()
    kwargs["jwt_jwks_url"] = "http://auth.example.com/.well-known/jwks.json"

    with pytest.raises(ValidationError, match="https"):
        Settings(**kwargs)


def test_production_requires_core_jwt_claims() -> None:
    """Verify production JWT validation cannot omit core access-token claims."""
    kwargs = _valid_production_kwargs()
    kwargs["jwt_required_claims"] = ["exp", "iss", "sub", "aud"]

    with pytest.raises(ValidationError, match="JWT_REQUIRED_CLAIMS"):
        Settings(**kwargs)


def test_production_requires_token_confusion_guard() -> None:
    """Verify production must configure a token type or provider token-use guard."""
    kwargs = _valid_production_kwargs()
    kwargs["jwt_expected_token_type"] = None
    kwargs["jwt_token_use_claim"] = None

    with pytest.raises(ValidationError, match="JWT_EXPECTED_TOKEN_TYPE"):
        Settings(**kwargs)


def test_valid_production_settings_load() -> None:
    """Verify explicit production security settings are accepted."""
    settings = Settings(**_valid_production_kwargs())

    assert settings.environment == "production"
    assert settings.auth_mode == "jwt"
    assert settings.jwt_audience == "lemon-api"

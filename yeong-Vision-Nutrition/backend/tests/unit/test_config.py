"""Application settings security tests."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.config import DEFAULT_DATABASE_URL, DEVELOPMENT_PRIVACY_HASH_SENTINEL, Settings


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
    assert "testserver" in settings.allowed_hosts
    assert settings.auth_mode == "disabled"
    assert settings.supplement_image_max_bytes == 5 * 1024 * 1024
    assert settings.supplement_image_max_pixels == 12_000_000
    assert settings.supplement_preview_ttl_minutes == 30


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
    kwargs["privacy_hash_secret"] = DEVELOPMENT_PRIVACY_HASH_SENTINEL

    with pytest.raises(ValidationError, match="PRIVACY_HASH_SECRET"):
        Settings(**kwargs)


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

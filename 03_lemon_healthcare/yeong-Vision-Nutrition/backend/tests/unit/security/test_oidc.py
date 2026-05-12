"""OIDC discovery helper tests."""

from __future__ import annotations

import pytest

from src.config import Settings
from src.security.oidc import (
    OIDCMetadataError,
    resolve_oidc_discovery_url,
    validate_oidc_metadata,
)


def _settings() -> Settings:
    """Return settings configured for OIDC metadata validation.

    Returns:
        Settings with issuer and JWKS URL.
    """
    return Settings(
        auth_mode="jwt",
        jwt_issuer="https://auth.example.com/",
        jwt_audience="lemon-api",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
    )


def test_resolve_oidc_discovery_url_from_issuer() -> None:
    """Verify default discovery URL uses the configured issuer boundary."""
    assert (
        resolve_oidc_discovery_url(_settings())
        == "https://auth.example.com/.well-known/openid-configuration"
    )


def test_validate_oidc_metadata_accepts_matching_issuer_and_jwks() -> None:
    """Verify discovery metadata must match configured issuer and JWKS URL."""
    metadata = validate_oidc_metadata(
        _settings(),
        {
            "issuer": "https://auth.example.com/",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        },
    )

    assert str(metadata.issuer) == "https://auth.example.com/"
    assert str(metadata.jwks_uri) == "https://auth.example.com/.well-known/jwks.json"


def test_validate_oidc_metadata_preserves_issuer_string_for_exact_match() -> None:
    """Verify issuer comparison does not add a trailing slash during validation."""
    settings = Settings(
        auth_mode="jwt",
        jwt_issuer="https://auth.example.com/oauth2/default",
        jwt_audience="lemon-api",
        jwt_jwks_url="https://auth.example.com/oauth2/default/v1/keys",
    )

    metadata = validate_oidc_metadata(
        settings,
        {
            "issuer": "https://auth.example.com/oauth2/default",
            "jwks_uri": "https://auth.example.com/oauth2/default/v1/keys",
        },
    )

    assert metadata.issuer == "https://auth.example.com/oauth2/default"


def test_validate_oidc_metadata_rejects_untrusted_jwks_uri() -> None:
    """Verify discovery metadata cannot redirect trust to an unexpected JWKS URL."""
    with pytest.raises(OIDCMetadataError, match="jwks_uri"):
        validate_oidc_metadata(
            _settings(),
            {
                "issuer": "https://auth.example.com/",
                "jwks_uri": "https://attacker.example.com/jwks.json",
            },
        )

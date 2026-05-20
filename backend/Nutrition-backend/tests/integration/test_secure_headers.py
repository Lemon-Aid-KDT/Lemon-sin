"""Integration tests for the secure headers middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app
from src.middleware.secure_headers import (
    BASELINE_SECURITY_HEADERS,
    PRODUCTION_HSTS_HEADER,
)


def test_secure_headers_apply_to_success_and_not_found_responses() -> None:
    """Verify baseline security headers are stamped on common responses."""
    client = TestClient(create_app(settings=Settings(_env_file=None)))

    for path in ("/health", "/nonexistent-route"):
        response = client.get(path)
        for header, expected in BASELINE_SECURITY_HEADERS.items():
            assert response.headers.get(header) == expected


def test_hsts_header_emitted_only_in_production() -> None:
    """Verify HSTS remains production-only."""
    header, value = PRODUCTION_HSTS_HEADER

    dev_client = TestClient(create_app(settings=Settings(_env_file=None)))
    assert dev_client.get("/health").headers.get(header) is None

    prod_settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+asyncpg://lemon_prod:secret@db.example.com:5432/lemon",
        allowed_origins=["https://lemonaid.example.com"],
        allowed_hosts=["api.lemonaid.example.com"],
        auth_mode="jwt",
        jwt_issuer="https://auth.example.com/",
        jwt_audience="lemon-api",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
        jwt_expected_token_type="at+jwt",
        privacy_hash_secret="prod-privacy-hash-secret-at-least-32",
        kdris_data_version="2025",
        kdris_data_path="data/nutrition_reference/kdris/kdris_2025.csv",
        allow_sample_kdris=False,
    )
    prod_client = TestClient(create_app(settings=prod_settings))

    assert prod_client.get("/health").headers.get(header) == value

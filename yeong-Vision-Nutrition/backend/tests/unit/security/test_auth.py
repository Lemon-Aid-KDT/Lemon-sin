"""OAuth/OIDC JWT authentication tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from fastapi import HTTPException, status

from src.config import Settings
from src.security import auth
from src.security.auth import JWTVerifier, require_analysis_write, require_current_user
from src.security.scopes import ALL_API_SCOPES


class _SigningKey:
    """Fake PyJWT signing key wrapper.

    Args:
        key: Public key returned by the fake JWKS client.
    """

    def __init__(self, key: object) -> None:
        self.key = key


class _JwksClient:
    """Fake JWKS client for deterministic unit tests.

    Args:
        key: Public key used to verify the token.
    """

    def __init__(self, key: object) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, _token: str) -> _SigningKey:
        """Return the configured signing key.

        Args:
            _token: JWT string. The fake does not inspect it.

        Returns:
            Signing key wrapper.
        """
        return _SigningKey(self._key)


def _jwt_settings() -> Settings:
    """Return JWT-enabled settings for auth tests.

    Returns:
        Settings configured like a production OAuth/OIDC resource server.
    """
    return Settings(
        auth_mode="jwt",
        jwt_issuer="https://auth.example.com/",
        jwt_audience="lemon-api",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
        jwt_algorithms=["RS256"],
        jwt_expected_token_type="JWT",
    )


def _key_pair() -> tuple[RSAPrivateKey, RSAPublicKey]:
    """Generate an RSA key pair for RS256 token tests.

    Returns:
        Private and public key objects.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _token(private_key: RSAPrivateKey, **claims: Any) -> str:
    """Build a signed RS256 JWT for tests.

    Args:
        private_key: RSA private key.
        **claims: Claim overrides.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": "user_123",
        "iss": "https://auth.example.com/",
        "aud": "lemon-api",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "scope": "analysis:write profile:read",
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test"})


@pytest.mark.asyncio
async def test_disabled_auth_returns_local_principal() -> None:
    """Verify local development can use protected dependencies without a token."""
    user = await require_current_user(None, Settings(auth_mode="disabled"))

    assert user.subject == "local-dev-user"
    assert "analysis:write" in user.scopes
    assert "supplement:write" in user.scopes
    assert set(user.scopes) == set(ALL_API_SCOPES)
    assert user.claims == {"auth_mode": "disabled"}


@pytest.mark.asyncio
async def test_jwt_auth_requires_bearer_credentials() -> None:
    """Verify JWT mode rejects missing credentials."""
    with pytest.raises(HTTPException) as error:
        await require_current_user(None, _jwt_settings())

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.value.headers == {"WWW-Authenticate": 'Bearer realm="lemon-healthcare"'}


def test_jwt_verifier_returns_validated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify JWT verifier validates issuer, audience, subject, and scopes."""
    private_key, public_key = _key_pair()
    monkeypatch.setattr(auth, "get_jwks_client", lambda *_args: _JwksClient(public_key))

    user = JWTVerifier(_jwt_settings()).verify(_token(private_key))

    assert user.subject == "user_123"
    assert user.issuer == "https://auth.example.com/"
    assert user.audience == "lemon-api"
    assert user.scopes == ("analysis:write", "profile:read")


def test_jwt_verifier_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify audience mismatch is rejected before protected storage APIs use the subject."""
    private_key, public_key = _key_pair()
    monkeypatch.setattr(auth, "get_jwks_client", lambda *_args: _JwksClient(public_key))

    with pytest.raises(HTTPException) as error:
        JWTVerifier(_jwt_settings()).verify(_token(private_key, aud="other-api"))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_jwt_verifier_requires_iat_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify issued-at is required to keep production token freshness checks explicit."""
    private_key, public_key = _key_pair()
    monkeypatch.setattr(auth, "get_jwks_client", lambda *_args: _JwksClient(public_key))
    token = _token(private_key, iat=None)

    with pytest.raises(HTTPException) as error:
        JWTVerifier(_jwt_settings()).verify(token)

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_jwt_verifier_rejects_wrong_token_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify configured typ mismatches are rejected before claims are trusted."""
    private_key, public_key = _key_pair()
    monkeypatch.setattr(auth, "get_jwks_client", lambda *_args: _JwksClient(public_key))
    settings = _jwt_settings()
    settings.jwt_expected_token_type = "at+jwt"

    with pytest.raises(HTTPException) as error:
        JWTVerifier(settings).verify(_token(private_key))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_jwt_verifier_rejects_disallowed_token_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify provider-specific id-token markers cannot pass as access tokens."""
    private_key, public_key = _key_pair()
    monkeypatch.setattr(auth, "get_jwks_client", lambda *_args: _JwksClient(public_key))
    settings = _jwt_settings()
    settings.jwt_token_use_claim = "token_use"
    settings.jwt_token_use_allowed_values = ["access"]

    with pytest.raises(HTTPException) as error:
        JWTVerifier(settings).verify(_token(private_key, token_use="id"))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_scope_dependency_rejects_missing_scope() -> None:
    """Verify route-level authorization returns RFC 6750 insufficient_scope."""
    user = auth.AuthenticatedUser(
        subject="user_123",
        issuer="https://auth.example.com/",
        scopes=("profile:read",),
    )

    with pytest.raises(HTTPException) as error:
        await require_analysis_write(user)

    assert error.value.status_code == status.HTTP_403_FORBIDDEN
    assert error.value.headers == {
        "WWW-Authenticate": (
            'Bearer realm="lemon-healthcare", ' 'error="insufficient_scope", scope="analysis:write"'
        )
    }

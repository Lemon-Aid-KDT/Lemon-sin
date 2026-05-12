"""애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+asyncpg://lemon:lemon@localhost:5432/lemon"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DEFAULT_JWT_ALGORITHMS = ["RS256"]
DEFAULT_JWT_REQUIRED_CLAIMS = ["exp", "iss", "sub", "aud", "iat"]
DEFAULT_JWT_SCOPE_CLAIMS = ["scope", "scp"]
DEVELOPMENT_PRIVACY_HASH_SENTINEL = "development-insecure-privacy-hash-sentinel"
JWT_CORE_REQUIRED_CLAIMS = {"aud", "exp", "iat", "iss", "sub"}
WILDCARD_VALUES = {"*"}
ASYMMETRIC_JWT_ALGORITHMS = {
    "EdDSA",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
    "RS256",
    "RS384",
    "RS512",
}


def _default_allowed_hosts() -> list[str]:
    """Return default hosts for local development and TestClient.

    Returns:
        Hostnames allowed by default outside production.
    """
    return DEFAULT_ALLOWED_HOSTS.copy()


def _default_jwt_algorithms() -> list[str]:
    """Return default public-key JWT algorithms.

    Returns:
        JWT algorithms accepted by default for OAuth/OIDC access tokens.
    """
    return DEFAULT_JWT_ALGORITHMS.copy()


def _default_jwt_required_claims() -> list[str]:
    """Return default JWT claims required for OAuth/OIDC access tokens.

    Returns:
        Required JWT claim names.
    """
    return DEFAULT_JWT_REQUIRED_CLAIMS.copy()


def _default_jwt_scope_claims() -> list[str]:
    """Return default JWT claims used to extract OAuth scopes.

    Returns:
        Scope claim names checked in order.
    """
    return DEFAULT_JWT_SCOPE_CLAIMS.copy()


def _contains_wildcard(values: list[str]) -> bool:
    """Check whether a security setting contains a wildcard value.

    Args:
        values: Setting values to inspect.

    Returns:
        True if a wildcard token is present.
    """
    return any(value.strip() in WILDCARD_VALUES for value in values)


def _failed_checks(checks: tuple[tuple[bool, str], ...]) -> list[str]:
    """Return messages for failed production security checks.

    Args:
        checks: Pairs of failure condition and error message.

    Returns:
        Error messages whose condition evaluated to True.
    """
    return [message for failed, message in checks if failed]


def _missing_required_field_errors(fields: tuple[tuple[str, str | None], ...]) -> list[str]:
    """Return production errors for missing required fields.

    Args:
        fields: Environment variable names and values to inspect.

    Returns:
        Error messages for empty values.
    """
    return [
        f"{name} is required when ENVIRONMENT=production." for name, value in fields if not value
    ]


def _is_non_https_url(value: str | None) -> bool:
    """Check whether a configured URL is present but not HTTPS.

    Args:
        value: URL string or None.

    Returns:
        True if the URL is set and does not start with https://.
    """
    return value is not None and not value.startswith("https://")


def _secret_value(value: SecretStr | None) -> str | None:
    """Return the raw secret value for production validation.

    Args:
        value: Secret setting value.

    Returns:
        Raw secret string or None.
    """
    if value is None:
        return None
    return value.get_secret_value()


class Settings(BaseSettings):
    """환경 변수 기반 애플리케이션 설정.

    Attributes:
        environment: 실행 환경.
        log_level: 애플리케이션 로그 레벨.
        database_url: PostgreSQL 연결 URL.
        redis_url: Redis 연결 URL.
        allowed_origins: CORS 허용 origin 목록.
        allowed_hosts: TrustedHost 허용 host 목록.
        auth_mode: 인증 모드. 실제 사용자 앱은 production에서 jwt를 사용한다.
        jwt_issuer: OAuth/OIDC issuer URL.
        jwt_audience: JWT audience.
        jwt_jwks_url: OAuth/OIDC JWKS URL.
        jwt_algorithms: JWT signature algorithms allowed for JWKS verification.
        jwt_leeway_seconds: Clock-skew leeway for exp, nbf, and iat checks.
        jwt_required_claims: JWT claims that must be present.
        jwt_scope_claims: JWT claim names used for OAuth scopes.
        jwt_expected_token_type: Optional JOSE typ value expected for access tokens.
        jwt_token_use_claim: Optional provider-specific claim used to distinguish access tokens.
        jwt_token_use_allowed_values: Allowed provider-specific access-token values.
        jwt_jwks_cache_ttl_seconds: JWKS cache lifespan.
        jwt_jwks_timeout_seconds: JWKS retrieval timeout.
        oidc_discovery_url: Optional OIDC discovery document URL for operational preflight.
        privacy_hash_secret: HMAC secret used for privacy-preserving audit identifiers.
        llm_provider: 기본 LLM provider. 민감정보 보호를 위해 Ollama만 허용한다.
        ollama_base_url: Ollama Local API 기본 주소.
        ollama_model: 텍스트 구조화 출력 기본 모델.
        ollama_vision_model: 이미지 입력 실험용 모델.
        ollama_timeout_sec: Ollama 요청 타임아웃.
        ollama_temperature: 구조화 출력 안정성을 위한 temperature.
        allow_external_llm: 외부 LLM 사용 허용 여부.
        google_application_credentials: Google Cloud 인증 파일 경로.
        clova_ocr_api_url: CLOVA OCR API Gateway invoke URL.
        clova_ocr_secret: CLOVA OCR client secret.
        mfds_api_key: 식약처/공공데이터 API 키.
        supplement_image_max_bytes: Maximum uploaded supplement label image size.
        supplement_image_max_pixels: Maximum decoded supplement label image pixels.
        supplement_preview_ttl_minutes: Minutes before an intake-only preview expires.
        supplement_ocr_text_max_chars: Maximum OCR text characters sent to the parser.
        supplement_parser_algorithm_version: Version label for structured supplement parsing.
        supplement_parser_max_ingredients: Maximum ingredient candidates accepted from the parser.
        kdris_data_version: KDRIs dataset version used by runtime lookup.
        kdris_data_path: Optional explicit KDRIs CSV path.
        kdris_manifest_path: Optional explicit KDRIs source manifest path.
        allow_sample_kdris: Whether the 2020 sample KDRIs fixture may be used.
        feature_prescription_ocr_intake: 처방전 OCR intake 기능 플래그.
        feature_lab_result_ocr_intake: 검사표 OCR intake 기능 플래그.
        feature_dosage_change_recommendation: 복용량 변경 추천 기능 플래그.
        feature_medication_safety_alert: 복약 안전 알림 기능 플래그.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = Field(default="INFO")

    database_url: str = Field(default=DEFAULT_DATABASE_URL)
    redis_url: str = Field(default=DEFAULT_REDIS_URL)
    allowed_origins: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=_default_allowed_hosts)

    auth_mode: Literal["disabled", "jwt"] = "disabled"
    jwt_issuer: str | None = Field(default=None)
    jwt_audience: str | None = Field(default=None)
    jwt_jwks_url: str | None = Field(default=None)
    jwt_algorithms: list[str] = Field(default_factory=_default_jwt_algorithms)
    jwt_leeway_seconds: int = Field(default=60, ge=0, le=300)
    jwt_required_claims: list[str] = Field(default_factory=_default_jwt_required_claims)
    jwt_scope_claims: list[str] = Field(default_factory=_default_jwt_scope_claims)
    jwt_expected_token_type: str | None = Field(default=None)
    jwt_token_use_claim: str | None = Field(default=None)
    jwt_token_use_allowed_values: list[str] = Field(default_factory=list)
    jwt_jwks_cache_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    jwt_jwks_timeout_seconds: int = Field(default=5, ge=1, le=30)
    oidc_discovery_url: str | None = Field(default=None)
    privacy_hash_secret: SecretStr = Field(default=SecretStr(DEVELOPMENT_PRIVACY_HASH_SENTINEL))

    llm_provider: Literal["ollama"] = "ollama"
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen3.5:9b")
    ollama_vision_model: str | None = Field(default="gemma4:e4b")
    ollama_timeout_sec: int = Field(default=60, ge=1)
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    allow_external_llm: bool = Field(default=False)

    google_application_credentials: str | None = Field(default=None)
    clova_ocr_api_url: str | None = Field(default=None)
    clova_ocr_secret: SecretStr | None = Field(default=None)
    mfds_api_key: SecretStr | None = Field(default=None)

    supplement_image_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=10 * 1024 * 1024)
    supplement_image_max_pixels: int = Field(default=12_000_000, ge=1, le=25_000_000)
    supplement_preview_ttl_minutes: int = Field(default=30, ge=1, le=1440)
    supplement_ocr_text_max_chars: int = Field(default=12_000, ge=100, le=50_000)
    supplement_parser_algorithm_version: str = Field(
        default="supplement-ollama-parser-v1.0.0",
        min_length=1,
        max_length=64,
    )
    supplement_parser_max_ingredients: int = Field(default=80, ge=1, le=80)

    kdris_data_version: Literal["2020-sample", "2025"] = "2020-sample"
    kdris_data_path: str | None = Field(default=None)
    kdris_manifest_path: str | None = Field(default=None)
    allow_sample_kdris: bool = Field(default=True)

    feature_prescription_ocr_intake: bool = Field(default=True)
    feature_lab_result_ocr_intake: bool = Field(default=True)
    feature_dosage_change_recommendation: bool = Field(default=False)
    feature_medication_safety_alert: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        """Validate production-only security requirements.

        Returns:
            Validated settings instance.

        Raises:
            ValueError: If production settings contain unsafe defaults or missing
                OAuth/JWT configuration.
        """
        if self.environment != "production":
            return self

        privacy_hash_secret = _secret_value(self.privacy_hash_secret)
        errors = _failed_checks(
            (
                (
                    self.database_url == DEFAULT_DATABASE_URL,
                    "DATABASE_URL must not use the development default in production.",
                ),
                (
                    self.log_level.upper() == "DEBUG",
                    "LOG_LEVEL=DEBUG is not allowed in production.",
                ),
                (
                    self.allow_external_llm,
                    "ALLOW_EXTERNAL_LLM=true is not allowed in production.",
                ),
                (not self.allowed_origins, "ALLOWED_ORIGINS must be explicit in production."),
                (not self.allowed_hosts, "ALLOWED_HOSTS must be explicit in production."),
                (
                    _contains_wildcard(self.allowed_origins),
                    "ALLOWED_ORIGINS must not contain wildcards in production.",
                ),
                (
                    _contains_wildcard(self.allowed_hosts),
                    "ALLOWED_HOSTS must not contain wildcards in production.",
                ),
                (self.auth_mode != "jwt", "AUTH_MODE=jwt is required for production user apps."),
                (
                    _is_non_https_url(self.jwt_jwks_url),
                    "JWT_JWKS_URL must use https in production.",
                ),
                (
                    _is_non_https_url(self.oidc_discovery_url),
                    "OIDC_DISCOVERY_URL must use https in production.",
                ),
                (not self.jwt_algorithms, "JWT_ALGORITHMS must be explicit in production."),
                (
                    not set(self.jwt_algorithms).issubset(ASYMMETRIC_JWT_ALGORITHMS),
                    "JWT_ALGORITHMS must use supported asymmetric signing algorithms.",
                ),
                (
                    not JWT_CORE_REQUIRED_CLAIMS.issubset(set(self.jwt_required_claims)),
                    "JWT_REQUIRED_CLAIMS must include aud, exp, iat, iss, and sub in production.",
                ),
                (
                    not self.jwt_scope_claims,
                    "JWT_SCOPE_CLAIMS must be explicit in production.",
                ),
                (
                    not self.jwt_expected_token_type
                    and (not self.jwt_token_use_claim or not self.jwt_token_use_allowed_values),
                    "JWT_EXPECTED_TOKEN_TYPE or JWT_TOKEN_USE_CLAIM with allowed values is required in production.",
                ),
                (
                    not privacy_hash_secret
                    or privacy_hash_secret == DEVELOPMENT_PRIVACY_HASH_SENTINEL,
                    "PRIVACY_HASH_SECRET must be set to a non-default value in production.",
                ),
                (
                    self.allow_sample_kdris,
                    "ALLOW_SAMPLE_KDRIS=false is required in production.",
                ),
                (
                    self.kdris_data_version != "2025",
                    "KDRIS_DATA_VERSION=2025 is required in production.",
                ),
                (
                    not self.kdris_data_path,
                    "KDRIS_DATA_PATH is required in production.",
                ),
            )
        )
        errors.extend(
            _missing_required_field_errors(
                (
                    ("JWT_ISSUER", self.jwt_issuer),
                    ("JWT_AUDIENCE", self.jwt_audience),
                    ("JWT_JWKS_URL", self.jwt_jwks_url),
                )
            )
        )

        if errors:
            raise ValueError(" ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """애플리케이션 설정 싱글턴을 반환한다.

    Returns:
        환경 변수와 기본값에서 로드한 설정 객체.
    """
    return Settings()

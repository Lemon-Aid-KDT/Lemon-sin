"""애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_DATABASE_URL = "postgresql+asyncpg://lemon:lemon@localhost:5432/lemon"
POSTGRESQL_ASYNCPG_DRIVER = "postgresql+asyncpg"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DEFAULT_JWT_ALGORITHMS = ["RS256"]
DEFAULT_JWT_REQUIRED_CLAIMS = ["exp", "iss", "sub", "aud", "iat"]
DEFAULT_JWT_SCOPE_CLAIMS = ["scope", "scp"]
DEFAULT_VISION_ROI_ALLOWED_CLASSES = ["supplement_label", "supplement_bottle", "blister_pack"]
# Deliberately insecure development sentinel; production validation rejects this exact value.
DEFAULT_PRIVACY_HASH_SECRET = "development-insecure-privacy-hash-secret"  # noqa: S105, RUF100
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE_CANDIDATES = (PROJECT_ROOT / ".env", BACKEND_ROOT / ".env")
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


def _default_vision_roi_allowed_classes() -> list[str]:
    """Return default YOLO ROI labels allowed for supplement image preprocessing.

    Returns:
        Allowed object-detection labels for supplement ROI assistance.
    """
    return DEFAULT_VISION_ROI_ALLOWED_CLASSES.copy()


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


def _is_local_http_url(value: str) -> bool:
    """Return whether a URL points at a loopback HTTP endpoint."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


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


def _database_drivername(database_url: str) -> str:
    """Return the SQLAlchemy driver name for a configured database URL.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        SQLAlchemy driver name such as ``postgresql+asyncpg``.

    Raises:
        ValueError: If the URL cannot be parsed by SQLAlchemy.
    """
    try:
        return make_url(database_url).drivername
    except ArgumentError as exc:
        raise ValueError("DATABASE_URL must be a valid SQLAlchemy database URL.") from exc


class Settings(BaseSettings):
    """환경 변수 기반 애플리케이션 설정.

    Attributes:
        environment: 실행 환경.
        log_level: 애플리케이션 로그 레벨.
        database_url: PostgreSQL asyncpg SQLAlchemy 연결 URL.
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
        llm_provider: 기본 LLM provider. Ollama 또는 로컬/자가호스팅 SGLang을 허용한다.
        ollama_base_url: Ollama Local API 기본 주소.
        ollama_model: 텍스트 구조화 출력 기본 모델.
        ollama_vision_model: 이미지 입력 실험용 모델.
        ollama_timeout_sec: Ollama 요청 타임아웃.
        ollama_temperature: 구조화 출력 안정성을 위한 temperature.
        allow_external_llm: 외부 LLM 사용 허용 여부.
        ocr_primary_provider: Primary supplement-label OCR provider selector.
        allow_external_ocr: Whether external OCR providers can receive image bytes.
        google_vision_auth_mode: Google Vision authentication mode.
        google_cloud_api_key: Google Cloud Vision REST API key.
        google_cloud_project: Google Cloud project used for quota and regional OCR.
        google_vision_location: Google Vision OCR processing location.
        google_vision_feature: Google Vision OCR feature type.
        google_vision_language_hints: Optional BCP-47 language hints passed to OCR.
        google_vision_timeout_seconds: Google Vision request timeout.
        google_vision_max_retries: Google Vision retry count for transient failures.
        google_application_credentials: Deprecated Google Cloud 인증 파일 경로.
        clova_ocr_api_url: CLOVA OCR API Gateway invoke URL.
        clova_ocr_secret: CLOVA OCR client secret.
        mfds_api_key: 식약처/공공데이터 API 키.
        supplement_image_max_bytes: Maximum uploaded supplement label image size.
        supplement_image_max_pixels: Maximum decoded supplement label image pixels.
        supplement_preview_ttl_minutes: Minutes before an intake-only preview expires.
        supplement_ocr_text_max_chars: Maximum OCR text characters sent to the parser.
        supplement_parser_algorithm_version: Version label for structured supplement parsing.
        supplement_parser_max_ingredients: Maximum ingredient candidates accepted from the parser.
        regulated_document_preview_ttl_minutes: Minutes before a regulated OCR preview expires.
        sensitive_document_original_image_retention_seconds: Seconds raw regulated document images
            may be retained before deletion. The default 0 means request-memory only.
        ocr_roi_preprocessing_policy: Whether detected ROI metadata should crop primary OCR input.
        multimodal_ocr_assist_policy: Policy controlling when local vision LLM fallback may run.
        enable_multimodal_verification: Whether local vision verification can sample OCR outputs.
        multimodal_verification_sample_rate: Fraction of accepted OCR outputs to verify.
        multimodal_verification_threshold: Minimum normalized text similarity for verification.
        enable_local_ocr: Whether local OCR fallback adapters may run.
        local_ocr_provider: Local OCR provider selector.
        local_ocr_language: Language setting passed to local OCR providers.
        local_ocr_device: Optional local OCR runtime device selector.
        local_ocr_confidence_threshold: Minimum confidence for local OCR fallback candidates.
        enable_clova_ocr: Whether NAVER Cloud CLOVA OCR fallback may run.
        vision_roi_min_confidence: Minimum detection confidence accepted for a YOLO ROI.
        vision_roi_allowed_classes: Allowed non-text object labels accepted from YOLO.
        feature_hall_lite_weight_prediction: Whether Hall-lite weight prediction can run.
        weight_prediction_engine: Internal weight prediction engine selector.
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
        env_file=ENV_FILE_CANDIDATES,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
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
    privacy_hash_secret: SecretStr = Field(default=SecretStr(DEFAULT_PRIVACY_HASH_SECRET))

    llm_provider: Literal["ollama", "sglang"] = "ollama"
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen3.5:9b")
    ollama_vision_model: str | None = Field(default="gemma4:e4b")
    ollama_timeout_sec: int = Field(default=60, ge=1)
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    sglang_base_url: str = Field(default="http://127.0.0.1:30000/v1")
    sglang_model: str = Field(default="qwen3.5:9b")
    sglang_api_key: SecretStr | None = Field(default=None)
    allow_external_llm: bool = Field(default=False)

    ocr_primary_provider: Literal["none", "google_vision"] = Field(default="none")
    allow_external_ocr: bool = Field(default=False)
    google_vision_auth_mode: Literal["api_key", "adc"] = Field(default="api_key")
    google_cloud_api_key: SecretStr | None = Field(default=None)
    google_cloud_project: str | None = Field(default=None)
    google_vision_location: Literal["global", "us", "eu"] = Field(default="global")
    google_vision_feature: Literal["document_text_detection"] = Field(
        default="document_text_detection"
    )
    google_vision_language_hints: list[str] = Field(default_factory=list, max_length=8)
    google_vision_timeout_seconds: int = Field(default=15, ge=1, le=60)
    google_vision_max_retries: int = Field(default=2, ge=0, le=5)
    google_application_credentials: str | None = Field(default=None)
    clova_ocr_api_url: str | None = Field(default=None)
    clova_ocr_secret: SecretStr | None = Field(default=None)
    data_go_kr_service_key: SecretStr | None = Field(default=None)
    mfds_api_key: SecretStr | None = Field(default=None)
    mfds_data_api_key: SecretStr | None = Field(default=None)
    kdca_healthinfo_url_template: str | None = Field(default=None)
    kdca_healthinfo_topic_ids_file: Path | None = Field(default=None)
    kdca_healthinfo_topic_ids: dict[str, str] = Field(default_factory=dict)
    kdca_healthinfo_api_key: SecretStr | None = Field(default=None)
    ncbi_api_key: SecretStr | None = Field(default=None)
    ncbi_tool_name: str = Field(default="lemon-aid")
    ncbi_email: str | None = Field(default=None)
    semantic_scholar_api_key: SecretStr | None = Field(default=None)
    openfda_api_key: SecretStr | None = Field(default=None)
    crossref_mailto: str | None = Field(default=None)
    google_cse_api_key: SecretStr | None = Field(default=None)
    google_cse_id: str | None = Field(default=None)

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
    regulated_document_preview_ttl_minutes: int = Field(default=30, ge=1, le=1440)
    sensitive_document_original_image_retention_seconds: int = Field(default=0, ge=0, le=3600)

    feature_hall_lite_weight_prediction: bool = Field(
        default=False,
        description="Hall-lite 동적 체중 예측 활성화. 기본값은 기존 7-step fallback.",
    )
    weight_prediction_engine: Literal["static_7step", "hall_lite", "auto"] = Field(
        default="static_7step",
        description="체중 예측 엔진 선택. 기본값은 기존 static 7-step.",
    )

    kdris_data_version: Literal["2020-sample", "2025"] = "2020-sample"
    kdris_data_path: str | None = Field(default=None)
    kdris_manifest_path: str | None = Field(default=None)
    allow_sample_kdris: bool = Field(default=True)

    feature_prescription_ocr_intake: bool = Field(default=False)
    feature_lab_result_ocr_intake: bool = Field(default=False)
    feature_dosage_change_recommendation: bool = Field(default=False)
    feature_medication_safety_alert: bool = Field(default=False)

    # Phase 게이트 플래그 — docs/17 §9 매핑. 모든 기본값 False/0.
    # 운영 활성화 전에는 발주처 리뷰 게이트(#1/#2/#3) 통과 후에만 변경.
    enable_multimodal_llm: bool = Field(
        default=False,
        description="Ollama 멀티모달(예: Gemma 4) 보조 채널 활성화. docs/17 §9 게이트 #1 필요.",
    )
    enable_vision_classifier: bool = Field(
        default=False,
        description="라벨 영역 검출용 YOLO 어댑터 활성화. docs/17 §9 게이트 #2 필요.",
    )
    vision_classifier_model: str = Field(default="yolov8n.pt")
    ocr_roi_preprocessing_policy: Literal[
        "disabled",
        "detect_only",
        "crop_before_primary",
    ] = Field(
        default="disabled",
        description="YOLO ROI를 primary OCR 입력에 적용하는 정책. 기본값 disabled.",
    )
    multimodal_ocr_assist_policy: Literal[
        "disabled",
        "ocr_empty_only",
        "low_confidence",
    ] = Field(
        default="disabled",
        description="Ollama vision assist 호출 조건. 기본값 disabled.",
    )
    enable_multimodal_verification: bool = Field(
        default=False,
        description="Primary OCR 결과를 local vision model로 샘플 검증. 기본값 disabled.",
    )
    multimodal_verification_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    multimodal_verification_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    enable_local_ocr: bool = Field(
        default=False,
        description="PaddleOCR 등 local OCR fallback 활성화. 기본값 disabled.",
    )
    local_ocr_provider: Literal["paddleocr"] = Field(default="paddleocr")
    local_ocr_language: str = Field(default="korean")
    local_ocr_device: str | None = Field(default=None)
    local_ocr_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    enable_clova_ocr: bool = Field(
        default=False,
        description="NAVER Cloud CLOVA OCR external fallback 활성화. 기본값 disabled.",
    )
    vision_roi_min_confidence: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="YOLO ROI 후보로 인정할 최소 confidence.",
    )
    vision_roi_allowed_classes: list[str] = Field(
        default_factory=_default_vision_roi_allowed_classes,
        min_length=1,
        max_length=10,
        description="YOLO ROI 보조에서 허용하는 object-detection class labels.",
    )
    enable_image_learning_pipeline: bool = Field(
        default=False,
        description="가명화 영양제 이미지의 학습 데이터셋 적재 활성화. docs/17 §9 게이트 #3 필요.",
    )
    enable_pgvector_storage: bool = Field(
        default=False,
        description="pgvector 기반 임베딩 저장소 활성화. docs/17 §9 게이트 #3 필요.",
    )
    embedding_model: str = Field(default="clip-ViT-B-32")
    embedding_dimensions: int | None = Field(
        default=None,
        ge=1,
        le=16000,
        description="검증된 embedding 차원. None이면 runner 결과를 그대로 기록한다.",
    )
    image_retention_days: int = Field(
        default=0,
        ge=0,
        le=730,
        description="영양제 이미지 보유 일수. 0 = 분석 직후 즉시 삭제(docs/17 §5).",
    )
    learning_object_storage_provider: Literal["disabled", "local", "s3"] = Field(
        default="disabled",
        description="학습 이미지 object storage provider. 기본값 disabled.",
    )
    learning_object_storage_bucket: str | None = Field(default=None)
    learning_object_storage_prefix: str = Field(default="learning/images")
    learning_object_storage_endpoint_url: str | None = Field(default=None)
    learning_object_storage_region: str | None = Field(default=None)
    learning_object_storage_sse: str | None = Field(default="AES256")
    learning_object_storage_local_path: Path = Field(
        default=PROJECT_ROOT / ".local" / "learning-images",
        description="개발/테스트 전용 local object storage 경로.",
    )

    @model_validator(mode="after")
    def validate_runtime_security(self) -> Self:
        """Validate database and production-only security requirements.

        Returns:
            Validated settings instance.

        Raises:
            ValueError: If settings contain an unsupported database URL, or if
                production settings contain unsafe defaults or missing OAuth/JWT
                configuration.
        """
        if _database_drivername(self.database_url) != POSTGRESQL_ASYNCPG_DRIVER:
            raise ValueError(
                f"DATABASE_URL must use {POSTGRESQL_ASYNCPG_DRIVER}; "
                "SQLite and sync PostgreSQL drivers are not supported."
            )
        if (
            self.learning_object_storage_provider == "s3"
            and not self.learning_object_storage_bucket
        ):
            raise ValueError(
                "LEARNING_OBJECT_STORAGE_BUCKET is required when "
                "LEARNING_OBJECT_STORAGE_PROVIDER=s3."
            )
        if (
            self.llm_provider == "sglang"
            and not self.allow_external_llm
            and not _is_local_http_url(self.sglang_base_url)
        ):
            raise ValueError(
                "SGLANG_BASE_URL must be a local loopback endpoint when "
                "ALLOW_EXTERNAL_LLM=false."
            )

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
                (
                    self.ocr_primary_provider == "google_vision" and not self.allow_external_ocr,
                    "ALLOW_EXTERNAL_OCR=true is required when OCR_PRIMARY_PROVIDER=google_vision in production.",
                ),
                (
                    self.ocr_primary_provider == "google_vision"
                    and self.google_vision_auth_mode != "adc",
                    "GOOGLE_VISION_AUTH_MODE=adc is required when OCR_PRIMARY_PROVIDER=google_vision in production.",
                ),
                (
                    self.ocr_primary_provider == "google_vision" and not self.google_cloud_project,
                    "GOOGLE_CLOUD_PROJECT is required when OCR_PRIMARY_PROVIDER=google_vision in production.",
                ),
                (
                    self.ocr_primary_provider == "google_vision"
                    and bool(self.google_application_credentials),
                    "GOOGLE_APPLICATION_CREDENTIALS file-based credentials are not allowed for Google Vision in production.",
                ),
                (
                    self.ocr_roi_preprocessing_policy != "disabled"
                    and not self.enable_vision_classifier,
                    "OCR_ROI_PREPROCESSING_POLICY requires ENABLE_VISION_CLASSIFIER=true.",
                ),
                (
                    self.enable_multimodal_verification and not self.enable_multimodal_llm,
                    "ENABLE_MULTIMODAL_VERIFICATION=true requires ENABLE_MULTIMODAL_LLM=true.",
                ),
                (
                    self.enable_multimodal_verification
                    and self.multimodal_verification_sample_rate <= 0,
                    "MULTIMODAL_VERIFICATION_SAMPLE_RATE must be greater than 0 when verification is enabled.",
                ),
                (
                    self.enable_clova_ocr and not self.allow_external_ocr,
                    "ALLOW_EXTERNAL_OCR=true is required when ENABLE_CLOVA_OCR=true in production.",
                ),
                (
                    self.enable_clova_ocr and not self.clova_ocr_api_url,
                    "CLOVA_OCR_API_URL is required when ENABLE_CLOVA_OCR=true in production.",
                ),
                (
                    self.enable_clova_ocr and self.clova_ocr_secret is None,
                    "CLOVA_OCR_SECRET is required when ENABLE_CLOVA_OCR=true in production.",
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
                    not privacy_hash_secret or privacy_hash_secret == DEFAULT_PRIVACY_HASH_SECRET,
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
                (
                    self.enable_multimodal_llm,
                    "ENABLE_MULTIMODAL_LLM=true requires docs/17 §9 gate #1 sign-off.",
                ),
                (
                    self.enable_multimodal_verification,
                    "ENABLE_MULTIMODAL_VERIFICATION=true requires docs/17 §9 gate #1 sign-off.",
                ),
                (
                    self.enable_vision_classifier,
                    "ENABLE_VISION_CLASSIFIER=true requires docs/17 §9 gate #2 sign-off.",
                ),
                (
                    self.ocr_roi_preprocessing_policy != "disabled",
                    "OCR_ROI_PREPROCESSING_POLICY requires docs/17 §9 gate #2 sign-off.",
                ),
                (
                    self.enable_local_ocr,
                    "ENABLE_LOCAL_OCR=true requires local OCR fallback validation sign-off.",
                ),
                (
                    self.enable_clova_ocr,
                    "ENABLE_CLOVA_OCR=true requires external OCR fallback vendor sign-off.",
                ),
                (
                    self.enable_image_learning_pipeline,
                    "ENABLE_IMAGE_LEARNING_PIPELINE=true requires docs/17 §9 gate #3 sign-off.",
                ),
                (
                    self.enable_pgvector_storage,
                    "ENABLE_PGVECTOR_STORAGE=true requires docs/17 §9 gate #3 sign-off.",
                ),
                (
                    self.learning_object_storage_provider != "disabled",
                    "LEARNING_OBJECT_STORAGE_PROVIDER requires docs/17 §9 gate #3 sign-off.",
                ),
                (
                    self.feature_hall_lite_weight_prediction,
                    "FEATURE_HALL_LITE_WEIGHT_PREDICTION=true requires Hall-lite validation sign-off.",
                ),
                (
                    self.feature_prescription_ocr_intake,
                    "FEATURE_PRESCRIPTION_OCR_INTAKE=true requires regulated OCR intake sign-off.",
                ),
                (
                    self.feature_lab_result_ocr_intake,
                    "FEATURE_LAB_RESULT_OCR_INTAKE=true requires regulated OCR intake sign-off.",
                ),
                (
                    self.sensitive_document_original_image_retention_seconds > 0,
                    "SENSITIVE_DOCUMENT_ORIGINAL_IMAGE_RETENTION_SECONDS>0 requires regulated OCR retention sign-off.",
                ),
                (
                    self.feature_medication_safety_alert,
                    "FEATURE_MEDICATION_SAFETY_ALERT=true requires medication safety workflow sign-off.",
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

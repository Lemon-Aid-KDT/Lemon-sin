"""Application settings security tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import SecretStr, ValidationError
from src.config import DEFAULT_DATABASE_URL, DEFAULT_PRIVACY_HASH_SECRET, Settings

PROJECT_ROOT = Path(__file__).resolve().parents[4]
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
        "_env_file": None,
        "environment": "production",
        "database_url": "postgresql+asyncpg://lemon_prod:secret@db.example.com:5432/lemon",
        "allowed_origins": ["https://app.example.com"],
        "allowed_hosts": ["api.example.com"],
        "rate_limit_enabled": True,
        "auth_mode": "jwt",
        "jwt_issuer": "https://auth.example.com/",
        "jwt_audience": "lemon-api",
        "jwt_jwks_url": "https://auth.example.com/.well-known/jwks.json",
        "jwt_expected_token_type": "at+jwt",
        "privacy_hash_secret": "prod-privacy-hash-secret-at-least-32",
        "kdris_data_version": "2025",
        "kdris_data_path": "data/nutrition_reference/kdris/kdris_2025.csv",
        "allow_sample_kdris": False,
    }


def _valid_public_staging_kwargs() -> dict[str, Any]:
    """Return a valid public staging settings baseline.

    Returns:
        Keyword arguments accepted by Settings.
    """
    kwargs = _valid_production_kwargs()
    kwargs.update(
        {
            "environment": "staging",
            "deployment_exposure": "public",
            "database_url": "postgresql+asyncpg://lemon_stage:secret@db.example.com:5432/lemon",
            "allowed_origins": ["https://staging-app.example.com"],
            "allowed_hosts": ["staging-api.example.com"],
        }
    )
    return kwargs


def test_default_development_settings_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify development defaults remain usable for local work."""
    monkeypatch.delenv("GOOGLE_CLOUD_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "testserver" in settings.allowed_hosts
    assert settings.auth_mode == "disabled"
    assert settings.supplement_image_max_bytes == 5 * 1024 * 1024
    assert settings.supplement_image_max_pixels == 12_000_000
    assert settings.supplement_preview_ttl_minutes == 30
    assert settings.regulated_document_preview_ttl_minutes == 30
    assert settings.sensitive_document_original_image_retention_seconds == 0
    assert not settings.feature_hall_lite_weight_prediction
    assert settings.weight_prediction_engine == "static_7step"
    assert settings.feature_prescription_ocr_intake is False
    assert settings.feature_lab_result_ocr_intake is False
    assert settings.feature_dosage_change_recommendation is False
    assert settings.feature_medication_safety_alert is False
    assert settings.ocr_primary_provider == "paddleocr"
    assert settings.allow_external_ocr is False
    assert settings.google_vision_auth_mode == "api_key"
    assert settings.google_cloud_api_key is None
    assert settings.google_cloud_project is None
    assert settings.google_vision_location == "global"
    assert settings.google_vision_feature == "document_text_detection"
    assert settings.google_vision_language_hints == []
    assert settings.google_vision_timeout_seconds == 15
    assert (
        settings.google_vision_max_retries,
        settings.ocr_confidence_threshold,
        settings.clova_ocr_timeout_seconds,
        settings.clova_ocr_max_retries,
    ) == (2, 0.85, 15, 1)
    assert settings.enable_multimodal_llm is False
    assert settings.multimodal_ocr_assist_policy == "disabled"
    assert settings.enable_multimodal_verification is False
    assert settings.multimodal_verification_sample_rate == 0.0
    assert settings.multimodal_verification_threshold == 0.80
    assert settings.enable_vision_classifier is False
    assert settings.ocr_roi_preprocessing_policy == "disabled"
    assert settings.enable_local_ocr is True
    assert (
        settings.local_ocr_provider,
        settings.local_ocr_language,
        settings.local_ocr_device,
        settings.local_ocr_engine,
        settings.local_ocr_use_doc_orientation_classify,
        settings.local_ocr_use_doc_unwarping,
        settings.local_ocr_use_textline_orientation,
        settings.local_ocr_paddlex_config,
        settings.local_ocr_text_recognition_model_dir,
        settings.local_ocr_text_detection_model_dir,
        settings.local_ocr_text_recognition_model_name,
        settings.local_ocr_text_detection_model_name,
        settings.local_ocr_confidence_threshold,
    ) == (
        "paddleocr",
        "korean",
        None,
        "paddle",
        True,
        False,
        False,
        None,
        None,
        None,
        None,
        None,
        0.75,
    )
    assert settings.enable_clova_ocr is False
    assert settings.enable_parser_domain_correction is False
    assert settings.parser_domain_correction_mode == "report_only"
    assert settings.parser_domain_correction_artifact_path.name == (
        "parser_domain_corrections.v1.json"
    )
    assert settings.vision_roi_min_confidence == 0.50
    assert settings.vision_roi_allowed_classes == [
        "supplement_label",
        "supplement_bottle",
        "blister_pack",
    ]
    assert settings.enable_image_learning_pipeline is False
    assert settings.enable_pgvector_storage is False
    assert settings.embedding_model == "clip-ViT-B-32"
    assert settings.embedding_dimensions is None
    assert settings.image_retention_days == 0
    assert settings.learning_object_storage_provider == "disabled"


def test_release_gate_defaults_are_local_and_fail_closed() -> None:
    """Verify release-gate settings default to local-only disabled posture."""
    settings = Settings(_env_file=None)

    assert settings.deployment_exposure == "local"
    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_default_per_minute == 60
    assert settings.rate_limit_image_upload_per_minute == 5
    assert settings.rate_limit_llm_explain_per_minute == 10


def test_governance_gate_defaults_to_report_only() -> None:
    """Verify release governance is report-only until CI sign-off enables blocking."""
    settings = Settings(_env_file=None)

    assert settings.governance_gate_mode == "report_only"


def test_google_cloud_api_key_can_be_loaded_as_secret() -> None:
    """Verify local Google Vision REST API key input is accepted as a secret value."""
    settings = Settings(
        _env_file=None,
        google_cloud_api_key=SecretStr("test-google-cloud-api-key"),
    )

    assert settings.google_cloud_api_key is not None
    assert settings.google_cloud_api_key.get_secret_value() == "test-google-cloud-api-key"


def test_official_barcode_lookup_defaults_are_fail_closed() -> None:
    """Verify official barcode lookup keys are disabled and empty by default."""
    settings = Settings(_env_file=None)

    assert settings.mfds_api_key is None
    assert settings.enable_barcode_lookup is False
    assert settings.foodqr_service_key is None
    assert settings.foodqr_base_url == "https://apis.data.go.kr/1471000/FoodQrInfoService01"
    assert settings.foodqr_product_list_path == "/getFoodQrProdList01"
    assert settings.foodqr_product_manufacturing_path is None
    assert settings.foodqr_timeout_seconds == 10
    assert settings.foodqr_max_retries == 2
    assert settings.foodqr_num_of_rows == 10
    assert settings.mfds_openapi_base_url == "http://openapi.foodsafetykorea.go.kr/api"
    assert settings.mfds_openapi_timeout_seconds == 10
    assert settings.mfds_openapi_max_retries == 2
    assert settings.mfds_openapi_page_size == 100


def test_google_cloud_api_key_can_be_loaded_from_dotenv(tmp_path: Path) -> None:
    """Verify Google Vision API key placeholders can be filled through dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_CLOUD_API_KEY=test-dotenv-google-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.google_cloud_api_key is not None
    assert settings.google_cloud_api_key.get_secret_value() == "test-dotenv-google-key"


def test_empty_google_cloud_api_key_dotenv_value_is_ignored(tmp_path: Path) -> None:
    """Verify an empty local dotenv placeholder does not become an active secret."""
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_CLOUD_API_KEY=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.google_cloud_api_key is None


def test_ocr_confidence_threshold_can_be_loaded_from_dotenv(tmp_path: Path) -> None:
    """Verify OCR fallback threshold can be tuned through dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text("OCR_CONFIDENCE_THRESHOLD=0.9\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.ocr_confidence_threshold == 0.9


def test_local_ocr_paddle_options_can_be_loaded_from_dotenv(tmp_path: Path) -> None:
    """Verify PaddleOCR 3.x options can be configured through dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "LOCAL_OCR_ENGINE=paddle_static",
                "LOCAL_OCR_USE_DOC_ORIENTATION_CLASSIFY=true",
                "LOCAL_OCR_USE_DOC_UNWARPING=true",
                "LOCAL_OCR_USE_TEXTLINE_ORIENTATION=true",
                "LOCAL_OCR_PADDLEX_CONFIG=/tmp/paddleocr.yaml",
                "LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR=/models/rec",
                "LOCAL_OCR_TEXT_DETECTION_MODEL_DIR=/models/det",
                "LOCAL_OCR_TEXT_RECOGNITION_MODEL_NAME=korean_PP-OCRv5_mobile_rec",
                "LOCAL_OCR_TEXT_DETECTION_MODEL_NAME=PP-OCRv5_server_det",
                "",
            )
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.local_ocr_engine == "paddle_static"
    assert settings.local_ocr_use_doc_orientation_classify is True
    assert settings.local_ocr_use_doc_unwarping is True
    assert settings.local_ocr_use_textline_orientation is True
    assert settings.local_ocr_paddlex_config == "/tmp/paddleocr.yaml"
    assert settings.local_ocr_text_recognition_model_dir == "/models/rec"
    assert settings.local_ocr_text_detection_model_dir == "/models/det"
    assert settings.local_ocr_text_recognition_model_name == "korean_PP-OCRv5_mobile_rec"
    assert settings.local_ocr_text_detection_model_name == "PP-OCRv5_server_det"


def test_clova_ocr_settings_can_be_loaded_from_dotenv(tmp_path: Path) -> None:
    """Verify CLOVA OCR backup settings can be tuned through dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "ENABLE_CLOVA_OCR=true",
                "ALLOW_EXTERNAL_OCR=true",
                "CLOVA_OCR_API_URL=https://example.apigw.ntruss.com/custom/v1/infer",
                "CLOVA_OCR_SECRET=test-clova-secret",
                "CLOVA_OCR_TIMEOUT_SECONDS=9",
                "CLOVA_OCR_MAX_RETRIES=2",
                "",
            )
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.enable_clova_ocr is True
    assert settings.allow_external_ocr is True
    assert settings.clova_ocr_api_url == "https://example.apigw.ntruss.com/custom/v1/infer"
    assert settings.clova_ocr_secret is not None
    assert settings.clova_ocr_secret.get_secret_value() == "test-clova-secret"
    assert settings.clova_ocr_timeout_seconds == 9
    assert settings.clova_ocr_max_retries == 2


@pytest.mark.parametrize("threshold", (-0.01, 1.01))
def test_ocr_confidence_threshold_is_bounded(threshold: float) -> None:
    """Verify OCR confidence threshold stays in the provider confidence range."""
    with pytest.raises(ValidationError, match="ocr_confidence_threshold"):
        Settings(_env_file=None, ocr_confidence_threshold=threshold)


@pytest.mark.parametrize(
    ("setting_name", "value"),
    (
        ("clova_ocr_timeout_seconds", 0),
        ("clova_ocr_timeout_seconds", 61),
        ("clova_ocr_max_retries", -1),
        ("clova_ocr_max_retries", 4),
    ),
)
def test_clova_ocr_retry_settings_are_bounded(setting_name: str, value: int) -> None:
    """Verify CLOVA timeout/retry settings stay within reviewed operational limits."""
    with pytest.raises(ValidationError, match=setting_name):
        Settings(_env_file=None, **cast(dict[str, Any], {setting_name: value}))


def test_official_barcode_lookup_keys_can_be_loaded_from_dotenv(tmp_path: Path) -> None:
    """Verify FoodQR and FoodSafetyKorea key placeholders can be filled through dotenv."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "ENABLE_BARCODE_LOOKUP=true",
                "FOODQR_SERVICE_KEY=test-foodqr-key",
                "FOODQR_BASE_URL=https://apis.data.go.kr/1471000/FoodQrInfoService01",
                "FOODQR_PRODUCT_LIST_PATH=/getFoodQrProdList01",
                "FOODQR_PRODUCT_MANUFACTURING_PATH=/configured-test-endpoint",
                "FOODQR_TIMEOUT_SECONDS=7",
                "FOODQR_MAX_RETRIES=1",
                "FOODQR_NUM_OF_ROWS=5",
                "MFDS_API_KEY=test-mfds-key",
                "MFDS_OPENAPI_BASE_URL=http://openapi.foodsafetykorea.go.kr/api",
                "MFDS_OPENAPI_TIMEOUT_SECONDS=8",
                "MFDS_OPENAPI_MAX_RETRIES=1",
                "MFDS_OPENAPI_PAGE_SIZE=20",
                "",
            )
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.enable_barcode_lookup is True
    assert settings.foodqr_service_key is not None
    assert settings.foodqr_service_key.get_secret_value() == "test-foodqr-key"
    assert settings.foodqr_base_url == "https://apis.data.go.kr/1471000/FoodQrInfoService01"
    assert settings.foodqr_product_list_path == "/getFoodQrProdList01"
    assert settings.foodqr_product_manufacturing_path == "/configured-test-endpoint"
    assert settings.foodqr_timeout_seconds == 7
    assert settings.foodqr_max_retries == 1
    assert settings.foodqr_num_of_rows == 5
    assert settings.mfds_api_key is not None
    assert settings.mfds_api_key.get_secret_value() == "test-mfds-key"
    assert settings.mfds_openapi_base_url == "http://openapi.foodsafetykorea.go.kr/api"
    assert settings.mfds_openapi_timeout_seconds == 8
    assert settings.mfds_openapi_max_retries == 1
    assert settings.mfds_openapi_page_size == 20


def test_empty_official_barcode_lookup_keys_are_ignored(tmp_path: Path) -> None:
    """Verify empty FoodQR and MFDS dotenv placeholders do not become active secrets."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FOODQR_SERVICE_KEY=\nMFDS_API_KEY=\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.foodqr_service_key is None
    assert settings.mfds_api_key is None


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


def test_public_staging_requires_jwt_configuration() -> None:
    """Verify internet-facing staging cannot run with auth disabled."""
    kwargs = _valid_public_staging_kwargs()
    kwargs["auth_mode"] = "disabled"

    with pytest.raises(ValidationError, match="AUTH_MODE=jwt"):
        Settings(**kwargs)


def test_public_staging_rejects_wildcard_origins_and_hosts() -> None:
    """Verify internet-facing staging requires explicit CORS and host settings."""
    kwargs = _valid_public_staging_kwargs()
    kwargs["allowed_origins"] = ["*"]
    kwargs["allowed_hosts"] = ["*"]

    with pytest.raises(ValidationError, match="wildcards"):
        Settings(**kwargs)


def test_public_staging_rejects_non_https_origins() -> None:
    """Verify internet-facing staging rejects cleartext CORS origins."""
    kwargs = _valid_public_staging_kwargs()
    kwargs["allowed_origins"] = ["http://staging-app.example.com"]

    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS must use https"):
        Settings(**kwargs)


def test_public_staging_requires_rate_limit() -> None:
    """Verify internet-facing staging must enable rate limiting."""
    kwargs = _valid_public_staging_kwargs()
    kwargs["rate_limit_enabled"] = False

    with pytest.raises(ValidationError, match="RATE_LIMIT_ENABLED"):
        Settings(**kwargs)


def test_public_staging_rejects_non_https_jwks_url() -> None:
    """Verify internet-facing staging JWKS URL must use HTTPS."""
    kwargs = _valid_public_staging_kwargs()
    kwargs["jwt_jwks_url"] = "http://auth.example.com/.well-known/jwks.json"

    with pytest.raises(ValidationError, match="JWT_JWKS_URL"):
        Settings(**kwargs)


def test_valid_public_staging_settings_load() -> None:
    """Verify public staging accepts the release-gate security baseline."""
    settings = Settings(**_valid_public_staging_kwargs())

    assert settings.environment == "staging"
    assert settings.deployment_exposure == "public"
    assert settings.auth_mode == "jwt"
    assert settings.rate_limit_enabled is True


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


def test_production_requires_official_key_for_barcode_lookup() -> None:
    """Verify production barcode lookup cannot run without an official provider key."""
    kwargs = _valid_production_kwargs()
    kwargs["_env_file"] = None
    kwargs["enable_barcode_lookup"] = True

    with pytest.raises(ValidationError, match="FOODQR_SERVICE_KEY or MFDS_API_KEY"):
        Settings(**kwargs)


def test_production_rejects_wildcard_origins_and_hosts() -> None:
    """Verify production requires explicit origins and hosts."""
    kwargs = _valid_production_kwargs()
    kwargs["allowed_origins"] = ["*"]
    kwargs["allowed_hosts"] = ["*"]

    with pytest.raises(ValidationError, match="wildcards"):
        Settings(**kwargs)


def test_production_rejects_non_https_origins() -> None:
    """Verify production rejects cleartext CORS origins."""
    kwargs = _valid_production_kwargs()
    kwargs["allowed_origins"] = ["http://app.example.com"]

    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS must use https"):
        Settings(**kwargs)


def test_production_requires_jwt_configuration() -> None:
    """Verify production user apps must be configured for OAuth/OIDC JWT."""
    kwargs = _valid_production_kwargs()
    kwargs["auth_mode"] = "disabled"
    kwargs["jwt_issuer"] = None

    with pytest.raises(ValidationError, match="AUTH_MODE=jwt"):
        Settings(**kwargs)


def test_production_requires_rate_limit() -> None:
    """Verify production public API cannot boot without rate limiting."""
    kwargs = _valid_production_kwargs()
    kwargs["rate_limit_enabled"] = False

    with pytest.raises(ValidationError, match="RATE_LIMIT_ENABLED"):
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


def test_production_rejects_roi_crop_policy_without_vision_gate() -> None:
    """Verify ROI crop policy cannot be enabled without the YOLO gate."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_roi_preprocessing_policy"] = "crop_before_primary"

    with pytest.raises(ValidationError, match="OCR_ROI_PREPROCESSING_POLICY"):
        Settings(**kwargs)


def test_production_rejects_multimodal_verification_without_llm_gate() -> None:
    """Verify verification cannot run without the local multimodal gate."""
    kwargs = _valid_production_kwargs()
    kwargs["enable_multimodal_verification"] = True
    kwargs["multimodal_verification_sample_rate"] = 1.0

    with pytest.raises(ValidationError, match="ENABLE_MULTIMODAL_VERIFICATION"):
        Settings(**kwargs)


def test_production_accepts_local_paddleocr_primary() -> None:
    """Verify production can use local PaddleOCR as the primary OCR provider."""
    kwargs = _valid_production_kwargs()

    settings = Settings(**kwargs)

    assert settings.ocr_primary_provider == "paddleocr"
    assert settings.enable_local_ocr is True


def test_production_rejects_local_ocr_fallback_without_signoff() -> None:
    """Verify local OCR fallback remains sign-off gated when primary is not PaddleOCR."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "none"
    kwargs["enable_local_ocr"] = True

    with pytest.raises(ValidationError, match="local OCR fallback"):
        Settings(**kwargs)


def test_production_rejects_clova_ocr_without_external_gate() -> None:
    """Verify CLOVA fallback cannot run while external OCR is disabled."""
    kwargs = _valid_production_kwargs()
    kwargs["enable_clova_ocr"] = True
    kwargs["clova_ocr_api_url"] = "https://example.apigw.ntruss.com/custom/v1/infer"
    kwargs["clova_ocr_secret"] = "secret"

    with pytest.raises(ValidationError, match="ALLOW_EXTERNAL_OCR"):
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


def test_production_rejects_learning_object_storage_without_signoff() -> None:
    """Verify production cannot enable learning object storage before sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs["learning_object_storage_provider"] = "s3"
    kwargs["learning_object_storage_bucket"] = "learning-images"

    with pytest.raises(ValidationError, match="LEARNING_OBJECT_STORAGE_PROVIDER"):
        Settings(**kwargs)


def test_production_rejects_regulated_raw_image_retention_without_signoff() -> None:
    """Verify regulated document raw images remain memory-only before sign-off."""
    kwargs = _valid_production_kwargs()
    kwargs["sensitive_document_original_image_retention_seconds"] = 60

    with pytest.raises(
        ValidationError,
        match="SENSITIVE_DOCUMENT_ORIGINAL_IMAGE_RETENTION_SECONDS",
    ):
        Settings(**kwargs)


def test_s3_learning_object_storage_requires_bucket() -> None:
    """Verify S3 learning object storage cannot start without a bucket."""
    with pytest.raises(ValidationError, match="LEARNING_OBJECT_STORAGE_BUCKET"):
        Settings(_env_file=None, learning_object_storage_provider="s3")


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


def test_implementation_readiness_ocr_defaults_use_local_paddle() -> None:
    """Verify the readiness manifest keeps external OCR off while PaddleOCR is primary."""
    manifest = _load_json_object(READINESS_SETTINGS_PATH)
    environment_variables = _object_field(manifest, "environment_variables")
    ocr_settings = _object_field(environment_variables, "ocr")

    primary_provider = _object_field(ocr_settings, "OCR_PRIMARY_PROVIDER")
    allow_external_ocr = _object_field(ocr_settings, "ALLOW_EXTERNAL_OCR")
    auth_mode = _object_field(ocr_settings, "GOOGLE_VISION_AUTH_MODE")
    credentials = _object_field(ocr_settings, "GOOGLE_APPLICATION_CREDENTIALS")
    confidence_threshold = _object_field(ocr_settings, "OCR_CONFIDENCE_THRESHOLD")
    clova_timeout = _object_field(ocr_settings, "CLOVA_OCR_TIMEOUT_SECONDS")
    clova_max_retries = _object_field(ocr_settings, "CLOVA_OCR_MAX_RETRIES")

    assert primary_provider["default"] == "paddleocr"
    assert allow_external_ocr["default"] is False
    assert auth_mode["default"] == "api_key"
    assert auth_mode["production_required_value"] == "adc"
    assert credentials["default"] is None
    assert confidence_threshold["default"] == 0.85
    assert clova_timeout["default"] == 15
    assert clova_max_retries["default"] == 1


def test_production_requires_external_ocr_gate_for_google_vision() -> None:
    """Verify production cannot enable Google Vision while the external gate is off."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "google_vision"
    kwargs["google_vision_auth_mode"] = "adc"
    kwargs["google_cloud_project"] = "lemon-prod"

    with pytest.raises(ValidationError, match="ALLOW_EXTERNAL_OCR"):
        Settings(**kwargs)


def test_production_requires_adc_for_google_vision() -> None:
    """Verify production Google Vision cannot use API key auth."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "google_vision"
    kwargs["allow_external_ocr"] = True
    kwargs["google_vision_auth_mode"] = "api_key"
    kwargs["google_cloud_api_key"] = "local-only-key"
    kwargs["google_cloud_project"] = "lemon-prod"

    with pytest.raises(ValidationError, match="GOOGLE_VISION_AUTH_MODE=adc"):
        Settings(**kwargs)


def test_production_requires_project_for_google_vision_adc() -> None:
    """Verify production Google Vision ADC mode pins the quota project."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "google_vision"
    kwargs["allow_external_ocr"] = True
    kwargs["google_vision_auth_mode"] = "adc"

    with pytest.raises(ValidationError, match="GOOGLE_CLOUD_PROJECT"):
        Settings(**kwargs)


def test_production_rejects_google_application_credentials_for_google_vision() -> None:
    """Verify production Google Vision does not use checked-in JSON credential paths."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "google_vision"
    kwargs["allow_external_ocr"] = True
    kwargs["google_vision_auth_mode"] = "adc"
    kwargs["google_cloud_project"] = "lemon-prod"
    kwargs["google_application_credentials"] = "/run/secrets/google-service-account.json"

    with pytest.raises(ValidationError, match="GOOGLE_APPLICATION_CREDENTIALS"):
        Settings(**kwargs)


def test_valid_production_google_vision_adc_settings_load() -> None:
    """Verify production accepts Google Vision only through attached-account ADC mode."""
    kwargs = _valid_production_kwargs()
    kwargs["ocr_primary_provider"] = "google_vision"
    kwargs["enable_local_ocr"] = False
    kwargs["allow_external_ocr"] = True
    kwargs["google_vision_auth_mode"] = "adc"
    kwargs["google_cloud_project"] = "lemon-prod"

    settings = Settings(**kwargs)

    assert settings.ocr_primary_provider == "google_vision"
    assert settings.allow_external_ocr is True
    assert settings.google_vision_auth_mode == "adc"
    assert settings.google_cloud_project == "lemon-prod"


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

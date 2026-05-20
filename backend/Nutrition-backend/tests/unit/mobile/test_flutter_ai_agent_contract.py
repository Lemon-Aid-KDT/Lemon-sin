"""Static contract checks for the Flutter AI Agent mobile shell."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
APP_ROOT = REPO_ROOT / "mobile" / "flutter_app"


def test_flutter_ai_agent_shell_files_exist() -> None:
    """Verify the mobile shell has the app, config, client, and screen files."""
    expected_paths = [
        APP_ROOT / "pubspec.yaml",
        APP_ROOT / "lib" / "main.dart",
        APP_ROOT / "lib" / "app.dart",
        APP_ROOT / "lib" / "core" / "config" / "app_config.dart",
        APP_ROOT / "lib" / "core" / "network" / "lemon_api_client.dart",
        APP_ROOT / "lib" / "core" / "storage" / "auth_token_store.dart",
        APP_ROOT / "lib" / "features" / "dashboard" / "presentation" / "dashboard_screen.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "data"
        / "ai_coaching_repository.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "domain"
        / "ai_coaching_models.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "presentation"
        / "daily_coaching_screen.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "data"
        / "supplement_capture_repository.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "domain"
        / "supplement_analysis_preview.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "presentation"
        / "supplement_capture_screen.dart",
        APP_ROOT / "lib" / "shared" / "widgets" / "medical_disclaimer.dart",
    ]

    missing = [str(path.relative_to(REPO_ROOT)) for path in expected_paths if not path.exists()]
    assert missing == []


def test_flutter_ai_agent_client_uses_backend_contract_paths() -> None:
    """Verify the shell calls the real consent and daily-coaching endpoints."""
    repository = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "data"
        / "ai_coaching_repository.dart"
    ).read_text(encoding="utf-8")
    config = (APP_ROOT / "lib" / "core" / "config" / "app_config.dart").read_text(
        encoding="utf-8"
    )

    assert "/api/v1/me/privacy/consents/sensitive_health_analysis" in repository
    assert "/api/v1/ai-agent/daily-coaching" in repository
    assert "LEMON_API_BASE_URL" in config
    assert "LEMON_AUTH_TOKEN" in config


def test_flutter_shell_routes_and_sensitive_storage_are_wired() -> None:
    """Verify dashboard routing and secure token storage are present."""
    app = (APP_ROOT / "lib" / "app.dart").read_text(encoding="utf-8")
    pubspec = (APP_ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    token_store = (
        APP_ROOT / "lib" / "core" / "storage" / "auth_token_store.dart"
    ).read_text(encoding="utf-8")
    capture_screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "presentation"
        / "supplement_capture_screen.dart"
    ).read_text(encoding="utf-8")

    assert "path: '/coaching'" in app
    assert "path: '/supplement-capture'" in app
    assert "flutter_secure_storage" in pubspec
    assert "flutter_secure_storage" in token_store
    assert "Permission.camera.request()" in capture_screen
    assert "ImageSource.camera" in capture_screen
    assert "ImageSource.gallery" in capture_screen


def test_flutter_supplement_capture_calls_backend_analyze_contract() -> None:
    """Verify supplement capture uses the real consent and multipart analyze endpoints."""
    client = (APP_ROOT / "lib" / "core" / "network" / "lemon_api_client.dart").read_text(
        encoding="utf-8"
    )
    repository = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "data"
        / "supplement_capture_repository.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "presentation"
        / "supplement_capture_screen.dart"
    ).read_text(encoding="utf-8")

    assert "postMultipart" in client
    assert "FormData.fromMap" in repository
    assert "MultipartFile.fromBytes" in repository
    assert "/api/v1/me/privacy/consents/ocr_image_processing" in repository
    assert "/api/v1/supplements/analyze" in repository
    assert "grantOcrImageProcessingConsent" in screen
    assert "analyzeLabelImage" in screen


def test_flutter_daily_coaching_request_is_confirmed_only() -> None:
    """Verify the starter flow sends confirmed OCR data, not preview-only data."""
    models = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "domain"
        / "ai_coaching_models.dart"
    ).read_text(encoding="utf-8")

    assert "'user_confirmed': true" in models
    assert "'raw_ocr_text': 'instant noodles sodium 2600mg'" in models
    assert "'agent_memory'" in models


def test_flutter_ai_agent_screen_includes_disclaimer_and_no_raw_error_leak() -> None:
    """Verify the user-facing screen includes the disclaimer and hides raw errors."""
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "presentation"
        / "daily_coaching_screen.dart"
    ).read_text(encoding="utf-8")
    disclaimer = (APP_ROOT / "lib" / "shared" / "widgets" / "medical_disclaimer.dart").read_text(
        encoding="utf-8"
    )

    assert "MedicalDisclaimer" in screen
    assert "error.toString()" not in screen
    assert "진단과 처방을 대체하지 않습니다" in disclaimer

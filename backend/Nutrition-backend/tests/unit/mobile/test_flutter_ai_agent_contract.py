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

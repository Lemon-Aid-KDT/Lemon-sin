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
        APP_ROOT / "lib" / "shared" / "models" / "agent_memory.dart",
        APP_ROOT / "lib" / "shared" / "models" / "analysis_result.dart",
        APP_ROOT / "lib" / "shared" / "models" / "supplement.dart",
        APP_ROOT / "lib" / "shared" / "dev" / "dev_confirmed_samples.dart",
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
        / "shared"
        / "state"
        / "confirmed_entry_store.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "food"
        / "domain"
        / "confirmed_food_entry.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "food"
        / "presentation"
        / "food_capture_screen.dart",
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
        APP_ROOT / "lib" / "shared" / "widgets" / "capture_frame_card.dart",
        APP_ROOT / "lib" / "shared" / "widgets" / "lemon_main_shell.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "chat"
        / "domain"
        / "chat_models.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "chat"
        / "data"
        / "chat_repository.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "chat"
        / "presentation"
        / "chat_screen.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "domain"
        / "notification_models.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "data"
        / "notification_repository.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "presentation"
        / "notification_settings_screen.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "activity"
        / "domain"
        / "activity_models.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "activity"
        / "data"
        / "activity_repository.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "activity"
        / "presentation"
        / "activity_sync_screen.dart",
        APP_ROOT
        / "lib"
        / "features"
        / "capture_result"
        / "presentation"
        / "capture_result_screen.dart",
    ]

    missing = [str(path.relative_to(REPO_ROOT)) for path in expected_paths if not path.exists()]
    assert missing == []


def test_flutter_ai_agent_client_uses_backend_contract_paths() -> None:
    """Verify the shell calls the real consent, coaching, and chat endpoints."""
    repository = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "data"
        / "ai_coaching_repository.dart"
    ).read_text(encoding="utf-8")
    chat_repository = (
        APP_ROOT / "lib" / "features" / "chat" / "data" / "chat_repository.dart"
    ).read_text(encoding="utf-8")
    config = (APP_ROOT / "lib" / "core" / "config" / "app_config.dart").read_text(
        encoding="utf-8"
    )

    assert "/api/v1/me/privacy/consents/sensitive_health_analysis" in repository
    assert "/api/v1/ai-agent/daily-coaching" in repository
    assert "/api/v1/me/privacy/consents/sensitive_health_analysis" in chat_repository
    assert "/api/v1/ai-agent/chat" in chat_repository
    assert "LEMON_API_BASE_URL" in config
    assert "LEMON_AUTH_TOKEN" in config


def test_flutter_client_uses_mobile_safe_base_url_defaults() -> None:
    """Verify local backend defaults work for desktop, web, and Android emulator."""
    config = (APP_ROOT / "lib" / "core" / "config" / "app_config.dart").read_text(
        encoding="utf-8"
    )
    client = (APP_ROOT / "lib" / "core" / "network" / "lemon_api_client.dart").read_text(
        encoding="utf-8"
    )

    assert "defaultApiBaseUrl" in config
    assert "LEMON_API_BASE_URL" in config
    assert "TargetPlatform.android" in config
    assert "http://10.0.2.2:18080" in config
    assert "http://localhost:18080" in config
    assert "http://127.0.0.1:18080" in config
    assert "connectTimeout" in client
    assert "receiveTimeout" in client
    assert "validateStatus" in client


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
    capture_frame = (
        APP_ROOT / "lib" / "shared" / "widgets" / "capture_frame_card.dart"
    ).read_text(encoding="utf-8")

    assert "path: '/coaching'" in app
    assert "path: '/chat'" in app
    assert "path: '/notifications'" in app
    assert "path: '/activity'" in app
    assert "path: '/supplement-capture'" in app
    assert "path: '/food-capture'" in app
    assert "path: '/entry-result'" in app
    assert "flutter_secure_storage" in pubspec
    assert "flutter_secure_storage" in token_store
    assert "Permission.camera.request()" in capture_screen
    assert "ImageSource.camera" in capture_frame
    assert "ImageSource.gallery" in capture_frame


def test_flutter_notification_settings_contract_is_wired() -> None:
    """Verify notification settings models, repository, and route are present."""
    app = (APP_ROOT / "lib" / "app.dart").read_text(encoding="utf-8")
    dashboard = (
        APP_ROOT / "lib" / "features" / "dashboard" / "presentation" / "dashboard_screen.dart"
    ).read_text(encoding="utf-8")
    models = (
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "domain"
        / "notification_models.dart"
    ).read_text(encoding="utf-8")
    repository = (
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "data"
        / "notification_repository.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "notifications"
        / "presentation"
        / "notification_settings_screen.dart"
    ).read_text(encoding="utf-8")

    assert "NotificationSettingsScreen" in app
    assert "path: '/notifications'" in app
    assert "context.go('/notifications')" in dashboard
    assert "class ReminderPreference" in models
    assert "ReminderCategory" in models
    assert "supplement_reminder" in models
    assert "meal_check_in" in models
    assert "daily_coaching_prompt" in models
    assert "safety_follow_up" in models
    assert "/api/v1/notifications/reminders" in repository
    assert "grantSensitiveHealthAnalysisConsent" in repository
    assert "SwitchListTile" in screen
    assert "DropdownButtonFormField" in screen
    assert "TextField" in screen
    assert "MedicalDisclaimer" in screen
    assert "진단" not in screen
    assert "처방" not in screen
    assert "치료" not in screen


def test_flutter_activity_context_is_manual_first_and_confirmed_only() -> None:
    """Verify activity context uses confirmed manual data and has disabled bridge UI."""
    app = (APP_ROOT / "lib" / "app.dart").read_text(encoding="utf-8")
    dashboard = (
        APP_ROOT / "lib" / "features" / "dashboard" / "presentation" / "dashboard_screen.dart"
    ).read_text(encoding="utf-8")
    models = (
        APP_ROOT / "lib" / "features" / "activity" / "domain" / "activity_models.dart"
    ).read_text(encoding="utf-8")
    repository = (
        APP_ROOT / "lib" / "features" / "activity" / "data" / "activity_repository.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "activity"
        / "presentation"
        / "activity_sync_screen.dart"
    ).read_text(encoding="utf-8")
    coaching_models = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "domain"
        / "ai_coaching_models.dart"
    ).read_text(encoding="utf-8")
    store = (
        APP_ROOT / "lib" / "shared" / "state" / "confirmed_entry_store.dart"
    ).read_text(encoding="utf-8")

    assert "ActivitySyncScreen" in app
    assert "path: '/activity'" in app
    assert "context.go('/activity')" in dashboard
    assert "class ConfirmedActivityEntry" in models
    assert "steps" in models
    assert "activeMinutes" in models
    assert "activityEnergyKcal" in models
    assert "workoutType" in models
    assert "userConfirmed" in models
    assert "'user_confirmed': true" in models
    assert "sleep" not in models
    assert "blood_glucose" not in models
    assert "blood_pressure" not in models
    assert "createManualActivity" in repository
    assert "ConfirmedEntryStore.instance.addActivity" in screen
    assert "HealthKit" in screen
    assert "Health Connect" in screen
    assert "onPressed: null" in screen
    assert "activities.where" in coaching_models
    assert "toAgentHealthTrendJson" in coaching_models
    assert "addActivity" in store


def test_flutter_chat_mvp_uses_safe_contract_and_navigation() -> None:
    """Verify chat DTO, repository, and UI are wired to the chatbot endpoint."""
    app = (APP_ROOT / "lib" / "app.dart").read_text(encoding="utf-8")
    dashboard = (
        APP_ROOT / "lib" / "features" / "dashboard" / "presentation" / "dashboard_screen.dart"
    ).read_text(encoding="utf-8")
    models = (
        APP_ROOT / "lib" / "features" / "chat" / "domain" / "chat_models.dart"
    ).read_text(encoding="utf-8")
    repository = (
        APP_ROOT / "lib" / "features" / "chat" / "data" / "chat_repository.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT / "lib" / "features" / "chat" / "presentation" / "chat_screen.dart"
    ).read_text(encoding="utf-8")

    assert "ChatScreen" in app
    assert "path: '/chat'" in app
    assert "context.go('/chat')" in dashboard
    assert "class ChatTurn" in models
    assert "class ChatbotRequest" in models
    assert "class ChatbotResponse" in models
    assert "class ChatbotSource" in models
    assert "requires_user_approval" in models
    assert "source_families" in models
    assert "sourceFamilies" in models
    assert "answerability" in models
    assert "final String answerability" in models
    assert "final List<ChatbotSource> sources" in models
    assert "source_id" in models
    assert "version_label" in models
    assert "expires_at" in models
    assert "source_url" in models
    assert "boundary_code" in models
    assert "boundaryCode" in models
    assert "hasReviewedSources" in models
    assert "usedAgentMemory" in models
    assert "/api/v1/ai-agent/chat" in repository
    assert "grantSensitiveHealthAnalysisConsent" in repository
    assert "TextField" in screen
    assert "IconButton" in screen
    assert "provider" in screen
    assert "memory" in screen
    assert "answerability" in screen
    assert "_answerabilityLabel" in screen
    assert "sourceFamilies" in screen
    assert "hasReviewedSources" in screen
    assert "_SourceBasisPanel" in screen
    assert "검수 근거" in screen
    assert "_sourceLabel" in screen
    assert "_sourceFamilyLabel" in screen
    assert "boundaryCode" in screen
    assert "nutrition_reference" in screen
    assert "영양 기준" in screen
    assert "supplement_reference" in screen
    assert "영양제 참고" in screen
    assert "MedicalDisclaimer" in screen
    assert "error.toString()" not in screen


def test_flutter_chat_cta_contract_is_wired_without_direct_checklist_save() -> None:
    """Verify chatbot CTA values are parsed and checklist CTA opens edit UI first."""
    models = (
        APP_ROOT
        / "lib"
        / "features"
        / "chat"
        / "domain"
        / "chat_models.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT / "lib" / "features" / "chat" / "presentation" / "chat_screen.dart"
    ).read_text(encoding="utf-8")

    assert "enum ChatbotCta" in models
    assert "ctas" in models
    assert "take(2)" in models
    assert "hasCtas" in models
    assert "complete_missing_record" in models
    assert "run_or_refresh_analysis" in models
    assert "add_checklist_item" in models
    assert "ask_about_this_result" in models
    assert "_ChatCtaPanel" in screen
    assert "showModalBottomSheet" in screen
    assert "addChecklistItem" in screen
    assert "체크리스트 편집" in screen
    assert "바로 저장하지 않고" in screen
    assert "runOrRefreshAnalysis" in screen
    assert "askAboutThisResult" in screen


def test_flutter_food_capture_collects_confirmed_input_without_nutrient_guessing() -> None:
    """Verify food flow captures confirmed manual input without inventing nutrients."""
    app = (APP_ROOT / "lib" / "app.dart").read_text(encoding="utf-8")
    dashboard = (
        APP_ROOT / "lib" / "features" / "dashboard" / "presentation" / "dashboard_screen.dart"
    ).read_text(encoding="utf-8")
    entry = (
        APP_ROOT / "lib" / "features" / "food" / "domain" / "confirmed_food_entry.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT / "lib" / "features" / "food" / "presentation" / "food_capture_screen.dart"
    ).read_text(encoding="utf-8")
    capture_frame = (
        APP_ROOT / "lib" / "shared" / "widgets" / "capture_frame_card.dart"
    ).read_text(encoding="utf-8")

    assert "FoodCaptureScreen" in app
    assert "context.go('/food-capture')" in dashboard
    assert "class ConfirmedFoodEntry" in entry
    assert "'source_type': 'food_user_input'" in entry
    assert "'user_confirmed': true" in entry
    assert "'nutrients'" not in entry
    assert "food_recognition" not in entry
    assert "nutrition_lookup" not in entry
    assert "ImageSource.camera" in capture_frame
    assert "ImageSource.gallery" in capture_frame
    assert "_confirmedForAgentPayload" in screen
    assert "userConfirmed" in screen


def test_flutter_confirmed_entries_are_shared_with_daily_coaching() -> None:
    """Verify confirmed food/supplements are handed off to daily coaching state."""
    store = (
        APP_ROOT / "lib" / "shared" / "state" / "confirmed_entry_store.dart"
    ).read_text(encoding="utf-8")
    food_screen = (
        APP_ROOT / "lib" / "features" / "food" / "presentation" / "food_capture_screen.dart"
    ).read_text(encoding="utf-8")
    supplement_screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "presentation"
        / "supplement_capture_screen.dart"
    ).read_text(encoding="utf-8")
    coaching_screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "presentation"
        / "daily_coaching_screen.dart"
    ).read_text(encoding="utf-8")

    assert "class ConfirmedEntryStore" in store
    assert "static final ConfirmedEntryStore instance" in store
    assert "addFood" in store
    assert "addSupplement" in store
    assert "ConfirmedEntryStore.instance.addFood" in food_screen
    assert "ConfirmedEntryStore.instance.addSupplement" in supplement_screen
    assert "ConfirmedEntryStore.instance.foods" in coaching_screen
    assert "ConfirmedEntryStore.instance.supplements" in coaching_screen
    assert "DailyCoachingRequest.fromConfirmedInputs" in coaching_screen


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


def test_flutter_supplement_capture_can_save_user_confirmed_records() -> None:
    """Verify supplement preview confirmation posts only user-confirmed records."""
    repository = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "data"
        / "supplement_capture_repository.dart"
    ).read_text(encoding="utf-8")
    preview = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "domain"
        / "supplement_analysis_preview.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "presentation"
        / "supplement_capture_screen.dart"
    ).read_text(encoding="utf-8")

    assert "saveConfirmedSupplement" in repository
    assert "/api/v1/me/privacy/consents/sensitive_health_analysis" in repository
    assert "grantSensitiveHealthAnalysisConsent" in repository
    assert "_client.postJson(" in repository
    assert "'/api/v1/supplements'" in repository
    assert "SupplementConfirmedInput" in preview
    assert "analysisId" in preview
    assert "'user_confirmed': true" in preview
    assert "saveConfirmedSupplement" in screen
    assert "_confirmedForSave" in screen


def test_flutter_taedong_compatible_models_preserve_raw_payloads() -> None:
    """Verify bridge models match taedong-style loose payload handling."""
    agent_memory = (
        APP_ROOT / "lib" / "shared" / "models" / "agent_memory.dart"
    ).read_text(encoding="utf-8")
    analysis_result = (
        APP_ROOT / "lib" / "shared" / "models" / "analysis_result.dart"
    ).read_text(encoding="utf-8")
    supplement = (
        APP_ROOT / "lib" / "shared" / "models" / "supplement.dart"
    ).read_text(encoding="utf-8")

    assert "class AgentMemory" in agent_memory
    assert "memory_summary" in agent_memory
    assert "Map<String, dynamic>.from(json)" in agent_memory
    assert "class AnalysisResult" in analysis_result
    assert "analysis_type" in analysis_result
    assert "result_snapshot" in analysis_result
    assert "user_confirmed" in analysis_result
    assert "class Supplement" in supplement
    assert "analysis_status" in supplement
    assert "ingredients" in supplement
    assert "candidates" in supplement
    assert "Map<String, dynamic>.from(json)" in supplement


def test_flutter_daily_coaching_request_is_confirmed_only() -> None:
    """Verify daily coaching uses confirmed entries without hard-coded nutrient guesses."""
    models = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "domain"
        / "ai_coaching_models.dart"
    ).read_text(encoding="utf-8")
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "presentation"
        / "daily_coaching_screen.dart"
    ).read_text(encoding="utf-8")
    food_entry = (
        APP_ROOT / "lib" / "features" / "food" / "domain" / "confirmed_food_entry.dart"
    ).read_text(encoding="utf-8")
    supplement_preview = (
        APP_ROOT
        / "lib"
        / "features"
        / "supplement"
        / "domain"
        / "supplement_analysis_preview.dart"
    ).read_text(encoding="utf-8")

    assert "fromConfirmedInputs" in models
    assert "ConfirmedFoodEntry" in models
    assert "SupplementConfirmedInput" in models
    assert "toAgentSupplementJson" in models
    assert "'product_name': displayName" in supplement_preview
    assert "'name': displayName" in supplement_preview
    assert "'times_per_day'" in supplement_preview
    assert "'user_confirmed': true" in food_entry
    assert "'user_confirmed': true" in supplement_preview
    assert "'raw_ocr_text'" not in models
    assert "'nutrients'" not in models
    assert "instant noodles" not in models
    assert "sodium 2600mg" not in models
    assert "confirmedMealSample" not in screen
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
    assert "오늘의 요약" in screen
    assert "권장 행동" in screen
    assert "참고 및 주의" in screen
    assert "_visibleSafetyWarnings" in screen
    assert "Trace text blocked" not in screen
    assert "Forbidden medical expression detected" not in screen
    assert "진단과 처방을 대체하지 않습니다" in disclaimer


def test_flutter_dev_sample_is_debug_only_and_confirmed_only() -> None:
    """Verify photo-free LLM demo seeds confirmed payloads only in debug UI."""
    screen = (
        APP_ROOT
        / "lib"
        / "features"
        / "ai_coaching"
        / "presentation"
        / "daily_coaching_screen.dart"
    ).read_text(encoding="utf-8")
    sample = (APP_ROOT / "lib" / "shared" / "dev" / "dev_confirmed_samples.dart").read_text(
        encoding="utf-8"
    )

    assert "kDebugMode" in screen
    assert "seedDevConfirmedEntries" in screen
    assert "ConfirmedFoodEntry" in sample
    assert "SupplementConfirmedInput" in sample
    assert "nutrients" not in sample
    assert "raw_ocr_text" not in sample

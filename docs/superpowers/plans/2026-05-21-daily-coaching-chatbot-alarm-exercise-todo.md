# Daily Coaching, Chatbot, Alarm, Exercise Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Daily Coaching 응답 품질을 제품 기준으로 고정하고, 그 구조를 재사용해 챗봇 MVP, 알람, 운동 앱 연동을 단계적으로 구현한다.

**Architecture:** 결정권은 deterministic nutrition/supplement/activity 로직에 두고, LLM은 설명과 코칭 말투를 담당한다. `daily-coaching`은 오늘의 요약 카드 경험의 기준 API로 유지하고, 챗봇은 같은 안전 문구와 context 조립 방식을 재사용하는 별도 endpoint로 확장한다. 알람과 운동 앱 연동은 챗봇 이후에 붙이며, 각각 동의/저장/preview boundary를 먼저 정의한 뒤 모바일 화면과 backend persistence를 연결한다.

**Tech Stack:** FastAPI, PostgreSQL, Alembic, `backend/ai_agent_chat`, SGLang OpenAI-compatible endpoint, Flutter/Dio, HealthKit/Health Connect 후보, Python pytest, Flutter analyze/test.

---

## Current Status

- [x] Active worktree: `C:\MyWorkspace\lemon_aid\ai-agent-backend-integration`
- [x] Active branch: `feat/ai-agent-backend-integration`
- [x] `daily-coaching` confirmed food/supplement payload flow is already connected.
- [x] `daily-coaching` preview/unconfirmed input must not update `agent_memory` or final run logs.
- [x] Local SGLang is reachable at `http://localhost:30000/v1/models`.
- [x] FastAPI health endpoint is reachable at `http://localhost:18080/health`.
- [x] Daily Coaching response wording is being standardized as `오늘의 요약`, `권장 행동`, `참고 및 주의`.

## Product Boundary

- [x] Do not implement chatbot, alarms, or exercise sync inside the Daily Coaching quality pass.
- [x] Do not add DB schema for future features until the feature task explicitly starts.
- [x] Do not let LLM invent nutrient values, exercise prescriptions, diagnoses, treatments, or medication advice.
- [x] Keep provider/memory diagnostics available as small badges, not as user-facing raw trace text.
- [x] Keep any sample/demo action debug-only.

---

## Task 1: Lock Daily Coaching Product Response Quality

**Files:**
- Modify: `backend/ai_agent_chat/src/lemon_ai_agent/agents/chat.py`
- Test: `backend/ai_agent_chat/tests/test_chat_agent_language.py`
- Test: `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/domain/ai_coaching_models.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/presentation/daily_coaching_screen.dart`
- Test: `mobile/flutter_app/test/confirmed_payload_test.dart`
- Test: `backend/Nutrition-backend/tests/unit/mobile/test_flutter_ai_agent_contract.py`

- [x] Replace English fallback wording with Korean product wording.
- [x] Keep `message`, `findings`, `recommendations`, `safety_warnings`, `provider`, and `used_tools` contract-compatible.
- [x] Parse `recommendations` in Flutter without adding new API fields.
- [x] Render Daily Coaching as three cards: `오늘의 요약`, `권장 행동`, `참고 및 주의`.
- [x] Hide raw `trace`, `supplement totals`, `nutrition findings`, and policy guard strings from user-facing text.
- [x] Add tests for Korean fallback, Korean-only SGLang prompt, and unsafe LLM fallback.
- [x] Add API tests that verify existing response fields stay present.
- [x] Add Flutter contract/unit tests for recommendations parsing and card UI strings.
- [x] Run: `python -m pytest --no-cov backend\ai_agent_chat\tests`
  - Expected: tests pass, with optional SGLang live smoke skipped unless explicitly enabled.
- [x] Run: `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py`
  - Expected: all selected API/mobile contract tests pass.
- [x] Run: `C:\src\flutter\bin\flutter.bat analyze`
  - Expected: `No issues found`.
- [x] Run: `C:\src\flutter\bin\flutter.bat test`
  - Expected: all Flutter tests pass.

## Task 2: Start Chatbot MVP From the Same Coaching Contract

**Files:**
- Create: `backend/ai_agent_chat/src/lemon_ai_agent/chat_session.py`
- Create: `backend/ai_agent_chat/src/lemon_ai_agent/agents/chatbot.py`
- Modify: `backend/Nutrition-backend/src/api/v1/ai_agent.py`
- Test: `backend/ai_agent_chat/tests/test_chatbot_agent.py`
- Test: `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
- Create: `mobile/flutter_app/lib/features/chat/domain/chat_models.dart`
- Create: `mobile/flutter_app/lib/features/chat/data/chat_repository.dart`
- Create: `mobile/flutter_app/lib/features/chat/presentation/chat_screen.dart`
- Modify: `mobile/flutter_app/lib/app.dart`
- Test: `backend/Nutrition-backend/tests/unit/mobile/test_flutter_ai_agent_contract.py`

- [x] Add `ChatTurn` with `role`, `content`, and `created_at`.
- [x] Add `ChatbotRequest` with `request_id`, `user_id`, `message`, `conversation`, and `context`.
- [x] Add `ChatbotResponse` with `request_id`, `message`, `provider`, `used_tools`, `safety_warnings`, and `requires_user_approval`.
- [x] Write failing unit test: unsafe user prompt or unsafe LLM answer returns safe Korean fallback and does not expose raw trace.
- [x] Implement `ChatbotAgent.answer()` by reusing `SafetyGuard`, local LLM clients, and the same Korean product structure from `ChatAgent`.
- [x] Add `POST /api/v1/ai-agent/chat` route behind sensitive-health consent.
- [x] Ensure chat route loads `agent_memory` context but does not write daily coaching memory unless a confirmed structured coaching action is produced.
- [x] Add API test that fake SGLang returns Korean chatbot response with `provider="sglang"`.
- [x] Add API test that preview/unconfirmed context does not call `upsert_daily_coaching_memory` or `record_agent_run` as a completed coaching run.
- [x] Add Flutter chat DTO and repository using `/api/v1/ai-agent/chat`.
- [x] Add a simple chat screen with message list, input box, send button, provider/memory badge, and medical disclaimer.
- [x] Add dashboard route/button to open the chat screen.
- [x] Run: `python -m pytest --no-cov backend\ai_agent_chat\tests\test_chatbot_agent.py`
  - Expected: chatbot unit tests pass.
- [x] Run: `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py`
  - Expected: daily coaching route still passes and new chat route tests pass.
- [x] Run: `C:\src\flutter\bin\flutter.bat analyze`
  - Expected: `No issues found`.
- [x] Run: `C:\src\flutter\bin\flutter.bat test`
  - Expected: all Flutter tests pass.

## Task 3: Add Alarm and Reminder Planning Layer

**Files:**
- Inspect: `docs/Nutrition-docs/dev-guides/17-feedback-and-notifications.md`
- Create: `backend/Nutrition-backend/src/models/db/notification.py`
- Create: `backend/Nutrition-backend/src/models/schemas/notification.py`
- Create: `backend/Nutrition-backend/src/api/v1/notifications.py`
- Modify: `backend/Nutrition-backend/src/api/v1/router.py`
- Test: `backend/Nutrition-backend/tests/integration/api/test_notifications_api.py`
- Create: `mobile/flutter_app/lib/features/notifications/domain/notification_models.dart`
- Create: `mobile/flutter_app/lib/features/notifications/data/notification_repository.dart`
- Create: `mobile/flutter_app/lib/features/notifications/presentation/notification_settings_screen.dart`
- Modify: `mobile/flutter_app/lib/app.dart`

- [x] Define reminder categories: supplement reminder, meal check-in, daily coaching prompt, and safety follow-up.
- [x] Store user reminder preferences separately from push delivery tokens.
- [x] Require sensitive-health consent before creating health-related reminders.
- [x] Add API for listing, creating, updating, and disabling reminders.
- [x] Do not send real push notifications in this task.
- [x] Add tests that disabled reminders are not selected for dispatch.
- [x] Add tests that reminder text avoids diagnosis/treatment/prescription language.
- [x] Add Flutter settings screen for reminder time, category, enabled toggle, and disclaimer.
- [x] Run: `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_notifications_api.py`
  - Expected: notification API tests pass.
- [x] Run: `C:\src\flutter\bin\flutter.bat analyze`
  - Expected: `No issues found`.

## Task 4: Add Exercise App Integration Context

**Files:**
- Inspect: `docs/Nutrition-docs/dev-guides/12-mobile-healthkit-integration.md`
- Inspect: `backend/Nutrition-backend/src/algorithms/activity.py`
- Inspect: `backend/Nutrition-backend/src/api/v1/activity.py`
- Create or modify: `mobile/flutter_app/lib/features/activity/domain/activity_models.dart`
- Create or modify: `mobile/flutter_app/lib/features/activity/data/activity_repository.dart`
- Create: `mobile/flutter_app/lib/features/activity/presentation/activity_sync_screen.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/domain/ai_coaching_models.dart`
- Test: `backend/Nutrition-backend/tests/unit/mobile/test_flutter_ai_agent_contract.py`
- Test: `mobile/flutter_app/test/confirmed_payload_test.dart`

- [x] Decide MVP source: manual activity entry first, then HealthKit/Health Connect bridge.
- [x] Define activity fields for Daily Coaching context: steps, active minutes, activity energy, workout type, source, date, and user confirmation.
- [x] Add mobile activity model that can serialize confirmed activity context into `payload.health_trends` or a dedicated activity context.
- [x] Do not collect sleep, route/location, blood glucose, blood pressure, or menstrual/cycle data in this task.
- [x] Add activity screen with manual entry and a disabled HealthKit/Health Connect placeholder until permission flow is ready.
- [x] Add tests that activity context uses user-confirmed data only.
- [x] Add tests that activity wording remains an exercise/activity recommendation, not medical exercise prescription.
- [x] Run: `python -m pytest --no-cov backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py`
  - Expected: mobile contract tests pass.
- [x] Run: `C:\src\flutter\bin\flutter.bat test`
  - Expected: all Flutter tests pass.

## Task 5: Connect Chatbot, Alarm, and Exercise Context Back Into Daily Coaching

**Files:**
- Modify: `backend/ai_agent_chat/src/lemon_ai_agent/adapters/app.py`
- Modify: `backend/ai_agent_chat/src/lemon_ai_agent/agents/chat.py`
- Modify: `backend/ai_agent_chat/src/lemon_ai_agent/agents/chatbot.py`
- Modify: `backend/Nutrition-backend/src/api/v1/ai_agent.py`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/domain/ai_coaching_models.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/presentation/daily_coaching_screen.dart`
- Test: `backend/ai_agent_chat/tests/test_chat_agent_language.py`
- Test: `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
- Test: `mobile/flutter_app/test/confirmed_payload_test.dart`

- [x] Add activity context to Daily Coaching only after Task 4 confirmed data model is implemented.
- [x] Allow chatbot to reference recent Daily Coaching summary through `agent_memory`, not through raw logs.
- [x] Allow reminders to be suggested as proposed actions, but require user approval before enabling them.
- [x] Keep `debug_trace` empty by default.
- [x] Add tests that chat, reminder, and activity context do not leak raw sensitive text.
- [x] Run: `python -m pytest --no-cov backend\ai_agent_chat\tests`
  - Expected: AI Agent tests pass.
- [x] Run: `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py`
  - Expected: AI Agent API tests pass.
- [x] Run: `C:\src\flutter\bin\flutter.bat analyze`
  - Expected: `No issues found`.
- [x] Run: `C:\src\flutter\bin\flutter.bat test`
  - Expected: all Flutter tests pass.

---

## Start Log

- [x] 2026-05-21: Created this TODO plan before starting chatbot/alarm/exercise implementation.
- [x] 2026-05-21: Started Task 2 with `ChatbotAgent`, chat session dataclasses, and safety-focused unit tests.
- [x] 2026-05-21: Completed Task 2-5 implementation, learning notes, and verification for chatbot, reminders, activity context, and Daily Coaching reconnection.

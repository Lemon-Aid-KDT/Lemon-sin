# AI Agent Food and Supplement Completion Checklist

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the Lemon Aid local LLM/AI Agent path from confirmed supplement and food inputs through backend daily coaching, summary memory, and mobile app integration before merging the taedong UI.

**Architecture:** Deterministic backend services remain the source of truth for nutrition and supplement data. The local LLM served by SGLang is an explanation and coaching layer that consumes only confirmed user data and must not invent nutrient values or medical conclusions. The active mobile app remains `mobile/flutter_app` until this flow is verified; `origin/taedong-design` is a UI source to port later.

**Tech Stack:** FastAPI, PostgreSQL, Alembic, SGLang OpenAI-compatible endpoint, Flutter/Dio, Python contract tests.

---

## Current Recording Status

Yes, the work has been recorded, but it was split across several documents rather than one active checklist.

- [x] `docs/superpowers/plans/2026-05-20-taedong-mobile-integration.md` records the completed taedong bridge decision and mobile API-base/model compatibility work.
- [x] `docs/Nutrition-docs/dev-guides/26-operations-manual.md` records the SGLang/PostgreSQL/FastAPI smoke path.
- [x] `PROJECT_GUIDE.md` and `guide.html` record the current backend, AI Agent, SGLang, and mobile status.
- [x] `mobile/README.md` records the current Flutter app boundary and taedong-design integration boundary.
- [x] This file is now the active checklist for the remaining work toward the local LLM app goal.

## Current Verified Baseline

- [x] Active worktree: `ai-agent-backend-integration`
- [x] Active branch: `feat/ai-agent-backend-integration`
- [x] Latest pushed commit before this checklist: `de1a963 feat(mobile): add taedong integration bridge`
- [x] Worktree was clean before this checklist update.
- [x] Backend supports `agent_memory` and `agent_runs`.
- [x] Backend supports `LLM_PROVIDER=sglang` with local loopback restriction when external LLM access is disabled.
- [x] User verified local SGLang at `http://localhost:30000/v1/models`.
- [x] Backend live smoke previously verified PostgreSQL migration, FastAPI daily-coaching, local SGLang call, and `agent_memory` reinjection.
- [x] Mobile app has dashboard shell, AI daily coaching call, secure token storage, local base URL resolver, supplement image permission/picker, and `/api/v1/supplements/analyze` preview call.
- [x] `origin/taedong-design` was inspected as a UI/auth candidate, but direct merge is deferred because the current backend does not expose `/api/v1/auth/*`.

## Product Boundary

- [x] LLM is not the food recognizer.
- [x] LLM is not the nutrition calculator.
- [x] Food nutrient calculation and DB lookup are assumed to be provided later by the team's food model/algorithm.
- [x] For now, our food work captures photo/manual input, asks the user to confirm/edit, and passes only confirmed food records into the Agent.
- [x] Unconfirmed OCR/model previews must not update `agent_memory` or final run logs.
- [x] Confirmed supplements and confirmed foods may update memory summaries.
- [x] taedong UI merge happens after the active backend/mobile/Agent flow is stable.

---

## Task 1: Finish Supplement Confirm and Save Flow

**Files:**
- Modify: `mobile/flutter_app/lib/features/supplement/data/supplement_capture_repository.dart`
- Modify: `mobile/flutter_app/lib/features/supplement/domain/supplement_analysis_preview.dart`
- Modify: `mobile/flutter_app/lib/features/supplement/presentation/supplement_capture_screen.dart`
- Modify: `backend/Nutrition-backend/tests/unit/mobile/test_flutter_ai_agent_contract.py`
- Update docs: `mobile/README.md`

- [x] Show the `/api/v1/supplements/analyze` preview on screen with editable product name, manufacturer, ingredients, serving, and intake schedule fields.
- [x] Add a repository method that posts a confirmed payload to `POST /api/v1/supplements`.
- [x] Ensure the confirmed payload always includes `user_confirmed: true`.
- [x] Preserve the backend `analysis_id` when a preview is confirmed.
- [x] Block saving when the user has not confirmed the values.
- [x] Request sensitive-health analysis consent before confirmed supplement storage.
- [x] Keep warnings visible as caution text, not diagnosis/treatment text.
- [x] Add static contract tests that assert the mobile app calls both `/api/v1/supplements/analyze` and `/api/v1/supplements`.
- [x] Add static contract tests that assert `user_confirmed` is required in the mobile save path.
- [x] Run `python -m pytest backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py -q --no-cov`.

## Task 2: Add Food Confirmed Input Flow Without Building the Food Model

**Files:**
- Create: `mobile/flutter_app/lib/features/food/domain/confirmed_food_entry.dart`
- Create: `mobile/flutter_app/lib/features/food/presentation/food_capture_screen.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/domain/ai_coaching_models.dart`
- Modify: `mobile/flutter_app/lib/app.dart` or current router file
- Modify: `backend/Nutrition-backend/tests/unit/mobile/test_flutter_ai_agent_contract.py`
- Update docs: `mobile/README.md`

- [x] Add a food capture/input screen that supports photo selection plus manual fields for food name, meal type, serving label, and optional memo.
- [x] Do not implement food image recognition.
- [x] Do not implement nutrition DB lookup.
- [x] Do not invent nutrients in the mobile app.
- [x] Build a confirmed food payload with `source_type: food_user_input` or a similarly explicit source marker.
- [x] Include `user_confirmed: true` only after the user confirms the food entry.
- [x] Allow `nutrients` to be empty or absent until the team's food algorithm supplies values.
- [x] Add static contract tests that assert the food flow avoids hard-coded nutrient guesses.
- [x] Add static contract tests that assert unconfirmed food input is not sent as final Agent payload.
- [x] Run `python -m pytest backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py -q --no-cov`.

## Task 3: Connect Confirmed Food and Supplement Data to Daily Coaching

**Files:**
- Modify: `mobile/flutter_app/lib/features/ai_coaching/domain/ai_coaching_models.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/data/ai_coaching_repository.dart`
- Modify: `mobile/flutter_app/lib/features/ai_coaching/presentation/ai_coaching_screen.dart`
- Modify: `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py` only if backend contract coverage needs expansion
- Update docs: `PROJECT_GUIDE.md`, `guide.html`, `mobile/README.md`

- [x] Replace the current fixed sample payload with a payload assembled from confirmed food and supplement entries.
- [x] Keep demo/sample data only behind an explicit sample action or test fixture.
- [x] Send confirmed food entries under `payload.foods`.
- [x] Send confirmed supplement entries under `payload.supplements`.
- [x] Keep missing nutrient values explicit rather than filling guessed values.
- [x] Connect confirmed food and supplement entries through `ConfirmedEntryStore` for daily coaching screen handoff.
- [x] Confirm that backend daily-coaching can still return provider, used tools, findings, safety warnings, and memory usage.
- [x] Run the targeted AI Agent API tests.
- [x] If `PROJECT_GUIDE.md` changes, update `guide.html` through the sync script when available; if unavailable, record the manual mirror reason in the final report.

## Task 4: Verify Memory and Safety Boundaries

**Files:**
- Inspect: `backend/Nutrition-backend/src/services/agent_memory.py`
- Inspect or modify: `backend/Nutrition-backend/tests/unit/services/test_agent_memory.py`
- Inspect or modify: `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`

- [x] Verify confirmed supplements can update supplement memory.
- [x] Verify confirmed foods can contribute to food-pattern memory only after confirmation.
- [x] Verify unconfirmed OCR preview data does not update memory.
- [x] Verify run logs avoid storing raw unconfirmed image/OCR payloads.
- [x] Verify generated coaching language stays bounded: information and caution only, no diagnosis, treatment, or prescription claims.
- [x] Run relevant unit and integration tests for memory and AI Agent routes.

## Task 5: Run Real Local Stack Smoke Again

**Files/Commands:**
- Use: `docs/Nutrition-docs/dev-guides/26-operations-manual.md`
- Use: `backend/scripts/smoke_ai_agent_server.py`

- [x] Confirm SGLang is reachable at `http://localhost:30000/v1/models`.
- [x] Run the backend smoke against PostgreSQL + FastAPI + SGLang.
- [x] Verify the smoke proves both initial daily-coaching and second-call `agent_memory` reinjection.
- [x] Record the latest smoke result in this checklist or the operations manual.

Latest smoke result:

```json
{
  "status": "ok",
  "server_url": "http://127.0.0.1:18080",
  "sglang_base_url": "http://localhost:30000/v1",
  "model": "Qwen/Qwen2.5-0.5B-Instruct",
  "first_provider": "sglang",
  "second_provider": "sglang",
  "second_used_tools": [
    "daily_health_agent",
    "nutrition_engine",
    "supplement_engine",
    "safety_guard",
    "chat_agent",
    "agent_memory"
  ]
}
```

## Task 6: Defer and Then Port taedong UI

**Files:**
- Reference only until Task 1-5 pass: `origin/taedong-design:mobile/**`
- Active app until then: `mobile/flutter_app/**`

- [x] Keep `mobile/flutter_app` as the canonical working app until confirmed food, confirmed supplement, daily coaching, and memory smoke pass.
- [x] After verification, decide whether to port taedong screens into `mobile/flutter_app` or replace the canonical app with taedong root `mobile/`.
- [x] Resolve auth mismatch before using taedong auth screens because current backend lacks `/api/v1/auth/*`.
- [x] Preserve the working API clients and payload rules when porting UI.
- [x] Run Flutter analyze/test if Flutter CLI is available.

Task 6 decision:

- Keep `mobile/flutter_app` as the current canonical app for this branch.
- Defer taedong root `mobile/` porting until the backend exposes compatible auth routes or the app auth contract is revised.
- Do not merge or checkout `taedong-design` in this worktree.
- Flutter/Dart SDK became available at `C:\src\flutter\bin`.
- `flutter analyze` passed with `No issues found`.
- `flutter test` passed after adding `mobile/flutter_app/test/confirmed_payload_test.dart`.

---

## Next Immediate Action

The checklist implementation is complete. Next operational step is review/commit/push, then a separate taedong UI porting task after backend auth compatibility is decided.

## Working Notes

- Use `mobile/flutter_app` for current implementation.
- Do not merge or checkout `taedong-design` during these tasks.
- Do not implement the food recognition model or nutrient DB algorithm.
- Do not require an external API key for local SGLang; the local endpoint can run without one unless a client library requires a placeholder.
- Keep `ALLOW_EXTERNAL_LLM=false` compatible with local/self-hosted SGLang only.

# Dev Guides Master Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Lemon Healthcare "건강의신 AI 모델" from `docs/dev-guides/00` through `29` in dependency order, with testable backend, mobile, demo, and handover deliverables.

**Architecture:** The backend owns all algorithms, nutrition evaluation, OCR/LLM adapters, persistence, and REST APIs. The Flutter app is a client for consent, capture, health-data sync, and result visualization only. Data standards and compliance wording are treated as first-class inputs, with demo/operations/handover artifacts produced after the core system is working.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, mypy strict, Ruff, Black, PostgreSQL/Alembic, Redis, Google Cloud Vision, Naver CLOVA OCR, Claude/OpenAI adapters, Flutter, Riverpod, Dio, Retrofit, Freezed, go_router, HealthKit/Health Connect.

---

## Scope Summary

Read source prompts:

- `00`: backend environment and FastAPI skeleton.
- `01`-`04`: BMI, activity v1-v4, BMR/TDEE, 7-step weight prediction.
- `05`-`06`: KDRIs lookup, unit conversion, nutrient status evaluation.
- `07`-`09`: OCR adapter, LLM supplement parsing, supplement registration API.
- `10`-`13`: Flutter setup, camera/gallery, health data integration, dashboard outputs.
- `14`-`17`: Hall dynamic weight model, goal-based analysis, meal recognition, feedback and push notifications.
- `18`-`21`: remaining mobile screens and feedback/pull-to-refresh/notification UI.
- `22`-`29`: demo scenarios, presentation, rehearsal, handover, operations, incident runbooks, retrospective, final delivery package.

Observed repository state on 2026-05-11:

- `backend/` has a completed `00`-style skeleton as of 2026-05-11: `pyproject.toml`, requirements files, `src/main.py`, `src/config.py`, `src/utils/logger.py`, package directories, and test directories.
- `mobile/` currently contains only `CLAUDE.md`; Flutter app scaffold is not yet present.
- `data/` currently contains only `CLAUDE.md`; KDRIs/MFDS/RDA data files are not yet present.
- Git status could not be checked because Git marked `C:/Lemon-Aid/Lemon-sin` as a dubious ownership repository. Resolve separately before committing.

## Planning Decision

The 30 prompts cover multiple independent subsystems. Do not attempt to execute all prompts as one giant coding task. Use this as the master roadmap, then create or execute smaller implementation plans per subsystem:

1. Backend core algorithms.
2. Nutrition standards and nutrient evaluation.
3. OCR/LLM ingestion and supplement API.
4. Flutter mobile MVP.
5. Advanced analysis and feedback.
6. Demo, operations, and handover artifacts.

## Global Rules

- Preserve root `CLAUDE.md`, `backend/CLAUDE.md`, `mobile/CLAUDE.md`, and `data/CLAUDE.md` constraints.
- Backend functions require full type hints, Google-style docstrings, and accompanying tests.
- Use Pydantic v2 for schemas and adapter interfaces for external APIs.
- Avoid medical claims in names, text, docstrings, prompts, logs, and UI. Prefer `analysis`, `evaluation`, `status`, `recommendation`, and `support` wording.
- Mobile must not implement business algorithms; it calls backend APIs.
- Keep Phase 6 artifacts under `docs/deliverables/` instead of adding new root folders, unless the user explicitly approves a different layout.
- Treat API keys, credentials, real health data, and service-account files as non-committable secrets.

## Structural Decisions Locked 2026-05-11

- **Prediction package:** use `backend/src/prediction/` as a dedicated package for 7-step prediction, Hall dynamic model, body composition, and model selection. Do not use `backend/src/algorithms/prediction.py`.
- **Service layer:** allow `backend/src/services/` for cross-domain orchestration such as supplement registration. Routers stay thin; domain modules keep pure logic.
- **Compliance naming:** internal modules may keep guide-compatible names such as `diagnosis.py` and `test_diagnosis.py`, but external API paths, response fields, UI labels, prompts, and logs must use safer wording such as `evaluation`, `analysis`, `status`, and `nutritionStatus`.
- **Deliverable layout:** map Phase 6 guide folders into `docs/deliverables/`:
  - `docs/deliverables/demo/`
  - `docs/deliverables/presentation/`
  - `docs/deliverables/handover/`
  - `docs/deliverables/operations/`
  - `docs/deliverables/incidents/`
  - `docs/deliverables/retrospective/`
  - `docs/deliverables/final/`
- **Coverage gate:** `--cov-fail-under=80` was removed during Phase 0 because pytest fails in a zero-test skeleton. Re-enable it in `backend/pyproject.toml` during Phase 1 as soon as the first meaningful algorithm tests exist.
- **Parallel work:** Phase 4 Flutter scaffolding can run in parallel with Phase 3 OCR/LLM adapter work because it can use mocked API contracts. Coordinate shared request/response schemas before parallel implementation starts.

## Phase 0: Baseline And Gap Audit - Completed 2026-05-11

**Files:**
- Created/Verified: `backend/pyproject.toml`
- Created/Verified: `backend/requirements.txt`
- Created/Verified: `backend/requirements-dev.txt`
- Created/Verified: `backend/src/main.py`
- Created/Verified: `backend/src/config.py`
- Created/Verified: `backend/src/utils/logger.py`
- Created/Verified: `backend/tests/conftest.py`
- Inspect: `mobile/CLAUDE.md`
- Inspect: `data/CLAUDE.md`

- [x] Backend skeleton created from `docs/dev-guides/00-setup-environment.md`.
- [x] `--cov-fail-under=80` temporarily removed so zero-test skeleton can run.
- [ ] Re-enable `--cov-fail-under=80` during Phase 1 after adding algorithm tests.
- [ ] Resolve Git safe-directory issue before the first implementation commit:

```powershell
git config --global --add safe.directory C:/Lemon-Aid/Lemon-sin
```

Expected gate: completed. Remaining Phase 0 carryover is Git safe-directory setup and restoring the coverage gate after Phase 1 tests are introduced.

## Phase 1: Backend Core Algorithms

**Prompts:** `01`, `02`, `03`, `04`

**Files:**
- Create: `backend/src/models/schemas/algorithm.py`
- Create: `backend/src/models/schemas/user.py`
- Create: `backend/src/models/schemas/prediction.py`
- Create: `backend/src/algorithms/bmi.py`
- Create: `backend/src/algorithms/activity.py`
- Create: `backend/src/algorithms/metabolism.py`
- Create: `backend/src/prediction/__init__.py`
- Create: `backend/src/prediction/weight.py`
- Create: `backend/tests/unit/algorithms/test_bmi.py`
- Create: `backend/tests/unit/algorithms/test_activity_v1.py`
- Create: `backend/tests/unit/algorithms/test_activity_v2.py`
- Create: `backend/tests/unit/algorithms/test_activity_v3.py`
- Create: `backend/tests/unit/algorithms/test_activity_v4.py`
- Create: `backend/tests/unit/algorithms/test_metabolism.py`
- Create: `backend/tests/unit/prediction/test_weight.py`
- Modify: `backend/tests/conftest.py`

- [ ] Implement BMI classification and v1 activity score with tests from `01`.
- [ ] Implement v2 heart-rate factor, v3 percentile bonus, and v4 chronic-condition multiplier with tests from `02`.
- [ ] Implement BMR and TDEE using Mifflin-St Jeor and step-based activity factors with tests from `03`.
- [ ] Implement 7-step weight prediction for single and standard periods with tests from `04`.
- [ ] Re-enable `--cov-fail-under=80` in `backend/pyproject.toml` once the first algorithm test file passes.
- [ ] Run focused tests after each prompt:

```powershell
pytest tests/unit/algorithms tests/unit/prediction -v
```

- [ ] Run backend quality gate:

```powershell
black src tests --check
ruff check src tests
mypy src --strict
pytest
```

Expected gate: guide examples pass, including 50대 여성 BMI/activity examples, v4 score around 87.2, BMR/TDEE examples, and 30-day/60-day weight predictions.

## Phase 2: Nutrition Standards And Status Evaluation

**Prompts:** `05`, `06`

**Files:**
- Create/Modify: `backend/src/models/schemas/nutrition.py`
- Create: `backend/src/nutrition/kdris.py`
- Create: `backend/src/nutrition/unit_converter.py`
- Create: `backend/src/nutrition/diagnosis.py`
- Create: `data/kdris/kdris_2020.csv`
- Create: `data/kdris/kdris_metadata.json`
- Create: `data/reference/nutrient_codes.json`
- Create: `data/mfds/unit_conversions.json`
- Create: `backend/tests/unit/nutrition/test_kdris.py`
- Create: `backend/tests/unit/nutrition/test_unit_converter.py`
- Create: `backend/tests/unit/nutrition/test_diagnosis.py`
- Create: `backend/tests/integration/nutrition/test_diagnosis_integration.py`

- [ ] Digitize or seed the minimum KDRIs rows needed for the guide examples.
- [ ] Implement user-context matching for age, sex, pregnancy, and lactation.
- [ ] Implement unit conversion for mg, ug, and IU for vitamins A, D, and E.
- [ ] Implement nutrient intake aggregation and status classification.
- [ ] Keep internal guide-compatible module names, but expose public API paths and fields with `evaluation`/`analysis`/`status` wording.
- [ ] Run:

```powershell
pytest tests/unit/nutrition tests/integration/nutrition -v
mypy src/nutrition src/models --strict
```

Expected gate: KDRIs lookup, unit conversion, and nutrient status scenarios pass, including pregnancy/lactation and upper-limit risk cases.

## Phase 3: OCR, LLM, And Supplement Registration API

**Prompts:** `07`, `08`, `09`

**Files:**
- Create: `backend/src/ocr/exceptions.py`
- Create: `backend/src/ocr/base.py`
- Create: `backend/src/ocr/preprocessor.py`
- Create: `backend/src/ocr/google_vision.py`
- Create: `backend/src/ocr/clova.py`
- Create: `backend/src/cache/ocr_cache.py`
- Create: `backend/src/ocr/pipeline.py`
- Create: `backend/src/llm/exceptions.py`
- Create: `backend/src/llm/schemas.py`
- Create: `backend/src/llm/prompts.py`
- Create: `backend/src/llm/base.py`
- Create: `backend/src/llm/claude.py`
- Create: `backend/src/llm/openai.py`
- Create: `backend/src/nutrition/mfds_matcher.py`
- Create: `backend/src/models/schemas/supplement.py`
- Create: `backend/src/models/db/supplement.py`
- Create: `backend/src/db/session.py`
- Create: `backend/src/api/deps.py`
- Create: `backend/src/services/supplement_service.py`
- Create: `backend/src/api/v1/supplements.py`
- Modify: `backend/src/main.py`

- [ ] Implement OCR adapter interfaces and mocked unit tests before real API tests.
- [ ] Implement LLM adapter interfaces and structured parsing schemas before prompt tuning.
- [ ] Implement MFDS matching with a small checked-in seed dataset.
- [ ] Implement supplement service orchestration: OCR -> LLM parse -> MFDS match -> nutrient status evaluation.
- [ ] Add FastAPI route and Swagger-visible schemas.
- [ ] Add integration tests with adapters mocked and optional real API tests skipped when credentials are absent.
- [ ] Publish mocked request/response schemas for the mobile team before or during Flutter scaffolding.
- [ ] Run:

```powershell
pytest tests/unit/ocr tests/unit/llm tests/unit/api tests/integration/api -v
mypy src --strict
```

Expected gate: multipart supplement upload can be tested without real external API credentials, and real API tests are opt-in.

## Phase 4: Flutter Mobile MVP

**Prompts:** `10`, `11`, `12`, `13`

**Parallelization:** This phase can start once the Phase 3 API contracts are drafted, even before OCR/LLM real integrations are complete. Use mocked repository responses until backend routes are ready.

**Files:**
- Create: `mobile/pubspec.yaml`
- Create: `mobile/analysis_options.yaml`
- Create: `mobile/.env.example`
- Create: `mobile/README.md`
- Create: `mobile/lib/main.dart`
- Create: `mobile/lib/app.dart`
- Create: `mobile/lib/core/**`
- Create: `mobile/lib/shared/widgets/disclaimer.dart`
- Create: `mobile/lib/features/home/**`
- Create: `mobile/lib/features/supplement/**`
- Create: `mobile/lib/features/health/**`
- Create: `mobile/lib/features/nutrition/**`
- Create: `mobile/lib/features/prediction/**`
- Create: `mobile/lib/features/activity/**`
- Modify: `mobile/ios/Runner/Info.plist`
- Modify: `mobile/android/app/src/main/AndroidManifest.xml`

- [ ] Scaffold Flutter app using the exact structure and dependencies from `mobile/CLAUDE.md`.
- [ ] Add routing, theme, API client, storage, and reusable loading/error/disclaimer widgets.
- [ ] Implement camera/gallery capture and supplement upload UI.
- [ ] Implement HealthKit/Health Connect permission, consent, sync, and manual fallback.
- [ ] Implement dashboard screens for recommended intake, weight prediction, and activity recommendation.
- [ ] Add widget/provider/golden tests where the prompt requires them.
- [ ] Run:

```powershell
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter analyze
flutter test
```

Expected gate: mobile can navigate through home -> supplement capture -> dashboard using mocked API data.

## Phase 5: Advanced Analysis, Meals, Feedback, And Remaining Mobile Screens

**Prompts:** `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`

**Files:**
- Create: `backend/src/prediction/body_composition.py`
- Create: `backend/src/prediction/hall.py`
- Create: `backend/src/prediction/selector.py`
- Create: `backend/src/nutrition/goal_definitions.py`
- Create: `backend/src/nutrition/goal_analysis.py`
- Create: `data/reference/health_goals.json`
- Create: `backend/src/meal/**`
- Create: `backend/src/nutrition/rda_matcher.py`
- Create: `data/rda/korean_foods.csv`
- Create: `backend/src/feedback/**`
- Create: `backend/src/notifications/**`
- Create: `backend/src/api/v1/feedback.py`
- Create: `mobile/lib/features/goal_analysis/**`
- Create: `mobile/lib/features/meal/**`
- Create: `mobile/lib/features/feedback/**`
- Create: `mobile/lib/core/notifications/**`

- [ ] Implement Hall model and selector after 7-step tests are already stable.
- [ ] Implement goal definitions and goal analysis with compliance tests for wording.
- [ ] Implement meal text parsing first; add image recognition only after text flow works.
- [ ] Implement backend feedback and notification services with adapter-style FCM/APNs dispatch.
- [ ] Implement mobile deficient nutrient, goal analysis, meal input, review, feedback, pull-to-refresh, and notification-token flows.
- [ ] Run backend and mobile full quality gates.

Expected gate: all five outputs are visible on mobile, and registration/meal/feedback flows can be demoed with stable mocked or seeded data.

## Phase 6: Demo, Presentation, Handover, Operations, And Final Package

**Prompts:** `22`, `23`, `24`, `25`, `26`, `27`, `28`, `29`

**Deliverable folders:**
- `docs/deliverables/demo/`
- `docs/deliverables/presentation/`
- `docs/deliverables/handover/`
- `docs/deliverables/operations/`
- `docs/deliverables/incidents/`
- `docs/deliverables/retrospective/`
- `docs/deliverables/final/`

- [ ] Create persona A/B demo scenarios and seed data.
- [ ] Create pre-demo checklist, live demo script, and backup-video placeholders or generated assets.
- [ ] Build presentation deck and PDF backup.
- [ ] Create rehearsal plan, Q&A scripts, and troubleshooting runbooks.
- [ ] Create handover docs, operations manual, incident runbooks, retrospective, final catalog, verification checklist, and completion declaration.
- [ ] Run final gate review against `docs/dev-guides/29-final-deliverables-index.md`.

Expected gate: final package is complete enough for an owner handoff and demo-day run-through.

## Critical Path

1. Confirm Phase 0 skeleton remains green after the coverage-gate adjustment.
2. Resolve Git safe-directory before the first implementation commit.
3. Implement backend algorithm tests and functions.
4. Restore `--cov-fail-under=80`.
5. Prepare KDRIs/MFDS data.
6. Draft API contracts for supplement registration and dashboard outputs.
7. Implement OCR/LLM adapters behind mocks.
8. Scaffold Flutter app in parallel against mocked API contracts.
9. Build supplement registration API.
10. Integrate health data, dashboard, and remaining five outputs.
11. Prepare demo and handover package under `docs/deliverables/`.

## Major Risks

- External API credentials can block OCR/LLM validation. Mitigation: mocks first, real tests skipped unless credentials exist.
- KDRIs/MFDS/RDA source data can delay nutrition features. Mitigation: minimal seed fixtures first, full datasets later.
- Compliance wording can create rework. Mitigation: automated forbidden-term scan and `docs/10-compliance-checklist.md` review per feature.
- Structure drift can create import churn. Mitigation: update `backend/CLAUDE.md` before Phase 1 to endorse `src/prediction/` and `src/services/`.
- Flutter native permissions can consume time. Mitigation: build platform permission scaffolding before visual polish.
- Git safe-directory issue blocks status/commit workflow. Mitigation: resolve before implementation commits.

## Immediate Next Plan

- [x] Mark Phase 0 as completed and capture its carryovers.
- [x] Update `backend/CLAUDE.md` to reflect `src/prediction/` and `src/services/`.
- [x] Update root `CLAUDE.md` to place Phase 6 artifacts under `docs/deliverables/`.
- [ ] Execute Phase 1 prompt `01-bmi-and-v1-algorithm.md` with TDD.
- [ ] Keep each dev-guide prompt as its own small implementation slice and commit after its tests pass.

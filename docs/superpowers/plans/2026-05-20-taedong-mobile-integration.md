# Taedong Mobile Integration Plan

> **For:** KDS13  
> **Feature:** taedong-design mobile frontend bridge  
> **Date:** 2026-05-20  
> **Status:** Bridge complete; first taedong UI shell elements selectively ported

## Goal

Use `origin/taedong-design` as the mobile UI reference without directly merging its large `mobile/` tree into `feat/ai-agent-backend-integration`. Preserve the currently verified backend/SGLang work and add only the frontend bridge pieces that help the current Flutter app connect to the real backend.

## Constraints

- Do not checkout, reset, or merge `taedong-design` in this worktree.
- Keep `mobile/flutter_app` as the active app path for this increment.
- Treat backend OpenAPI/runtime behavior as the source of truth for endpoints.
- Do not wire taedong auth screens yet because the current backend does not expose `/api/v1/auth/*`.
- Keep medical and nutrition UI language bounded by the existing disclaimer.

## Completed Bridge Tasks

- [x] Confirm current branch and clean worktree before editing.
- [x] Add a mobile-safe API base URL resolver so Android emulator defaults to `10.0.2.2` while desktop/web keep localhost-style defaults.
- [x] Add taedong-compatible loose response models that preserve raw backend payloads for future UI migration.
- [x] Extend static contract tests to lock the bridge behavior.
- [x] Update mobile/project documentation with the taedong-design integration boundary.
- [x] Run targeted mobile contract tests and broader backend verification where feasible.
- [x] Commit and push the resulting narrow integration increment.
- [x] Re-check latest `origin/taedong-design` commit `7d1dfa8` and confirm it should not be merged wholesale.
- [x] Restore `mobile/flutter_app` to a clean Flutter analyze/test state after partial UI edits.
- [x] Add a taedong-inspired bottom shell for the active home/coaching routes while keeping capture flows full-screen.
- [x] Apply Lemon theme cards/pills to dashboard, food capture, supplement capture, coaching result, and disclaimer screens.
- [x] Add a taedong-inspired capture frame card for food/supplement camera or gallery selection.
- [x] Add an entry-result screen after confirmed food/supplement save so the analysis-result UX can grow without replacing backend contracts.
- [x] Add a debug-only sample confirmed input button so photo-free LLM coaching can be exercised while upstream recognition models are assumed.
- [x] Add a local dev stack script that starts PostgreSQL/FastAPI with Flutter web CORS allowed for `localhost:52100`.

## Current Decision

Keep `mobile/flutter_app` as the canonical app for the current AI Agent branch. The taedong root `mobile/` app remains a UI/auth reference, not the active code path, until the backend exposes compatible auth routes or the app auth contract is revised.

The current safe UI merge path is selective porting:

- port reusable visual ideas into `mobile/flutter_app/shared`;
- preserve the existing API client, confirmed food/supplement payload contracts, and `ConfirmedEntryStore` handoff;
- defer taedong auth/OAuth/router migration until backend auth routes are compatible;
- do not import taedong mock chat behavior over the live AI Agent coaching flow.
- keep dev sample seeding behind `kDebugMode` and exclude invented food nutrients/raw OCR from the sample payload.

## Follow-Up Boundary

The next larger decision is whether the canonical Flutter app path should become taedong's root `mobile/` app or remain `mobile/flutter_app` temporarily. That should be handled as a separate migration because direct merge would replace or conflict with many app files and docs. The first camera/analysis-result layer is now present in `mobile/flutter_app`; the next safe UI step is to expand the result screen with backend result details rather than importing taedong mock data.

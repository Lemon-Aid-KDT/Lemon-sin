# Taedong Mobile Integration Plan

> **For:** KDS13  
> **Feature:** taedong-design mobile frontend bridge  
> **Date:** 2026-05-20  
> **Status:** Executing

## Goal

Use `origin/taedong-design` as the mobile UI reference without directly merging its large `mobile/` tree into `feat/ai-agent-backend-integration`. Preserve the currently verified backend/SGLang work and add only the frontend bridge pieces that help the current Flutter app connect to the real backend.

## Constraints

- Do not checkout, reset, or merge `taedong-design` in this worktree.
- Keep `mobile/flutter_app` as the active app path for this increment.
- Treat backend OpenAPI/runtime behavior as the source of truth for endpoints.
- Do not wire taedong auth screens yet because the current backend does not expose `/api/v1/auth/*`.
- Keep medical and nutrition UI language bounded by the existing disclaimer.

## Task List

1. Confirm current branch and clean worktree before editing.
2. Add a mobile-safe API base URL resolver so Android emulator defaults to `10.0.2.2` while desktop/web keep localhost-style defaults.
3. Add taedong-compatible loose response models that preserve raw backend payloads for future UI migration.
4. Extend static contract tests to lock the bridge behavior.
5. Update mobile/project documentation with the taedong-design integration boundary.
6. Run targeted mobile contract tests and broader backend verification where feasible.
7. Commit and push the resulting narrow integration increment.

## Follow-Up Boundary

The next larger decision is whether the canonical Flutter app path should become taedong's root `mobile/` app or remain `mobile/flutter_app` temporarily. That should be handled as a separate migration because direct merge would replace or conflict with many app files and docs.

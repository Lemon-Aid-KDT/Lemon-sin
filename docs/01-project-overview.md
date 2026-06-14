# 01. Project Overview

> Status: team-wide summary
> Detailed source: [Nutrition-docs/01-project-overview.md](./Nutrition-docs/01-project-overview.md)

## One-Line Summary

Lemon Aid is an AI healthcare project that combines supplement-label analysis, food-image analysis, health activity data, and AI chat support into a unified health-management experience.

## Team Scope

| Area | Working Folder | Responsibility |
|------|----------------|----------------|
| Nutrition | `docs/Nutrition-docs/`, `backend/Nutrition-backend/`, `data/supplement_images/`, `data/nutrition_reference/` | supplement image intake, OCR/text parsing, nutrient analysis, KDRIs lookup, weight/activity/nutrition logic |
| Food | `docs/Food-docs/`, `backend/food_image_analysis/`, `data/food_images/` | food image classification, cuisine/category taxonomy, meal metadata |
| Chat | `docs/Chat-docs/`, `backend/ai_agent_chat/` | AI agent chat flow, safe user guidance, context orchestration |
| Integration | `docs/Integration-docs/`, `.github/`, root README/handoff files | CI, PR, release, demo, cross-part integration |

## Common Product Boundary

- The product is positioned as non-diagnostic health-management support, not medical diagnosis, prescription, or treatment.
- Nutrition, food, and chat outputs must converge into one user-facing experience instead of separate demos.
- Sensitive health data and image-derived data must follow consent, retention, and external-processing gates.
- Implementation status must be checked against runtime code and tests, not planning documents alone.

## Current Source Of Truth

- Collaboration and PR rules: [05-github-guidelines.md](./05-github-guidelines.md)
- Common product intent: [03-project-intent.md](./03-project-intent.md)
- Common technical map: [06-tech-stack.md](./06-tech-stack.md)
- Common compliance guardrails: [10-compliance-checklist.md](./10-compliance-checklist.md)
- Nutrition detailed design: [Nutrition-docs/](./Nutrition-docs/)
- Integration operations: [Integration-docs/01-ci-pr-integration-operations.md](./Integration-docs/01-ci-pr-integration-operations.md)

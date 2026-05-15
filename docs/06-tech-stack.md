# 06. Tech Stack

> Status: team-wide summary
> Detailed source: [Nutrition-docs/06-tech-stack.md](./Nutrition-docs/06-tech-stack.md)

## Common Architecture

```text
mobile/
  flutter_app/ or Xcode/iOS-specific implementation

backend/
  Nutrition-backend/
  food_image_analysis/
  ai_agent_chat/
  scripts/
  alembic/

data/
  nutrition_reference/
  supplement_images/
  food_images/

docs/
  common summary docs
  Nutrition-docs/
  Food-docs/
  Chat-docs/
  Integration-docs/
```

## Shared Stack Principles

- Backend feature areas use Python/FastAPI-compatible module layouts with their own `src/` and `tests/`.
- Mobile work may use Flutter and Xcode/iOS-specific assets, but product behavior must remain aligned with backend contracts.
- OCR, LLM, vision, and external APIs must be adapter-driven and gated by settings, consent, and environment policy.
- Local/private processing is preferred for identifiable or sensitive health data.
- CI must validate formatting, lint, type checks, tests, and data gates before integration.

## Current Backend Execution Surface

| Area | Runtime Path | Test Path |
|------|--------------|-----------|
| Nutrition | `backend/Nutrition-backend/src` | `backend/Nutrition-backend/tests` |
| Food | `backend/food_image_analysis/src` | `backend/food_image_analysis/tests` |
| Chat | `backend/ai_agent_chat/src` | `backend/ai_agent_chat/tests` |
| Shared DB/scripts | `backend/alembic`, `backend/scripts` | covered by backend CI |

## Required Local Checks

Run from `yeong-Lemon-Aid/backend`:

```bash
.venv/bin/python -m black --check Nutrition-backend/src Nutrition-backend/tests food_image_analysis/src food_image_analysis/tests ai_agent_chat/src ai_agent_chat/tests alembic scripts
.venv/bin/python -m ruff check Nutrition-backend/src Nutrition-backend/tests food_image_analysis/src food_image_analysis/tests ai_agent_chat/src ai_agent_chat/tests alembic scripts
.venv/bin/python -m mypy --explicit-package-bases Nutrition-backend/src Nutrition-backend/tests food_image_analysis/src food_image_analysis/tests ai_agent_chat/src ai_agent_chat/tests --strict
.venv/bin/python -m pytest -q --no-cov
```

## Related Documents

- GitHub and CI rules: [05-github-guidelines.md](./05-github-guidelines.md)
- Integration operations: [Integration-docs/01-ci-pr-integration-operations.md](./Integration-docs/01-ci-pr-integration-operations.md)
- Nutrition detailed architecture: [Nutrition-docs/06-tech-stack.md](./Nutrition-docs/06-tech-stack.md)

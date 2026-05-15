# Backend Structure

This backend is organized for team-owned feature areas while preserving a working integration surface.

## Current Layout

- `Nutrition-backend/`: active Nutrition runtime, including supplement analysis, OCR/LLM adapters, nutrition logic, and tests.
- `food_image_analysis/`: food image analysis package skeleton.
- `ai_agent_chat/`: AI agent chat package skeleton.
- `scripts/`: active validation and operation scripts.
- `alembic/`: current shared database migration history.
- `pyproject.toml`: shared backend lint, type-check, test, and coverage settings.

## Rule

Keep each feature area's runtime, tests, and ownership notes inside its team folder. Shared assets such as `scripts/`, `alembic/`, and `pyproject.toml` remain at the backend root until they need to split by service.

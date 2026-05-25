# Docs Structure

This directory keeps team-wide documentation separate from each member or feature-area document set.

## Current Layout

- `01-project-overview.md`: common project summary for the whole team.
- `03-project-intent.md`: common product intent and positioning summary.
- `05-github-guidelines.md`: common GitHub collaboration rules for the whole team.
- `06-tech-stack.md`: common architecture and validation summary.
- `10-compliance-checklist.md`: common compliance guardrails.
- `Nutrition-docs/`: detailed Nutrition and supplement-analysis documents maintained by the Nutrition part. See `Nutrition-docs/43-ocr-3-tier-fixture-evaluation-report-plan.md` for the current OCR fixture evaluation gate.
- `Food-docs/`: reserved for food image analysis documents.
- `Chat-docs/`: AI agent chat documents. The current runtime implementation also lives in `backend/ai_agent_chat/` and is exposed through `backend/Nutrition-backend/src/api/v1/ai_agent.py`.
- `Integration-docs/`: reserved for final integration, deployment, and demo documents.
- `superpowers/plans/2026-05-22-mvp-runtime-and-medical-knowledge-todo.md`: current FastAPI + Flutter web + AI Agent smoke checklist and medical knowledge boundary TODO.
- `Nutrition-docs/dev-guides/31-medical-knowledge-layer.md`: medical knowledge layer design for keeping chronic-condition facts outside model fine-tuning and behind reviewed source records.

## Rule

Keep detailed feature work inside the matching part folder. Keep only team-wide summaries, collaboration rules, and cross-part operating guides in this root directory.

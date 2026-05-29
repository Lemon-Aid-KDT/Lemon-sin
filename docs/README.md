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
- `Integration-docs/02-ai-agent-worktree-integration-plan.md`: AI Agent worktree 기준축, PR 분리, 보안 preflight, safety/privacy gate.
- `Integration-docs/03-ai-agent-safety-porting-contract.md`: AI Agent, backend, DB, UI, RAG 선별 이식용 표준 응답/저장/안전 계약.
- `Integration-docs/04-medical-source-db-contract.md`: 의료정보 DB의 source, claim, review, boundary, RAG 연결 기준과 DB 담당자 TODO.
- `Integration-docs/05-grounded-chatbot-prd.md`: 검수 지식 기반 동적 답변 카드 챗봇의 제품 요구사항.
- `Integration-docs/06-grounded-chatbot-tdd.md`: PRD를 구현하기 위한 Technical Design Document.
- `Integration-docs/07-grounded-chatbot-todo.md`: TDD 기반 단계별 구현 TODO와 검증 게이트.
- `Integration-docs/08-grounded-chatbot-trd.md`: PRD 기반 기술 요구사항 명세.
- `Integration-docs/09-grounded-chatbot-implementation-log.md`: PRD/TRD/TDD/TODO 기반 챗봇 구현 결과와 검증 로그.
- `superpowers/plans/2026-05-22-mvp-runtime-and-medical-knowledge-todo.md`: current FastAPI + Flutter web + AI Agent smoke checklist and medical knowledge boundary TODO.
- `Nutrition-docs/dev-guides/31-medical-knowledge-layer.md`: medical knowledge layer design for keeping chronic-condition facts outside model fine-tuning and behind reviewed source records.

## Rule

Keep detailed feature work inside the matching part folder. Keep only team-wide summaries, collaboration rules, and cross-part operating guides in this root directory.

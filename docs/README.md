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
- `Integration-docs/05-grounded-chatbot-prd.md`: 검수 지식 기반 동적 답변 프레임 챗봇의 제품 요구사항.
- `Integration-docs/06-grounded-chatbot-tdd.md`: PRD를 구현하기 위한 Technical Design Document와 `AnswerCard` 내부 프레임 설계.
- `Integration-docs/07-grounded-chatbot-todo.md`: TDD 기반 단계별 구현 TODO와 검증 게이트.
- `Integration-docs/08-grounded-chatbot-trd.md`: PRD 기반 기술 요구사항 명세.
- `Integration-docs/09-grounded-chatbot-implementation-log.md`: PRD/TRD/TDD/TODO 기반 챗봇 구현 결과와 검증 로그.
- `Integration-docs/10-grounded-chatbot-gap-review.md`: LLM-WIKI와 Lemon Aid 문서를 기준으로 현재 챗봇 코드의 정렬 상태와 후속 TODO를 점검한 리뷰.
- `Integration-docs/11-supabase-chatbot-dev-setup.md`: 챗봇을 빠르게 개발하기 위해 Supabase PostgreSQL을 개발 DB로 연결하는 방법과 스모크 테스트 절차.
- `Integration-docs/12-agent-chatbot-todo.md`: 앱 전체 컨텍스트를 읽는 개인화 건강 에이전트와 챗봇/분석 공통 planning layer 구현 TODO.
- `Integration-docs/13-agent-chatbot-release-todo.md`: 완료된 agent/chatbot v1을 PR 분리, 테스트 환경 정리, live smoke, reviewed evidence 운영 루프로 가져가기 위한 릴리스 TODO.
- `Integration-docs/14-agent-chatbot-release-execution-report.md`: 릴리스 TODO 실행 결과, PR 분리표, smoke 검증, SGLang 블로커와 evidence 운영 루프 정리.
- `Integration-docs/15-agent-llm-gap-audit.md`: 초기 통합 설계부터 DB/source governance, RAG, agent/LLM 보완점까지 다시 정리한 흐름 감사 문서.
- `Integration-docs/16-agent-chatbot-continuity-implementation-log.md`: 짧은 후속 질문이 이전 사용자 발화 맥락을 잃지 않도록 한 대화 연속성 구현 로그.
- `Integration-docs/17-agent-chatbot-source-governance-implementation-log.md`: unknown backlog 상태 흐름을 DB/source governance 운영 루프로 고정한 구현 로그.
- `Integration-docs/18-agent-chatbot-entity-normalization-implementation-log.md`: 약물/영양제 alias를 canonical entity로 정규화하고 넓은 약 표현을 needs_more_info로 닫은 구현 로그.
- `Integration-docs/19-agent-chatbot-boundary-coverage-implementation-log.md`: P0 상호작용 boundary가 stable boundary_code와 source metadata를 남기도록 한 구현 로그.
- `Integration-docs/20-agent-chatbot-retrieval-eval-implementation-log.md`: DB evidence retrieval이 reviewed/not-expired gate를 통과한 row만 AnswerCard로 쓰도록 한 구현 로그.
- `Integration-docs/21-agent-chatbot-structured-output-implementation-log.md`: structured JSON schema 성공/실패 경로를 deterministic fallback과 함께 고정한 구현 로그.
- `Integration-docs/22-agent-chatbot-source-ui-observability-implementation-log.md`: Flutter source metadata 표시와 raw-free 운영 리포트 payload를 연결한 구현 로그.
- `Integration-docs/23-agent-llm-pipeline-flow.md`: 에이전트/LLM 전체 흐름을 파이프라인 이미지로 만들기 위한 레이어별 상세 정리.
- `Integration-docs/24-post-merge-integration-blueprint.md`: GitHub 원격 브랜치 병합 후 Agent/LLM/RAG 고도화를 위한 통합 지도와 병합 전 history/root 감사 기준.
- `Integration-docs/25-llm-rag-agent-advancement-start-gate.md`: LLM/RAG/Agent 고도화를 언제 시작할지 판단하는 계약 기반 Go/No-Go 기준.
- `Integration-docs/26-agent-llm-product-direction-reset.md`: Agent/LLM 제품 방향, 개인화 학습, 메모리, 분석 점수, 체크리스트, 의료 boundary를 다시 정리한 기준 문서.
- `Integration-docs/27-agent-llm-prd.md`: 26번 방향 재정리를 제품 요구사항으로 분해한 Agent/LLM PRD.
- `Integration-docs/28-agent-llm-trd.md`: Agent/LLM PRD를 구현자가 테스트 가능한 기술 요구사항으로 옮긴 TRD.
- `Integration-docs/29-agent-llm-tdd.md`: Agent/LLM memory, analysis, checklist, boundary, retrieval 흐름을 설계한 Technical Design Document.
- `Integration-docs/30-agent-llm-todo.md`: Agent/LLM 새 기준을 PR 단위로 실행하기 위한 TODO와 검증 게이트.
- `Integration-docs/31-agent-llm-runtime-decision-eval.md`: Agent/LLM runtime 방향을 SGLang 운영 후보와 Ollama fallback으로 고정하고 모델 채택 eval gate를 정리한 기준 문서.
- `Integration-docs/32-agent-llm-model-smoke-eval-report.md`: Qwen baseline과 Gemma 후보를 비교하기 전 현재 deterministic eval 결과와 필수 live smoke gate를 정리한 리포트.
- `Integration-docs/33-agent-llm-team-integration-contract.md`: 팀 파트 병합 후 Agent가 소비해야 하는 DB/backend/Flutter 최소 I/O 계약과 현재 gap을 정리한 문서.
- `Integration-docs/34-agent-llm-readiness-audit.md`: 31~33번 기준을 현재 구현과 팀 브랜치 상태에 대입해 시작 가능한 slice와 no-go를 정리한 audit.
- `Integration-docs/35-agent-llm-orchestration-plan.md`: Agent/LLM 10일 full vertical integration의 phase, gate, touchpoint map, future risk를 관리하는 실행 관제판.
- `Integration-docs/36-medical-wiki-rag-execution-plan.md`: MEDICAL-WIKI 42 claim/94 EvidenceBundle 이후 source contract, sanitized trace/LangSmith, retrieval, reranker, vector DB, SGLang polish 후속 실행 계획.
- `superpowers/plans/2026-05-22-mvp-runtime-and-medical-knowledge-todo.md`: current FastAPI + Flutter web + AI Agent smoke checklist and medical knowledge boundary TODO.
- `Nutrition-docs/dev-guides/31-medical-knowledge-layer.md`: medical knowledge layer design for keeping chronic-condition facts outside model fine-tuning and behind reviewed source records.

## How To Use This Index

- Start here when a topic could belong to more than one workstream.
- Move into the closest folder README before opening individual documents.
- For chatbot, LLM, RAG, reviewed-source, or runtime integration work, read
  `Integration-docs/README.md` first.
- For Agent/LLM work specifically, use the "Agent/LLM 문서 참조 가이드" section in
  `Integration-docs/README.md` to decide whether to read 26~30 product/design docs,
  31~32 runtime/eval docs, or 33~34 team-integration/readiness docs first.
- For nutrition, OCR, supplement, or medical-knowledge implementation details,
  start from `Nutrition-docs/` and its nearest README or dev guide index.

## Rule

Keep detailed feature work inside the matching part folder. Keep only team-wide summaries, collaboration rules, and cross-part operating guides in this root directory.
When adding or moving a document, update the nearest README with one sentence
that says what the document is for. Use searchable names such as
`NN-topic-purpose.md` for ordered design docs or `YYYY-MM-DD-topic.md` for
dated reports and logs.

<!-- docs-index:start -->
## 자동 파일 목록

이 영역은 `python scripts/update_docs_index.py --write <폴더>`로 갱신합니다.

### 현재 폴더 파일
- [01-project-overview.md](./01-project-overview.md): 01. Project Overview
- [03-project-intent.md](./03-project-intent.md): 03. Project Intent
- [05-github-guidelines.md](./05-github-guidelines.md): 05. GitHub 협업 규칙 (GitHub Collaboration Guidelines)
- [06-tech-stack.md](./06-tech-stack.md): 06. Tech Stack
- [10-compliance-checklist.md](./10-compliance-checklist.md): 10. Compliance Checklist

### 하위 폴더 색인
- [Chat-docs/](./Chat-docs/README.md): Chat Docs
- [Food-docs/](./Food-docs/README.md): Food Docs
- [Integration-docs/](./Integration-docs/README.md): Integration Docs
- [track-d/](./track-d/README.md): docs/track-d/ — Track D (모바일) 작업 산출물

<!-- docs-index:end -->

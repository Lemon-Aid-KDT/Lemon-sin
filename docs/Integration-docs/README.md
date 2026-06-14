# Integration Docs

Final integration, deployment, and demo documents belong here.

## Agent/LLM 문서 참조 가이드

이 섹션은 "어떤 문서를 수정할지"가 아니라 "작업 전에 어떤 기준 문서를 먼저
참조할지"를 정하는 가이드입니다. 문서 번호가 곧 작업 순서는 아닙니다.

Agent/LLM, chatbot, RAG, runtime, DB/mobile/backend 통합 작업을 시작할 때는
문서를 단순히 번호순으로 모두 읽지 말고 아래 기준으로 필요한 문서를 먼저 확인합니다.

기본 원칙:

1. 새 Agent/LLM 방향, 모델, runtime, 팀 통합 판단은 26~34번을 기준으로 합니다.
2. 그 판단을 실제 코드에 적용하다가 기존 grounded chatbot 코드나 계약을 건드리게 되면
   05~10번, 17~22번을 함께 확인합니다.
3. 새 문서는 꼭 필요할 때만 만들고, 기존 결정의 보강이면 26~34번 중 가장 가까운 문서를
   갱신합니다.

### Agent/LLM 방향을 판단할 때

- Agent/LLM의 제품 방향이나 답변 철학을 판단할 때:
  [26-agent-llm-product-direction-reset.md](./26-agent-llm-product-direction-reset.md)
- 제품 요구사항을 구현 범위로 바꿀 때:
  [27-agent-llm-prd.md](./27-agent-llm-prd.md)
- backend, DB, mobile, runtime에 걸친 기술 요구사항을 확인할 때:
  [28-agent-llm-trd.md](./28-agent-llm-trd.md)
- memory, analysis, checklist, boundary, retrieval 설계를 구현할 때:
  [29-agent-llm-tdd.md](./29-agent-llm-tdd.md)
- 실제 PR 단위와 검증 순서를 잡을 때:
  [30-agent-llm-todo.md](./30-agent-llm-todo.md)

### Runtime 또는 모델 작업을 할 때

- SGLang, Ollama fallback, Qwen baseline, Gemma 후보, 모델 채택 기준을 판단할 때:
  [31-agent-llm-runtime-decision-eval.md](./31-agent-llm-runtime-decision-eval.md)
- 모델 smoke/eval 결과를 남기거나 live smoke gate를 확인할 때:
  [32-agent-llm-model-smoke-eval-report.md](./32-agent-llm-model-smoke-eval-report.md)

이 두 문서를 확인하지 않고 기본 모델을 바꾸거나 SGLang runtime을 production-ready로
판단하지 않습니다.

### 팀 통합 또는 현재 구현 상태를 볼 때

- 다른 팀의 DB/backend/mobile 결과물을 Agent가 어떤 I/O 계약으로 받아야 하는지 정할 때:
  [33-agent-llm-team-integration-contract.md](./33-agent-llm-team-integration-contract.md)
- 지금 바로 작업을 시작해도 되는지, 어떤 slice부터 해야 하는지 판단할 때:
  [34-agent-llm-readiness-audit.md](./34-agent-llm-readiness-audit.md)

팀 브랜치를 pull/merge하기 전에는 33번과 34번을 먼저 확인합니다. 현재 기준으로는
팀 브랜치를 바로 병합하기보다 Agent가 믿을 수 있는 confirmed record adapter,
memory schema, mobile response contract를 먼저 고정합니다.

### 기존 grounded chatbot 코드나 계약을 건드릴 때

이 문서들은 새 Agent/LLM 방향 문서가 아닙니다. 기존 chatbot 구현의 의도와 현재 동작을
확인하기 위한 참조 문서입니다. 즉, 26~34번 기준을 코드에 적용하는 과정에서
`AnswerCard`, reviewed evidence retrieval, unknown fallback, boundary renderer,
structured output, source UI 같은 기존 영역을 수정해야 할 때 확인합니다.

- 기존 chatbot의 PRD/TRD/TDD/TODO는 05~08번을 기준으로 봅니다.
- 구현된 범위와 남은 gap은 09~10번을 봅니다.
- source governance, entity normalization, boundary, retrieval, structured output,
  source UI observability의 구현 로그는 17~22번을 봅니다.

### 문서를 새로 만들 때

- 새 방향/의사결정 문서는 기존 문서에 통합할 수 있는지 먼저 확인합니다.
- runtime, model, eval, team contract, readiness 판단은 31~34번을 우선 갱신합니다.
- 새 문서를 추가했다면 이 README와 상위 [docs/README.md](../README.md)의 색인을 갱신합니다.

## Documents

- [01-ci-pr-integration-operations.md](./01-ci-pr-integration-operations.md): CI, PR, release, and cross-part integration operations.
- [02-ai-agent-worktree-integration-plan.md](./02-ai-agent-worktree-integration-plan.md): AI Agent worktree 기준축, PR 분리, 보안 preflight, safety/privacy gate.
- [03-ai-agent-safety-porting-contract.md](./03-ai-agent-safety-porting-contract.md): AI Agent, backend, DB, UI, RAG 선별 이식용 표준 응답/저장/안전 계약.
- [04-medical-source-db-contract.md](./04-medical-source-db-contract.md): 의료정보 DB의 source, claim, review, boundary, RAG 연결 기준과 DB 담당자 TODO.
- [05-grounded-chatbot-prd.md](./05-grounded-chatbot-prd.md): 검수 지식 기반 동적 답변 프레임 챗봇의 제품 요구사항.
- [06-grounded-chatbot-tdd.md](./06-grounded-chatbot-tdd.md): PRD를 구현하기 위한 Technical Design Document와 `AnswerCard` 내부 프레임 설계.
- [07-grounded-chatbot-todo.md](./07-grounded-chatbot-todo.md): TDD 기반 단계별 구현 TODO와 검증 게이트.
- [08-grounded-chatbot-trd.md](./08-grounded-chatbot-trd.md): PRD 기반 기술 요구사항 명세.
- [09-grounded-chatbot-implementation-log.md](./09-grounded-chatbot-implementation-log.md): PRD/TRD/TDD/TODO 기반 챗봇 구현 결과와 검증 로그.
- [10-grounded-chatbot-gap-review.md](./10-grounded-chatbot-gap-review.md): LLM-WIKI와 Lemon Aid 문서를 기준으로 현재 챗봇 코드의 정렬 상태와 후속 TODO를 점검한 리뷰.
- [11-supabase-chatbot-dev-setup.md](./11-supabase-chatbot-dev-setup.md): 챗봇을 빠르게 개발하기 위해 Supabase PostgreSQL을 개발 DB로 연결하는 방법과 스모크 테스트 절차.
- [12-agent-chatbot-todo.md](./12-agent-chatbot-todo.md): 앱 전체 컨텍스트를 읽는 개인화 건강 에이전트와 챗봇/분석 공통 planning layer 구현 TODO.
- [13-agent-chatbot-release-todo.md](./13-agent-chatbot-release-todo.md): 완료된 agent/chatbot v1을 PR 분리, 테스트 환경 정리, live smoke, reviewed evidence 운영 루프로 가져가기 위한 릴리스 TODO.
- [14-agent-chatbot-release-execution-report.md](./14-agent-chatbot-release-execution-report.md): 릴리스 TODO 실행 결과, PR 분리표, smoke 검증, SGLang 블로커와 evidence 운영 루프 정리.
- [15-agent-llm-gap-audit.md](./15-agent-llm-gap-audit.md): 초기 통합 설계부터 DB/source governance, RAG, agent/LLM 보완점까지 다시 정리한 흐름 감사 문서.
- [16-agent-chatbot-continuity-implementation-log.md](./16-agent-chatbot-continuity-implementation-log.md): 짧은 후속 질문이 이전 사용자 발화 맥락을 잃지 않도록 한 대화 연속성 구현 로그.
- [17-agent-chatbot-source-governance-implementation-log.md](./17-agent-chatbot-source-governance-implementation-log.md): unknown backlog 상태 흐름을 DB/source governance 운영 루프로 고정한 구현 로그.
- [18-agent-chatbot-entity-normalization-implementation-log.md](./18-agent-chatbot-entity-normalization-implementation-log.md): 약물/영양제 alias를 canonical entity로 정규화하고 넓은 약 표현을 needs_more_info로 닫은 구현 로그.
- [19-agent-chatbot-boundary-coverage-implementation-log.md](./19-agent-chatbot-boundary-coverage-implementation-log.md): P0 상호작용 boundary가 stable boundary_code와 source metadata를 남기도록 한 구현 로그.
- [20-agent-chatbot-retrieval-eval-implementation-log.md](./20-agent-chatbot-retrieval-eval-implementation-log.md): DB evidence retrieval이 reviewed/not-expired gate를 통과한 row만 AnswerCard로 쓰도록 한 구현 로그.
- [21-agent-chatbot-structured-output-implementation-log.md](./21-agent-chatbot-structured-output-implementation-log.md): structured JSON schema 성공/실패 경로를 deterministic fallback과 함께 고정한 구현 로그.
- [22-agent-chatbot-source-ui-observability-implementation-log.md](./22-agent-chatbot-source-ui-observability-implementation-log.md): Flutter source metadata 표시와 raw-free 운영 리포트 payload를 연결한 구현 로그.
- [23-agent-llm-pipeline-flow.md](./23-agent-llm-pipeline-flow.md): 에이전트/LLM 전체 흐름을 파이프라인 이미지로 만들기 위한 레이어별 상세 정리.
- [24-post-merge-integration-blueprint.md](./24-post-merge-integration-blueprint.md): GitHub 원격 브랜치 병합 후 Agent/LLM/RAG 고도화를 위한 통합 지도와 병합 전 history/root 감사 기준.
- [25-llm-rag-agent-advancement-start-gate.md](./25-llm-rag-agent-advancement-start-gate.md): LLM/RAG/Agent 고도화를 언제 시작할지 판단하는 계약 기반 Go/No-Go 기준.
- [26-agent-llm-product-direction-reset.md](./26-agent-llm-product-direction-reset.md): Agent/LLM 제품 방향, 개인화 학습, 메모리, 분석 점수, 체크리스트, 의료 boundary를 다시 정리한 기준 문서.
- [27-agent-llm-prd.md](./27-agent-llm-prd.md): 26번 방향 재정리를 제품 요구사항으로 분해한 Agent/LLM PRD.
- [28-agent-llm-trd.md](./28-agent-llm-trd.md): Agent/LLM PRD를 구현자가 테스트 가능한 기술 요구사항으로 옮긴 TRD.
- [29-agent-llm-tdd.md](./29-agent-llm-tdd.md): Agent/LLM memory, analysis, checklist, boundary, retrieval 흐름을 설계한 Technical Design Document.
- [30-agent-llm-todo.md](./30-agent-llm-todo.md): Agent/LLM 새 기준을 PR 단위로 실행하기 위한 TODO와 검증 게이트.
- [31-agent-llm-runtime-decision-eval.md](./31-agent-llm-runtime-decision-eval.md): Agent/LLM runtime 방향을 SGLang 운영 후보와 Ollama fallback으로 고정하고 모델 채택 eval gate를 정리한 기준 문서.
- [32-agent-llm-model-smoke-eval-report.md](./32-agent-llm-model-smoke-eval-report.md): Qwen baseline과 Gemma 후보를 비교하기 전 현재 deterministic eval 결과와 필수 live smoke gate를 정리한 리포트.
- [33-agent-llm-team-integration-contract.md](./33-agent-llm-team-integration-contract.md): 팀 파트 병합 후 Agent가 소비해야 하는 DB/backend/Flutter 최소 I/O 계약과 현재 gap을 정리한 문서.
- [34-agent-llm-readiness-audit.md](./34-agent-llm-readiness-audit.md): 31~33번 기준을 현재 구현과 팀 브랜치 상태에 대입해 시작 가능한 slice와 no-go를 정리한 audit.
- [35-agent-llm-orchestration-plan.md](./35-agent-llm-orchestration-plan.md): Agent/LLM 10일 full vertical integration의 phase, gate, touchpoint map, future risk를 관리하는 실행 관제판.
- [36-medical-wiki-rag-execution-plan.md](./36-medical-wiki-rag-execution-plan.md): MEDICAL-WIKI 42 claim/94 EvidenceBundle 이후 source contract, sanitized trace/LangSmith, retrieval, reranker, vector DB, SGLang polish 후속 실행 계획.

## 문서 추가 기준

- 제품 의도는 `prd`, 기술 요구사항은 `trd`, 설계는 `tdd`, 실행 항목은 `todo`,
  구현 결과는 `implementation-log`, 차이 점검은 `gap-review`가 파일명에 드러나게
  둡니다.
- 새 통합 문서를 만들 때는 번호를 이어 붙인 `NN-topic-purpose.md` 형식을 기본으로
  사용합니다.
- 문서를 추가하거나 이동하면 이 README와 상위
  [`docs/README.md`](../README.md)를 함께 갱신합니다.

<!-- docs-index:start -->
## 자동 파일 목록

이 영역은 `python scripts/update_docs_index.py --write <폴더>`로 갱신합니다.

### 현재 폴더 파일
- [01-ci-pr-integration-operations.md](./01-ci-pr-integration-operations.md): 01. CI, PR, And Integration Operations
- [02-ai-agent-worktree-integration-plan.md](./02-ai-agent-worktree-integration-plan.md): 02. AI Agent Worktree Integration Plan
- [03-ai-agent-safety-porting-contract.md](./03-ai-agent-safety-porting-contract.md): 03. AI Agent 안전 이식 계약
- [04-medical-source-db-contract.md](./04-medical-source-db-contract.md): 04. 의료정보 DB 계약
- [04-medical-source-db-implementation-log.md](./04-medical-source-db-implementation-log.md): 의료정보 DB 계약 구현 로그
- [05-grounded-chatbot-prd.md](./05-grounded-chatbot-prd.md): 05. 근거 기반 동적 답변 프레임 챗봇 PRD
- [06-grounded-chatbot-tdd.md](./06-grounded-chatbot-tdd.md): 06. 근거 기반 동적 답변 프레임 챗봇 TDD
- [07-grounded-chatbot-todo.md](./07-grounded-chatbot-todo.md): 07. 근거 기반 동적 답변 프레임 챗봇 TODO
- [08-grounded-chatbot-trd.md](./08-grounded-chatbot-trd.md): 08. 근거 기반 동적 답변 프레임 챗봇 TRD
- [09-grounded-chatbot-implementation-log.md](./09-grounded-chatbot-implementation-log.md): 09. 근거 기반 동적 답변 프레임 챗봇 구현 로그
- [10-grounded-chatbot-gap-review.md](./10-grounded-chatbot-gap-review.md): 10. 근거 기반 챗봇 문서-코드 갭 리뷰
- [11-supabase-chatbot-dev-setup.md](./11-supabase-chatbot-dev-setup.md): Supabase 챗봇 개발 DB 설정
- [12-agent-chatbot-todo.md](./12-agent-chatbot-todo.md): 12. 앱 컨텍스트 기반 에이전트 & 챗봇 TODO
- [13-agent-chatbot-release-todo.md](./13-agent-chatbot-release-todo.md): 13. 에이전트/챗봇 릴리스 TODO
- [14-agent-chatbot-release-execution-report.md](./14-agent-chatbot-release-execution-report.md): 14. 에이전트/챗봇 릴리스 실행 리포트
- [15-agent-llm-gap-audit.md](./15-agent-llm-gap-audit.md): 15. 에이전트/LLM/DB 흐름 감사
- [16-agent-chatbot-continuity-implementation-log.md](./16-agent-chatbot-continuity-implementation-log.md): 16. 에이전트/챗봇 대화 연속성 구현 로그
- [17-agent-chatbot-source-governance-implementation-log.md](./17-agent-chatbot-source-governance-implementation-log.md): 17. 에이전트/챗봇 Source Governance 구현 로그
- [18-agent-chatbot-entity-normalization-implementation-log.md](./18-agent-chatbot-entity-normalization-implementation-log.md): 18. 에이전트/챗봇 Entity Normalization 구현 로그
- [19-agent-chatbot-boundary-coverage-implementation-log.md](./19-agent-chatbot-boundary-coverage-implementation-log.md): 19. 에이전트/챗봇 Boundary Coverage 구현 로그
- [20-agent-chatbot-retrieval-eval-implementation-log.md](./20-agent-chatbot-retrieval-eval-implementation-log.md): 20. 에이전트/챗봇 Retrieval Eval 구현 로그
- [21-agent-chatbot-structured-output-implementation-log.md](./21-agent-chatbot-structured-output-implementation-log.md): 21. 에이전트/챗봇 Structured Output 구현 로그
- [22-agent-chatbot-source-ui-observability-implementation-log.md](./22-agent-chatbot-source-ui-observability-implementation-log.md): 22. 에이전트/챗봇 Source UI와 Observability 구현 로그
- [23-agent-llm-pipeline-flow.md](./23-agent-llm-pipeline-flow.md): 23. 에이전트/LLM 파이프라인 흐름 정리
- [24-post-merge-integration-blueprint.md](./24-post-merge-integration-blueprint.md): 24. 병합 후 통합 계획 (Post-Merge Integration Blueprint)
- [25-llm-rag-agent-advancement-start-gate.md](./25-llm-rag-agent-advancement-start-gate.md): 25. LLM/RAG/Agent 고도화 시작 기준
- [26-agent-architecture.html](./26-agent-architecture.html): 26 agent architecture
- [26-agent-llm-product-direction-reset.md](./26-agent-llm-product-direction-reset.md): 26. Agent/LLM 제품 방향 재정리
- [26-agent-presentation.html](./26-agent-presentation.html): 26 agent presentation
- [27-agent-llm-prd.md](./27-agent-llm-prd.md): 27. Agent/LLM PRD
- [27-chatbot-architecture.html](./27-chatbot-architecture.html): 27 chatbot architecture
- [28-agent-llm-trd.md](./28-agent-llm-trd.md): 28. Agent/LLM TRD
- [29-agent-llm-tdd.md](./29-agent-llm-tdd.md): 29. Agent/LLM TDD
- [30-agent-llm-todo.md](./30-agent-llm-todo.md): 30. Agent/LLM TODO
- [31-agent-llm-runtime-decision-eval.md](./31-agent-llm-runtime-decision-eval.md): 31. Agent/LLM Runtime Decision & Eval 기준
- [32-agent-llm-model-smoke-eval-report.md](./32-agent-llm-model-smoke-eval-report.md): 32. Agent/LLM Model Smoke/Eval Report
- [33-agent-llm-team-integration-contract.md](./33-agent-llm-team-integration-contract.md): 33. Agent/LLM Team Integration Contract
- [34-agent-llm-readiness-audit.md](./34-agent-llm-readiness-audit.md): 34. Agent/LLM Readiness Audit
- [35-agent-llm-orchestration-plan.md](./35-agent-llm-orchestration-plan.md): 35. Agent/LLM Orchestration Plan
- [36-medical-wiki-rag-execution-plan.md](./36-medical-wiki-rag-execution-plan.md): 36. MEDICAL-WIKI RAG 실행 계획
- [37-agent-implementation-executive-audit.md](./37-agent-implementation-executive-audit.md): 37. Agent 구현 현황 통합 총괄 감사
- [38-agent-llm-merge-response-check-report.md](./38-agent-llm-merge-response-check-report.md): 38. Agent LLM 병합 전 응답 확인 리포트
- [40-agent-llm-development-roadmap.md](./40-agent-llm-development-roadmap.md): 40. Agent/LLM 전체 개발 로드맵
- [chatbot-unknown-backlog-report.md](./chatbot-unknown-backlog-report.md): Chatbot Unknown Knowledge Backlog

<!-- docs-index:end -->

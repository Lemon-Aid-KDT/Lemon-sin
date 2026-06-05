# 35. Agent/LLM Orchestration Plan

작성일: 2026-06-05

이 문서는 Agent/LLM 작업의 **실행 관제판**이다. 26~34번 문서를 다시 요약하거나
대체하지 않는다. 각 문서가 맡은 source of truth를 유지하면서, 어떤 순서로 실행하고
어떤 gate를 통과해야 다음 작업으로 갈 수 있는지 관리한다.

## 1. 문서 역할

35번 문서가 하는 일:

- Agent/LLM 작업의 phase, gate, blocked 조건을 한 곳에서 관리한다.
- 구현 slice를 시작하기 전에 작성할 touchpoint map 템플릿을 제공한다.
- 아직 구현/문서화가 약한 future risk를 누락되지 않게 추적한다.
- 새 문서를 계속 늘릴지, 기존 문서를 갱신할지 판단하는 운영 규칙을 둔다.

35번 문서가 하지 않는 일:

- 30번의 PR별 세부 TODO를 복제하지 않는다.
- 34번의 current-state readiness audit을 복제하지 않는다.
- 모델, schema, API 계약의 source of truth를 새로 만들지 않는다.
- 전체 touchpoint map을 미리 확정하지 않는다.

## 2. Source of Truth

| 영역 | 기준 문서 | 이 문서에서의 사용 방식 |
| --- | --- | --- |
| 제품 방향, Agent/LLM 정체성 | [26](./26-agent-llm-product-direction-reset.md) | 방향 판단 기준 |
| 제품 요구사항 | [27](./27-agent-llm-prd.md) | 제품 목표/비목표 판단 기준 |
| 기술 요구사항 | [28](./28-agent-llm-trd.md) | backend, DB, mobile, runtime 요구사항 기준 |
| 기술 설계 | [29](./29-agent-llm-tdd.md) | memory, analysis, checklist, boundary, retrieval 설계 기준 |
| 세부 PR TODO | [30](./30-agent-llm-todo.md) | PR별 실행 TODO 기준 |
| runtime/model/eval 기준 | [31](./31-agent-llm-runtime-decision-eval.md) | SGLang, Ollama fallback, Qwen/Gemma 채택 gate |
| smoke/eval 결과 | [32](./32-agent-llm-model-smoke-eval-report.md) | deterministic/live smoke 결과 기록 |
| 팀 통합 I/O 계약 | [33](./33-agent-llm-team-integration-contract.md) | DB/backend/mobile 최소 계약 |
| 현재 readiness 판단 | [34](./34-agent-llm-readiness-audit.md) | 지금 시작 가능한 slice와 no-go 판단 |

기존 grounded chatbot 구현을 수정해야 할 때는 05~10번과 17~22번을 함께 확인한다. 이때도
새 Agent/LLM 방향 판단은 26~34번을 기준으로 한다.

## 3. 10-Day Success Target

10일 목표는 축소판 chatbot이 아니다. 목표는 **Agent/LLM full vertical integration**이다.

Day 10 성공 기준:

- Flutter에서 사용자가 Agent에게 질문한다.
- Agent가 memory, app context, reviewed evidence를 함께 읽는다.
- LLM은 결정자가 아니라 답변 생성/정리 역할을 한다.
- 위험 질문은 BoundaryPlan으로 닫고, 근거 없는 질문은 unknown으로 닫는다.
- 음식, 영양제, 복약 context는 confirmed record 기준으로만 강하게 반영한다.
- today analysis snapshot과 smart analysis snapshot을 응답에 포함할 수 있다.
- checklist 후보와 CTA를 생성할 수 있다.
- `sources[]`, `ctas[]`, approval preview, boundary/unknown 상태를 Flutter가 표시할 수 있다.
- Qwen baseline과 Gemma 후보의 smoke/eval 결과가 있다.
- SGLang 경로를 우선 검증하고, 막히면 Ollama fallback으로 end-to-end demo가 돈다.
- golden scenario가 deterministic 경로와 LLM smoke 경로에서 핵심 boundary를 통과한다.

작업 방식:

- 기능을 빼지 않는다.
- 각 기능은 10일 안에 통합 가능한 v1 형태로 만든다.
- 완성도 고도화는 뒤로 미룰 수 있지만, 전체 흐름은 end-to-end로 돌아야 한다.
- 매일 최소 한 번 full flow smoke가 가능한 상태를 목표로 한다.

## 4. 10-Day Execution Board

10일 동안 순차 waterfall로 진행하지 않는다. 아래 track을 병렬로 진행하고, 매일 통합 상태를
확인한다.

| Track | 목표 | Day 10 산출물 | 주요 기준 문서 |
| --- | --- | --- | --- |
| Core Agent | memory, context resolver, answer plan, boundary, reviewed evidence를 연결한다. | memory + context + evidence 기반 답변 path | 26~30, 33~35 |
| Product Loop | today/smart analysis, checklist, CTA, approval preview를 연결한다. | analysis snapshot + checklist 후보 + CTA 응답 | 27~30, 33, 35 |
| Integration | DB confirmed adapter와 Flutter response contract를 맞춘다. | confirmed context와 mobile DTO/display contract | 30, 33~35 |
| Runtime | SGLang Qwen/Gemma, Ollama fallback, latency/error smoke를 검증한다. | Qwen/Gemma smoke 결과와 fallback demo path | 31, 32, 35 |
| Verification | golden scenarios와 demo script를 고정한다. | deterministic + LLM smoke + demo scenario | 30, 32, 35 |

10-day board:

| Day | 통합 목표 | 완료 gate |
| --- | --- | --- |
| Day 1 | 10일 목표 고정, Phase 1 touchpoint map 작성, worktree/doc 상태 보호 | 35번에 10-day board 반영, touchpoint map 준비 |
| Day 2 | Agent memory 4종 최소 schema와 v0 compatibility 시작 | memory 저장/조회 unit path |
| Day 3 | memory retrieval을 chat context에 연결 | raw 미저장 test, 기존 `agent_memory` read compatibility |
| Day 4 | confirmed food/supplement/medication context adapter 연결 | preview/candidate exclusion test |
| Day 5 | today/smart analysis snapshot과 checklist 후보 v1 연결 | response payload에 analysis/checklist/CTA 포함 |
| Day 6 | mobile response contract와 boundary/unknown/source 표시 연결 | Flutter DTO compatibility smoke |
| Day 7 | SGLang Qwen smoke와 Ollama fallback demo path 정리 | Qwen 또는 fallback end-to-end answer |
| Day 8 | Gemma 후보 smoke와 모델 비교 기록 | Qwen/Gemma/fallback 결과가 32번에 기록 |
| Day 9 | golden scenarios, error/timeout/fallback UX 정리 | representative scenarios 통과 |
| Day 10 | full vertical integration demo hardening | Flutter -> backend -> Agent/LLM -> response display demo 통과 |

## 5. Execution Phases

상태 값은 `Ready`, `In Progress`, `Blocked`, `Done`만 사용한다. PR별 체크박스는 30번에서
관리한다.

| Phase | 상태 | 목표 | 주요 기준 문서 | 완료 gate |
| --- | --- | --- | --- | --- |
| Phase 0. 기준 보호 | Done | 31~35 문서와 README 색인을 보호한다. | 31~35 | 문서가 index에 잡히고 diff check 통과 |
| Phase 1. Memory schema | Done | memory 4종 schema와 v0 compatibility adapter를 만든다. | 26~30, 33, 34 | raw 미저장 test와 기존 `agent_memory` read compatibility 통과 |
| Phase 2. Confirmed record adapter | Ready | 음식/영양제/복약 confirmed record만 Agent context로 쓰게 한다. | 26, 28~30, 33, 34 | preview/candidate exclusion test 통과 |
| Phase 3. Runtime live smoke | Blocked | SGLang Qwen/Gemma live smoke로 모델 후보를 비교한다. | 31, 32, 34 | SGLang prereq, Qwen smoke, Gemma smoke 통과 |
| Phase 4. Mobile response contract | Ready | Flutter가 CTA, approval, sources, boundary, analysis snapshot을 표시할 계약을 맞춘다. | 28~30, 33, 34 | DTO compatibility와 source/approval UI contract test 통과 |
| Phase 5. Integration hardening | Ready | session, rate limit, latency, observability, deletion, push 등 10일 성공에 필요한 gate를 정리한다. | 31~35 | Future Risk Register의 Blocker/Day-10 Critical 항목이 닫힘 |

## 6. Phase Gate Rules

### Phase 0. 기준 보호

시작 조건:

- 31~34번 문서가 작성되어 있다.
- README에 Agent/LLM 문서 참조 가이드가 있다.

완료 조건:

- 35번 문서가 작성된다.
- `docs/Integration-docs/README.md`와 `docs/README.md`에 35번이 잡힌다.
- `diff --check`가 통과한다.

Blocked 조건:

- 35번이 30번 TODO 또는 34번 readiness audit을 중복해 source of truth가 둘로 갈라진다.

### Phase 1. Memory schema

시작 조건:

- Phase 0 완료.
- 구현 전 slice touchpoint map 작성.

완료 조건:

- `profile`, `behavior`, `conversation`, `safety` memory type을 저장/조회할 수 있다.
- 기존 v0 `agent_memory` summary를 깨지 않고 읽는다.
- raw transcript, raw prompt, raw provider payload가 memory에 저장되지 않는 negative test가 있다.

Blocked 조건:

- memory 저장이 공식 음식/영양제/복약 DB를 자동 수정한다.
- chat-derived memory와 confirmed app record가 구분되지 않는다.

### Phase 2. Confirmed record adapter

시작 조건:

- 구현 전 slice touchpoint map 작성.
- 팀 브랜치를 바로 merge하지 않고 contract adapter 기준으로 확인한다.

완료 조건:

- 영양제는 `user_confirmed=true`와 deterministic `nutrient_code` 기준을 통과한 데이터만 강하게 반영한다.
- 식단은 user review/confirmation equivalent 기준을 통과한 데이터만 강하게 반영한다.
- 복약은 active status, provenance, medication class 기준이 명확하다.
- OCR/YOLO/LLM preview는 Agent context에서 확정 기록으로 쓰이지 않는다.

Blocked 조건:

- preview/candidate 데이터가 confirmed record와 같은 priority로 들어간다.
- raw OCR/LLM/model output이 context나 memory에 들어간다.

### Phase 3. Runtime live smoke

시작 조건:

- SGLang server와 model serving 환경이 준비된다.
- 31번의 Qwen baseline, Gemma candidate 기준을 유지한다.

완료 조건:

- SGLang Qwen live smoke 결과가 32번에 기록된다.
- SGLang Gemma live smoke 결과가 32번에 기록된다.
- Ollama fallback smoke 결과가 32번에 기록된다.
- answerability, boundary, source use, structured JSON parse, latency를 비교한다.

Blocked 조건:

- SGLang prereq가 통과하지 않는다.
- live smoke 없이 Gemma를 기본 모델로 바꾸려 한다.
- Ollama fallback을 production runtime으로 간주한다.

### Phase 4. Mobile response contract

시작 조건:

- 33번의 Agent I/O 계약을 기준으로 endpoint/DTO mismatch를 확인한다.
- 구현 전 slice touchpoint map 작성.

완료 조건:

- `sources[]`, `ctas[]`, `requires_user_approval`, `BoundaryPlan`, `analysis_snapshot` 표시 계약이 맞는다.
- timeout/error/fallback UX가 최소 계약에 포함된다.
- raw/internal field가 Flutter 응답에 노출되지 않는 test가 있다.

Blocked 조건:

- `/api/v1/agents/chat`와 `/api/v1/ai-agent/chat` endpoint 기준이 정리되지 않는다.
- Flutter가 unknown/source/boundary 상태를 구분해 표시할 수 없다.

### Phase 5. Integration hardening

시작 조건:

- Phase 1~4의 핵심 계약이 안정된다.
- Future Risk Register에서 Blocker/Day-10 Critical 항목의 owner가 정해진다.

완료 조건:

- session, rate limit, latency, observability, deletion, push, concurrency 중 Day 10 성공에 필요한 항목의 gate가 정리된다.
- release 전 필수 smoke/eval/monitoring 기준이 문서화된다.

Blocked 조건:

- 운영 리스크가 "나중에"로만 남고 owner/gate가 없다.

## 7. Slice Touchpoint Map Template

구현 slice가 확정되면 코드 수정 전에 아래 템플릿을 이 문서 또는 해당 slice 문서에 복사해
채운다. 전체 시스템 touchpoint map을 미리 만들지 않는다.

```markdown
### Touchpoint Map: <slice name>

- 목표:
- 기준 문서:
- 건드릴 가능성이 있는 backend 영역:
- 건드릴 가능성이 있는 DB/migration 영역:
- 건드릴 가능성이 있는 mobile/API contract:
- 기존 grounded chatbot 문서 확인 필요 여부:
- 팀 브랜치에서 확인할 후보:
- migration 필요 여부:
- 테스트/smoke 명령:
- 건드리면 안 되는 영역:
- 연결된 Future Risk 항목:
- 완료 조건:
```

### Touchpoint Map: Agent/LLM full vertical integration Day 1

- 목표:
  - Day 10 full vertical integration을 줄이지 않고, Day 2부터 바로 구현할 첫 slice와 검증 명령을 고정한다.
  - Agent memory, confirmed context, mobile response contract, runtime smoke를 한꺼번에 병합하지 않고 각각의 adapter/gate로 분리한다.
- 기준 문서:
  - Agent/LLM 방향과 요구사항: [26](./26-agent-llm-product-direction-reset.md), [27](./27-agent-llm-prd.md), [28](./28-agent-llm-trd.md), [29](./29-agent-llm-tdd.md), [30](./30-agent-llm-todo.md)
  - runtime/eval/team/readiness: [31](./31-agent-llm-runtime-decision-eval.md), [32](./32-agent-llm-model-smoke-eval-report.md), [33](./33-agent-llm-team-integration-contract.md), [34](./34-agent-llm-readiness-audit.md)
  - 기존 grounded chatbot 기준: [05](./05-grounded-chatbot-prd.md), [06](./06-grounded-chatbot-tdd.md), [07](./07-grounded-chatbot-todo.md), [08](./08-grounded-chatbot-trd.md), [09](./09-grounded-chatbot-implementation-log.md), [10](./10-grounded-chatbot-gap-review.md)
  - 관련 구현 로그 확인 대상: [17](./17-agent-chatbot-source-governance-implementation-log.md), [18](./18-agent-chatbot-entity-normalization-implementation-log.md), [19](./19-agent-chatbot-boundary-coverage-implementation-log.md), [20](./20-agent-chatbot-retrieval-eval-implementation-log.md), [21](./21-agent-chatbot-structured-output-implementation-log.md), [22](./22-agent-chatbot-source-ui-observability-implementation-log.md)
- 건드릴 가능성이 있는 backend 영역:
  - Day 2 첫 slice: `backend/Nutrition-backend/src/models/db/agent_memory.py`, `backend/Nutrition-backend/src/services/agent_memory.py`, `backend/Nutrition-backend/tests/unit/services/test_agent_memory.py`, `backend/Nutrition-backend/tests/unit/db/test_models.py`
  - compatibility 확인: `backend/Nutrition-backend/src/api/v1/ai_agent.py`, `backend/ai_agent_chat/src/lemon_ai_agent/app_intake.py`, `backend/ai_agent_chat/tests/test_agent_memory_context.py`
- 건드릴 가능성이 있는 DB/migration 영역:
  - 기존 `agent_memory` v0 table을 깨지 않는 additive migration 또는 repository-level compatibility를 우선 검토한다.
  - Day 2에서는 `profile_memory`, `behavior_memory`, `conversation_memory`, `safety_memory` type contract와 raw/internal field exclusion을 먼저 테스트로 고정한다.
- 건드릴 가능성이 있는 mobile/API contract:
  - Day 1에는 수정하지 않는다.
  - Day 6 후보로 `answerability`, `sources[]`, `ctas[]`, `requires_user_approval`, `analysis_snapshot`, boundary/unknown 표시 계약만 유지 확인한다.
- 기존 grounded chatbot 문서 확인 필요 여부:
  - 필요하다. Day 2 memory slice가 `/api/v1/ai-agent/chat`, `agent_memory`, `daily_coaching_summary`, `AnswerCard`/boundary/unknown 경로와 충돌하지 않아야 한다.
  - 단, Day 2는 reviewed evidence/RAG coverage를 넓히는 작업이 아니므로 05~10번의 source governance를 재정의하지 않는다.
- 팀 브랜치에서 확인할 후보:
  - `origin/sunghoon-database`: memory/profile/reminder schema 후보를 adapter 계약 참고로만 본다.
  - `origin/yeong-tech`: `user_confirmed`, `requires_confirmation`, deterministic `nutrient_code` 원칙을 confirmed supplement adapter 후보로 본다.
  - `origin/jongpil-tech`: `needs_user_review`, `food_code`, `estimated_grams` 같은 식단 adapter 후보 필드만 본다.
  - `origin/taedong-design`: source/CTA/boundary/streaming UI 아이디어를 mobile response contract 후보로만 본다.
  - 위 브랜치는 Day 1/Day 2에서 merge 대상이 아니다.
- migration 필요 여부:
  - Day 2 시작 전 확인한다.
  - v0 `agent_memory` table에 type contract만 추가해도 충분하면 migration 없이 service/repository compatibility를 먼저 고정한다.
  - 새 컬럼이 필요하면 raw transcript, raw prompt, raw provider payload 컬럼은 추가하지 않는다.
- 테스트/smoke 명령:
  - Day 2 RED 후보:
    - `python -m pytest -q --no-cov backend/Nutrition-backend/tests/unit/services/test_agent_memory.py`
    - `python -m pytest -q --no-cov backend/Nutrition-backend/tests/unit/db/test_models.py`
    - `python -m pytest -q --no-cov backend/ai_agent_chat/tests/test_agent_memory_context.py`
  - Day 2 GREEN 후 회귀 후보:
    - `python -m pytest -q --no-cov backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
    - `python backend/scripts/eval_chatbot_golden.py`
- 건드리면 안 되는 영역:
  - 팀 브랜치 직접 merge 또는 cherry-pick
  - Gemma 기본 모델 전환, SGLang runtime 기본값 변경
  - `guide.html` 직접 수정
  - raw chat 전문, raw prompt, raw OCR, raw LLM output, provider payload를 memory/API/unknown backlog에 저장하는 구조
  - OCR/YOLO/LLM preview를 confirmed food/supplement/medication context로 승격하는 구조
  - reviewed source governance, `AnswerCard`, boundary/unknown renderer의 source of truth 재정의
- 연결된 Future Risk 항목:
  - Conversation session 관리
  - Privacy/deletion
  - Multi-device/concurrency
  - Reviewed evidence 콘텐츠 운영
  - Mobile contract completeness
  - Production LLM infra
- 완료 조건:
  - 35번의 Day 1 checklist와 gate가 완료 상태로 갱신된다.
  - Day 2 첫 구현 slice가 `Agent memory 4종 schema + v0 compatibility adapter`로 명확하다.
  - 팀 의존 질문과 독립 구현 작업이 분리되어 있다.
  - 코드 수정 전에 건드리면 안 되는 영역과 테스트 명령이 명시되어 있다.

### Touchpoint Map: Agent/LLM full vertical integration Day 3

- 목표:
  - Day 2에서 만든 `profile_memory`, `behavior_memory`, `conversation_memory`,
    `safety_memory` bundle을 `/api/v1/ai-agent/chat`의 grounding context에 연결한다.
  - chat-derived memory는 사용자 보고/요약 정보로 낮은 강도로만 반영하고, 공식 음식/영양제/복약
    DB record처럼 확정 표현하지 않는다.
- 기준 문서:
  - Agent/LLM memory 설계: [29](./29-agent-llm-tdd.md), [30](./30-agent-llm-todo.md)
  - 팀 통합 I/O 계약과 readiness: [33](./33-agent-llm-team-integration-contract.md), [34](./34-agent-llm-readiness-audit.md)
  - Day 1/2 실행 gate: [35](./35-agent-llm-orchestration-plan.md)
  - 기존 grounded chatbot 기준: [05](./05-grounded-chatbot-prd.md), [06](./06-grounded-chatbot-tdd.md), [08](./08-grounded-chatbot-trd.md), [10](./10-grounded-chatbot-gap-review.md)
- 건드릴 가능성이 있는 backend 영역:
  - `backend/ai_agent_chat/src/lemon_ai_agent/agents/chatbot.py`
  - `backend/ai_agent_chat/tests/test_chatbot_agent.py`
  - `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
- 건드릴 가능성이 있는 DB/migration 영역:
  - 없다. Day 2의 service-level `memory_bundle` 계약을 소비한다.
- 건드릴 가능성이 있는 mobile/API contract:
  - response DTO는 바꾸지 않는다.
  - `used_tools`의 `agent_memory` 유지와 internal prompt/context raw-free 보장을 확인한다.
- 기존 grounded chatbot 문서 확인 필요 여부:
  - 필요하다. `AnswerCard`, reviewed evidence, boundary/unknown renderer의 source of truth를 재정의하지 않는다.
- 팀 브랜치에서 확인할 후보:
  - 없다. Day 3는 팀 브랜치 merge/cherry-pick 없이 현 worktree의 memory retrieval 소비만 구현한다.
- migration 필요 여부:
  - 없다.
- 테스트/smoke 명령:
  - RED/GREEN:
    - `python -m pytest -q --no-cov backend/ai_agent_chat/tests/test_chatbot_agent.py`
    - `python -m pytest -q --no-cov backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`
  - 회귀:
    - `python -m pytest -q --no-cov backend/Nutrition-backend/tests/unit/services/test_agent_memory.py backend/Nutrition-backend/tests/unit/db/test_models.py backend/ai_agent_chat/tests/test_agent_memory_context.py`
    - `python backend/scripts/eval_chatbot_golden.py`
- 건드리면 안 되는 영역:
  - 공식 음식/영양제/복약 DB 자동 수정
  - raw chat 전문, raw prompt, raw OCR, raw LLM output, provider payload의 prompt/API 노출
  - chat-derived memory를 confirmed app record와 같은 priority로 승격
  - reviewed evidence, `AnswerCard`, boundary/unknown renderer의 source of truth 변경
  - 팀 브랜치 직접 merge 또는 cherry-pick
- 연결된 Future Risk 항목:
  - Conversation session 관리
  - Privacy/deletion
  - Multi-device/concurrency
  - Medical boundary drift
- 완료 조건:
  - LLM prompt/grounding context에 4종 memory summary가 raw-free 형태로 들어간다.
  - confidence/provenance가 사용자 보고 또는 요약 memory로 표시되어 확정 기록과 구분된다.
  - 공식 음식/영양제/복약 DB는 chat 발화만으로 자동 수정되지 않는다.
  - memory context 관련 unit/integration smoke와 golden eval이 통과한다.

## 8. Future Risk Register

분류:

- `Blocker`: 이 항목이 닫히지 않으면 출시 또는 핵심 통합을 진행하지 않는다.
- `Day-10 Critical`: 10일 full vertical integration에 포함해 닫아야 한다.
- `After Day-10`: 10일 이후 고도화로 넘길 수 있지만 설계 충돌을 막기 위해 추적한다.
- `Watch`: 지금 결정하지 않되 구현 중 다시 확인한다.

| Risk | 분류 | 왜 중요한가 | 연결 Phase | 기준/갱신 문서 |
| --- | --- | --- | --- | --- |
| Streaming 응답 | Day-10 Critical | 10~30초 대기 UX를 줄이고 중간 실패를 설명해야 한다. 최소 loading/fallback UX라도 정해야 한다. | 4, 5 | 31, 33, 35 |
| Conversation session 관리 | Day-10 Critical | turn limit, timeout, compaction trigger, 앱 재시작 복원이 필요하다. | 1, 5 | 29, 30, 35 |
| Rate limiting/cost control | Day-10 Critical | LLM 비용 폭증과 반복 요청 abuse를 막아야 한다. | 3, 5 | 31, 32, 35 |
| Cold start | Day-10 Critical | 신규 사용자에게 분석/추천/질문 흐름을 어떻게 시작할지 정해야 한다. | 1, 4, 5 | 27, 29, 35 |
| Production LLM infra | Blocker | SGLang 운영, Ollama fallback 범위, 모델 lifecycle이 결정되어야 한다. | 3 | 31, 32 |
| Latency budget | Day-10 Critical | first token, total latency, timeout, degradation 기준이 필요하다. | 3, 5 | 31, 32, 35 |
| Error/timeout UX | Day-10 Critical | SGLang/LLM/DB 장애 시 Flutter와 backend 메시지가 일관돼야 한다. | 4, 5 | 33, 35 |
| Reviewed evidence 콘텐츠 운영 | Blocker | 구조만 있고 검수 콘텐츠가 부족하면 unknown으로 닫힌다. | 2, 5 | 30, 33, 34 |
| Privacy/deletion | Blocker | memory 삭제, 탈퇴, retention, raw archive 정책이 필요하다. | 1, 5 | 28, 29, 35 |
| Push notification | Day-10 Critical | checklist/reminder가 Agent action으로 노출되면 최소 등록/해제 계약 또는 명시적 deferred 상태가 필요하다. | 5 | 27, 30, 35 |
| Multi-device/concurrency | Day-10 Critical | message ordering, duplicate action, memory update race를 막아야 한다. | 1, 4, 5 | 29, 33, 35 |
| Mobile contract completeness | Day-10 Critical | CTA, approval, sources, BoundaryPlan card, analysis snapshot이 모두 맞아야 한다. | 4 | 33, 35 |
| Observability | Day-10 Critical | model, latency, answerability, fallback, unknown topic metrics가 필요하다. | 3, 5 | 31, 32, 35 |
| Rollback/fallback | Day-10 Critical | 모델 변경 실패 시 즉시 되돌릴 설정과 smoke 기준이 필요하다. | 3 | 31, 32 |
| Team merge risk | Watch | 팀 브랜치를 바로 병합하면 계약보다 구현 세부가 먼저 들어올 수 있다. | 2, 4, 5 | 33, 34, 35 |
| Secrets/API key hygiene | Blocker | 외부 OCR/LLM/API key가 prompt, log, repo에 섞이면 안 된다. | 3, 5 | 28, 31, 35 |
| Medical boundary drift | Blocker | 모델/renderer 변경 후 진단, 치료, 복용량 판단 문구가 다시 새어 나올 수 있다. | 3, 4, 5 | 26, 29, 30 |

## 9. 운영 규칙

- 새 Agent/LLM 방향, 모델, runtime, 팀 통합 판단은 먼저 26~34번 중 가까운 문서에 반영한다.
- 35번에는 10일 성공 기준, 실행 순서, gate 상태, future risk 연결만 반영한다.
- 세부 PR TODO는 30번을 갱신한다.
- smoke/eval 결과는 32번을 갱신한다.
- current-state readiness가 바뀌면 34번을 갱신한다.
- 코드 구현 전에는 해당 slice의 touchpoint map을 먼저 작성한다.
- 팀 브랜치는 바로 merge하지 않고, 33번 계약과 34번 readiness 기준으로 adapter 흡수 여부를 판단한다.
- 구현이 기존 grounded chatbot 코드나 계약을 건드리면 05~10번, 17~22번을 함께 확인한다.

## 10. Daily Execution TODO

이 TODO는 Day를 넘길 수 있는지 확인하기 위한 체크리스트다. 세부 PR TODO는 30번에서 관리하고,
여기서는 daily gate만 관리한다.

### Day 1. 기준 고정과 touchpoint map

- [x] 26~35번 문서에서 Day 1에 필요한 기준을 다시 확인한다.
- [x] `Touchpoint Map: Agent/LLM full vertical integration Day 1`을 작성한다.
- [x] 10일 성공 기준을 코드/문서/검증 작업으로 나눈다.
- [x] Core Agent, Product Loop, Integration, Runtime, Verification track별 Day 2~3 작업 경계를 정한다.
- [x] 팀 브랜치에서 확인할 후보를 merge 대상이 아니라 adapter 확인 대상으로 분리한다.
- [x] Day 2에서 바로 구현할 첫 코드 slice를 확정한다.
- [x] Day 1 완료 후 35번의 phase 상태를 갱신한다.

Day 1 완료 gate:

- [x] Day 1 touchpoint map이 작성되어 있다.
- [x] Day 2 첫 구현 slice와 테스트 명령이 명확하다.
- [x] 팀 의존 질문과 독립 구현 작업이 분리되어 있다.
- [x] 코드 수정 전에 건드리면 안 되는 영역이 명시되어 있다.

Day 1 실행 기록:

| 항목 | Day 1 판정 |
| --- | --- |
| 10일 성공 기준 분해 | `memory/context/evidence`, `analysis/checklist/CTA`, `DB/mobile contract`, `runtime smoke`, `golden/demo verification` 5개 track으로 유지한다. |
| Day 2 첫 구현 slice | `Agent memory 4종 schema + v0 compatibility adapter`를 첫 코드 slice로 시작한다. |
| Day 2 테스트 시작점 | `test_agent_memory.py`, `test_models.py`, `test_agent_memory_context.py`에 raw/internal exclusion과 v0 read compatibility RED를 먼저 추가한다. |
| Day 2에서 유지할 기존 경로 | v0 `daily_coaching` memory, `/api/v1/ai-agent/chat`, deterministic golden eval, `AnswerCard`/boundary/unknown 경로를 깨지 않는다. |
| 팀 의존 질문 | DB/team branch의 새 table/field, Flutter source/CTA/boundary 표시 세부 UI, SGLang live server 준비는 확인 대상으로 둔다. |
| 독립 구현 작업 | memory type contract, repository/service compatibility, raw prompt/transcript/provider payload 미저장 테스트는 현 worktree에서 바로 진행한다. |
| 사용자 확인 필요 여부 | Day 2 첫 slice를 시작하는 데 필요한 사용자 결정은 없다. 모델 전환, 팀 브랜치 병합, migration 방식이 충돌할 때만 확인한다. |

Day 2~3 track 경계:

| Track | Day 2 | Day 3 |
| --- | --- | --- |
| Core Agent | memory 4종 type contract와 v0 `agent_memory` read compatibility | memory bundle을 chat context 선택 규칙에 연결 |
| Product Loop | today/smart analysis는 수정하지 않고 memory 영향 후보만 기록 | conversation/behavior memory가 checklist/analysis로 들어가는 조건 정의 |
| Integration | migration 필요 여부와 existing `agent_memory` table compatibility 확인 | 공식 DB record와 chat-derived memory의 priority 분리 |
| Runtime | live model 변경 없음. deterministic fallback/golden을 회귀 기준으로 유지 | structured output/live smoke 준비만 병렬 추적 |
| Verification | raw/internal exclusion RED, model/service unit RED 작성 | chat route memory context smoke와 golden eval 회귀 |

### Day 2. Agent memory 최소 schema 시작

- [x] memory 4종 schema 구현 위치와 migration 필요 여부를 확인한다.
- [x] 기존 v0 `agent_memory` read compatibility를 유지한다.
- [x] raw transcript, raw prompt, raw provider payload 미저장 테스트를 먼저 고정한다.
- [x] memory repository 또는 service 최소 path를 구현한다.

Day 2 완료 gate:

- [x] memory 저장/조회 unit path가 있다.
- [x] raw/internal payload exclusion test가 있다.
- [x] 기존 chatbot/daily coaching path가 깨지지 않는다.

Day 2 실행 기록:

| 항목 | Day 2 판정 |
| --- | --- |
| 구현 위치 | 기존 `agent_memory` table을 유지하고 `backend/Nutrition-backend/src/services/agent_memory.py`의 service-level contract로 4종 memory를 추가했다. |
| migration 필요 여부 | 현재 Day 2 범위에서는 불필요하다. `memory_type`, `summary_json`, `source_counters` 기존 컬럼으로 v0 compatibility와 v2 memory taxonomy를 모두 표현할 수 있다. |
| memory type contract | `profile_memory`, `behavior_memory`, `conversation_memory`, `safety_memory`를 `AGENT_MEMORY_TYPES`로 고정했다. |
| 저장 path | `upsert_agent_memory_record()`가 compact summary, structured payload, confidence, source kind/ref, priority, review/expiry metadata를 sanitized `summary_json`으로 저장한다. |
| 조회 path | `load_agent_memory_context()`가 기존 `summaries`를 유지하면서 `memory_bundle`에 4종 memory를 type별로 묶어 반환한다. |
| v0 compatibility | 기존 `daily_coaching`, `confirmed_supplement`, `nutrition_analysis` memory type은 `summaries`에 그대로 남기고 4종 `memory_bundle`에는 섞지 않는다. |
| raw/internal exclusion | raw transcript, raw prompt, raw provider payload, raw OCR, raw LLM response, messages/provider payload key를 memory 저장/조회 결과에서 제거한다. |
| 기존 경로 회귀 | daily coaching memory service, DB model contract, app intake memory context, ai-agent API integration, deterministic golden eval을 회귀 검증 대상으로 확인했다. |

### Day 3. Memory retrieval과 chat context 연결

- [x] `profile`, `behavior`, `conversation`, `safety` memory retrieval을 chat context에 연결한다.
- [x] confidence/provenance가 답변 표현에 낮은 강도로 반영되는지 확인한다.
- [x] chat-derived memory와 confirmed app record가 섞이지 않게 한다.
- [x] 기존 grounded chatbot 흐름과 충돌하는지 05~10, 17~22 기준으로 확인한다.

Day 3 완료 gate:

- [x] Agent chat에서 memory context가 사용된다.
- [x] 공식 음식/영양제/복약 DB가 chat 발화만으로 자동 수정되지 않는다.
- [x] memory context 관련 smoke가 통과한다.

Day 3 실행 기록:

| 항목 | Day 3 판정 |
| --- | --- |
| 구현 위치 | `ChatbotAgent`가 `agent_memory.memory_bundle`을 `User-reported memory context` prompt section과 safety grounding context에 raw-free 요약으로 연결한다. |
| memory 표현 강도 | `confidence`, `source_kind`를 함께 표시하고 `confirmed app record가 아닌 낮은 강도 참고 정보` 문구로 공식 DB record와 구분한다. |
| raw/internal exclusion | `summary_json`, `raw_prompt`, `provider_payload`, `messages` 같은 internal key와 hidden payload는 prompt에 노출하지 않는다. |
| API contract 영향 | `/api/v1/ai-agent/chat` response DTO는 변경하지 않고 `agent_memory` used tool과 internal prompt safety만 보강했다. |
| DB/migration 영향 | 없다. Day 2의 기존 `agent_memory` service-level bundle 계약을 소비한다. |
| 회귀 기준 | `test_chatbot_agent.py`, `test_ai_agent_api.py`, Day 2 memory unit tests, deterministic golden eval을 회귀 검증 대상으로 확인한다. |

### Day 4. Confirmed context adapter

- [ ] 음식/영양제/복약 confirmed record 기준을 adapter로 고정한다.
- [ ] OCR/YOLO/LLM preview와 후보 데이터는 확정 context에서 제외한다.
- [ ] 팀 브랜치의 후보 필드는 33/34 기준으로 확인만 하고 바로 merge하지 않는다.
- [ ] 부족한 필드는 fixture 또는 compatibility layer로 Day 10 demo path를 확보한다.

Day 4 완료 gate:

- [ ] preview/candidate exclusion test가 있다.
- [ ] confirmed food/supplement/medication context가 Agent input에 들어간다.
- [ ] raw OCR/LLM/model output이 context에 들어가지 않는다.

### Day 5. Analysis snapshot, checklist, CTA

- [ ] today analysis snapshot v1을 response contract에 연결한다.
- [ ] smart analysis snapshot v1을 response contract에 연결한다.
- [ ] checklist 후보 1~3개와 확장 후보 구조를 만든다.
- [ ] CTA와 approval preview를 side effect 없이 반환한다.

Day 5 완료 gate:

- [ ] response payload에 analysis/checklist/CTA가 포함된다.
- [ ] 저장/알림/분석 실행은 사용자 승인 전에는 실행되지 않는다.
- [ ] 금지 문구와 medical boundary wording test가 통과한다.

### Day 6. Mobile response contract

- [ ] Flutter가 받을 `answerability`, `sources[]`, `ctas[]`, approval preview, boundary/unknown 상태를 맞춘다.
- [ ] `/api/v1/agents/chat`와 `/api/v1/ai-agent/chat` endpoint mismatch를 정리한다.
- [ ] source detail, boundary card, unknown card, loading/error UX 최소 계약을 맞춘다.
- [ ] raw/internal field가 mobile response에 노출되지 않게 한다.

Day 6 완료 gate:

- [ ] backend/mobile DTO compatibility smoke가 통과한다.
- [ ] Flutter에서 answer, source, CTA, boundary/unknown 상태를 표시할 수 있다.
- [ ] timeout/error/fallback 메시지가 최소 계약에 포함된다.

### Day 7. Qwen baseline runtime smoke

- [ ] SGLang Qwen 실행 조건을 확인한다.
- [ ] SGLang이 막히면 Ollama fallback demo path를 확보한다.
- [ ] Qwen baseline chatbot smoke를 실행하고 32번에 기록한다.
- [ ] latency, answerability, source use, boundary 결과를 기록한다.

Day 7 완료 gate:

- [ ] Qwen 또는 fallback 경로로 end-to-end answer가 나온다.
- [ ] 실패 원인과 fallback 조건이 32번 또는 35번에 남아 있다.
- [ ] Gemma smoke 준비 조건이 명확하다.

### Day 8. Gemma 후보 smoke와 모델 비교

- [ ] Gemma 후보 모델 실행 조건을 확인한다.
- [ ] Gemma chatbot smoke를 실행하고 32번에 기록한다.
- [ ] Qwen baseline, Gemma 후보, Ollama fallback 결과를 비교한다.
- [ ] 기본 모델 변경 여부는 live smoke 결과 없이 결정하지 않는다.

Day 8 완료 gate:

- [ ] Qwen/Gemma/fallback 비교 결과가 있다.
- [ ] 모델별 실패/timeout/JSON parse/source 사용 차이가 기록되어 있다.
- [ ] Day 10 demo runtime path가 확정되어 있다.

### Day 9. Golden scenarios와 failure UX

- [ ] 대표 golden scenarios를 deterministic + LLM smoke로 실행한다.
- [ ] 응급, unknown, 병용, 음식 조정, memory 반영, checklist/CTA 흐름을 확인한다.
- [ ] error/timeout/fallback UX를 Flutter/backend 계약에 맞춘다.
- [ ] observability 최소 항목을 기록한다.

Day 9 완료 gate:

- [ ] representative scenarios가 통과한다.
- [ ] 실패 케이스가 unknown/boundary/fallback으로 안전하게 닫힌다.
- [ ] demo script가 고정되어 있다.

### Day 10. Full vertical integration demo hardening

- [ ] Flutter -> backend -> Agent/LLM -> response display 전체 흐름을 확인한다.
- [ ] memory, confirmed context, reviewed evidence, analysis, checklist, CTA, source, boundary가 함께 돈다.
- [ ] Qwen/Gemma/fallback 중 Day 10 demo runtime path를 고정한다.
- [ ] 남은 gap은 35번 Future Risk Register 또는 30번 TODO로 되돌린다.

Day 10 완료 gate:

- [ ] full vertical integration demo가 통과한다.
- [ ] golden/smoke 결과가 기록되어 있다.
- [ ] Day 10 이후 고도화 항목과 Blocker가 분리되어 있다.
- [ ] 팀 통합 PR 또는 다음 작업 slice가 명확하다.

## 11. 다음 실행 기준

현재 기준의 다음 실행 후보는 Day 4다.

다음 구현은 음식/영양제/복약 confirmed record adapter를 연결하는 것이다. Day 4에서는
팀 브랜치를 바로 merge하지 않고 33번 계약과 34번 readiness 기준으로 후보 필드만 확인한다.
OCR/YOLO/LLM preview와 unconfirmed 후보는 Agent context에서 확정 기록으로 쓰이지 않도록
preview/candidate exclusion test를 먼저 고정한다. mobile response contract와 runtime smoke는
Day 5 이후 gate로 계속 병렬 추적한다.

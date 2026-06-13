# 40. Agent/LLM 전체 개발 로드맵

> 기준 시점: 2026-06-12 KST
> 입력 문서: [24](./24-post-merge-integration-blueprint.md) 병합 blueprint, [26](./26-agent-llm-product-direction-reset.md) 제품 방향, [30](./30-agent-llm-todo.md) 기능 TODO, [33](./33-agent-llm-team-integration-contract.md) 팀 계약, [35](./35-agent-llm-orchestration-plan.md) 오케스트레이션, [36](./36-medical-wiki-rag-execution-plan.md) RAG 실행 계획, [37](./37-agent-implementation-executive-audit.md) 통합 총괄 감사, [38](./38-agent-llm-merge-response-check-report.md) 병합 전 응답 확인
> 역할: 흩어진 실행 문서들(24/30/35/36/37)을 하나의 시간축 위에 재배열한 단일 실행 기준. 이 문서와 개별 문서가 충돌하면 이 문서를 따르고 개별 문서를 갱신한다.

## 1. 현재 위치 한 줄 요약

핵심 의료 안전 runtime(reviewed claim -> AnswerCard -> renderer/LLM polish -> SafetyGuard)은
구현·검증 완료, CI 통과, 병합 smoke gate 확보. **다음 병목은 새 기능이 아니라
(1) 한 달간 정체된 develop으로의 팀 병합, (2) DB 배선, (3) 제품 기능 백로그(체크리스트·
분석 점수·행동 승인), (4) 콘텐츠 확장 운영 루프다.**

## 2. 불변 원칙 (모든 Phase에 적용)

1. 모든 건강 답변은 reviewed card / boundary / unknown 중 하나로만 닫는다.
2. LLM은 판단자가 아니라 polish다. boundary/urgent는 LLM bypass를 유지한다.
3. raw prompt/OCR/LLM response/provider payload/health snapshot은 응답·memory·trace에 넣지 않는다.
4. Agent는 confirmed record만 강한 컨텍스트로 소비한다. preview/candidate는 제외한다.
5. 저장·알림·체크리스트 추가 등 부작용은 사용자 승인 전에 실행하지 않는다.
6. `sources[]` 등 API 확장은 additive만 허용한다. Flutter DTO를 깨지 않는다.
7. LangChain core/LangGraph/vector DB/LangSmith upload는 각 게이트(§6) 충족 전 도입 금지.

## 3. Phase 구조

전체 흐름:

```text
R0 팀 병합 게이트 (D+0~3, 최우선)
  -> R1 DB/Runtime 배선 (D+3~10)
       -> R2 제품 기능 완성 (D+10~24)
            -> R5 데모/릴리스 게이트 (D+24~30)
  ── 병렬 트랙 ──
  R3 콘텐츠/지식 확장 루프 (D+3~, 주간 cadence, 종료 없음)
  R4 운영 준비/품질 (D+5~, R2와 병행)
```

### Phase R0. 팀 병합 게이트 — D+0~3, 최우선

37번 통합 감사가 확인한 P0. 모든 후속 작업의 전제다.

| # | 작업 | 담당 제안 | 완료 게이트 |
|---|---|---|---|
| R0-1 | 24번 Phase 0 브랜치 감사: 팀 브랜치 merge-base 확인, unrelated history 브랜치 처리 방식 합의 | 태동 + 창민 | 브랜치별 병합 방식 결정 기록 |
| R0-2 | 병합 순서 합의: OCR 강화 -> YOLO/데이터 -> food gate -> 프로토콜 -> 모바일 -> **Agent(PR #4) 마지막** | 전원 | develop에 순차 반영 |
| R0-3 | PR #4 draft 해제 및 병합. 통째 병합 시 PR 본문 "팀 최소 계약"을 develop 규칙 문서로 승격 | 창민 | merge 완료 + 계약 문서화 |
| R0-4 | 병합 직후 전원 merge smoke: `check_ai_agent_runtime_prereqs.py` + `run_agent_llm_merge_smoke.py --llm sglang --require-answerable-llm` | 각 팀원 | 4/4 케이스 pass, `failures=[]` |
| R0-5 | develop branch protection + `Agent Backend CI`가 develop PR 필수 체크로 동작 확인 | 태동 | 보호 규칙 적용 |
| R0-6 | 병합 후 이후 PR 크기 규칙 명문화 (도메인 단위, 리뷰 가능한 수백 라인) | 전원 | 팀 가이드 반영 |

Agent를 마지막에 병합하는 이유: Agent는 다른 모든 브랜치의 출력(confirmed food/
supplement record, OCR `nutrient_code`, 프로필)을 입력으로 소비하므로, 입력 측 변경을
먼저 안정화한 뒤 계약 충돌을 한 번에 검증하는 것이 되돌리기 비용이 가장 작다.

### Phase R1. DB/Runtime 배선 — D+3~10 (24번 Phase B 대응)

| # | 작업 | 출처 | 완료 게이트 |
|---|---|---|---|
| R1-1 | PostgreSQL test DB 준비 (`127.0.0.1:55432`), `TEST_DATABASE_URL`/`RUN_POSTGRES_MIGRATION_SMOKE` 설정 | 38번 §3 | migration smoke 자동 실행 |
| R1-2 | `AgentRunLogger` InMemory -> DB 교체 | 24번 Phase B | DB-backed 로그 + raw-free 테스트 |
| R1-3 | `AgentMemoryWriter` DB 연결 (4종 memory: profile/behavior/conversation/safety) | 24번, 30번 PR B | owner-scoped 읽기/쓰기 테스트 |
| R1-4 | unknown backlog DB 반영 + medical_sources 시드 동기화 | 24번 Phase B | backlog가 DB에 적재 |
| R1-5 | app context route wiring 마무리: `UserHealthContextSnapshot`이 live DB record로 생성 | 37번 PR-Context | route-level contract test + adapter contract doc |
| R1-6 | DB-backed migration smoke를 CI nightly 또는 manual workflow에 연결 | 38번 §6 | workflow 실행 기록 |

### Phase R2. 제품 기능 완성 — D+10~24 (30번 PR C~M 재배열)

26번 제품 정체성의 미구현 절반을 완성한다. 의존성 기준 재배열:

| 묶음 | PR | 내용 | 순서 근거 |
|---|---|---|---|
| 2a. Memory 완성 | PR C + D | conversation compaction (rolling summary), 채팅 유래 정보 -> `safety_memory` (공식 DB 자동수정 차단) | R1-3 DB 배선 직후가 최적. 이후 모든 답변 품질의 기반 |
| 2b. 분석 점수 | PR F + G | 스마트 생활관리 점수 contract + 오늘 분석 wording hardening (26번 §12 금지/권장 표현) | 점수는 분석 탭 UI의 전제. wording은 컴플라이언스 직결 |
| 2c. 행동 루프 | PR H + I | checklist planner (기본 1~3개 + 확장 모드) + action approval contract (승인 전 부작용 없음 테스트) | 26번 §13의 핵심 차별 기능. I는 H의 전제 계약 |
| 2d. Boundary 품질 | PR J | BoundaryPlan 설명형 renderer — "짧은 차단"이 아니라 "결정 금지 안에서 충분히 설명" (26번 §15) | 사용자 체감 품질 최대 항목. 2a 메모리 컨텍스트 활용 |
| 2e. 모바일 계약 | PR L | Flutter sources/CTA/approval/boundary 표시 계약 + 위젯 golden 테스트 (37번 §14) | 2b~2d 출력이 정의된 뒤 화면 계약 고정 |
| 2f. E2E 고정 | PR M | 페르소나 대표 시나리오 golden (라면 반복 -> 나트륨 코칭, 복약 병용 -> boundary 등) deterministic + LLM 경로 | 전체 묶음의 회귀 방지선. R5 데모 리허설 겸용 |

PR E(음식/영양제 알고리즘 adapter 감사)는 R0 병합 결과에 따라 2a 이전에 삽입한다 —
병합으로 들어온 food/OCR 산출물 필드가 33번 계약과 일치하는지 먼저 확인.

### Phase R3. 콘텐츠/지식 확장 운영 루프 — D+3부터 주간 cadence (37번 §12)

구조는 완성됐고 내용물이 부족하다(42 claims / answerable 10개). 도구가 아니라 운영
주기를 만든다.

| 항목 | 내용 |
|---|---|
| 주간 cadence | 매주 1회: unknown backlog triage (`triage_priority` 기준) -> 승격 후보 선정 -> 공식 source 검수 -> claim/boundary/allowed·blocked wording 등록 -> golden test 추가 |
| 주간 목표 | reviewed claim +5~8개/주 (의료 검수 가능 범위 내) |
| 분기 목표 | 50+ claims / 100+ eval / 75~150 sections — 36번 Phase 6 vector DB 실험 조건 충족 |
| 담당 | 창민 (검수 기준은 26번 §14 운영 루프, 33번 evidence 계약 준수) |
| 게이트 | claim-level review metadata + golden test 없이는 runtime 미반영 (37번 §7.2 유지) |

### Phase R4. 운영 준비/품질 — D+5부터 R2와 병행

| # | 작업 | 출처 | 완료 게이트 |
|---|---|---|---|
| R4-1 | p95 latency local baseline 수집 -> SLO 초기 target 설정 | 37번 §8 | metric report에 target 대비 기록 |
| R4-2 | runtime metric dashboard + alert routing (Slack 등) + trace 보존 정책 | 37번 PR-Observability | alert가 실제 채널에 도달 |
| R4-3 | `pip-audit` + Bandit scoped run을 CI에 추가 | 37번 P2 | CI 단계 통과 |
| R4-4 | retrieval/context folding 성능 benchmark (500/1k/5k claim fixture) | 37번 §6 | corpus 확장 전 baseline 확보 |
| R4-5 | Modularize 2차: `knowledge.py` -> classification/seed_registry/policy/eval_cases, `chatbot.py` -> prompt_builder/response_router 분리. behavior no-change 테스트 선행 | 37번 §5.2 | 파일별 1,000 lines 이하 + 전체 테스트 green |
| R4-6 | answerability/warning code/source family registry화 (Literal/Enum) + contract test | 37번 §4 | 문자열 drift 검출 테스트 |
| R4-7 | 개인정보 수명주기 정책 문서 + 구현: raw_chat_archive 보존 기간, memory 삭제/탈퇴 처리, 채팅 유래 정보 동의 (37번 §9.2) | 26번 §8, 35번 Blocker | 정책 문서 + 삭제 flow 테스트 |
| R4-8 | 감사 자동화: 파일 크기 lint, forbidden marker CI 정규화, `audit_agent_readiness.py` | 37번 §15 | CI에서 자동 실행 |

R4-5(큰 모듈 분리)는 38번 권고대로 병합 직전·직후를 피하고, R0 완료 후 안정기(D+7
이후)에 시작한다.

### Phase R5. 데모/릴리스 게이트 — D+24~30 (24번 Phase E 대응)

| # | 작업 | 완료 게이트 |
|---|---|---|
| R5-1 | 페르소나 E2E: 김건강(52세 만성질환자) / 박직장(38세 예방) 시나리오를 Flutter -> backend -> Agent full vertical로 실행 | PR M golden과 일치 |
| R5-2 | Safety 리허설: P0 병용, 응급, 검사수치, unknown 4종 라이브 확인 (38번 스모크 절차) | provider/answerability 기대값 일치 |
| R5-3 | 성능 확인: LLM 응답 p95 (R4-1 target), 분석 응답 시간 | target 충족 또는 완화 결정 기록 |
| R5-4 | streaming/loading UX, 세션 turn limit, rate limit 적용 여부 최종 결정 (37번 §15) | 데모 시나리오에서 대기 UX 검증 |
| R5-5 | 데모 스크립트 + 실패 시 fallback 시나리오 문서화 | 리허설 1회 통과 |

## 4. 주차별 타임라인 요약

| 주차 | 핵심 산출물 |
|---|---|
| W1 (6/12~6/18) | R0 팀 병합 완료 + 전원 merge smoke 통과. R1 착수 (test DB, migration smoke). R3 첫 triage 회의 |
| W2 (6/19~6/25) | R1 완료 (memory/logger/backlog DB 배선, route wiring). R2 착수 (PR E 감사 -> 2a memory). R4-1/2 observability |
| W3 (6/26~7/2) | R2 2b 분석 점수 + 2c 체크리스트/승인. R4-5 모듈 분리 1차. R3 claim 60개 돌파 목표 |
| W4 (7/3~7/9) | R2 2d boundary 품질 + 2e 모바일 계약 + 2f E2E golden. R4 잔여 (보안 audit, registry) |
| W5 (7/10~) | R5 데모 게이트 + 릴리스 판정. R3는 계속 |

일정은 팀 병합(R0)이 W1에 끝난다는 가정이다. R0가 밀리면 전체가 1:1로 밀린다 —
그래서 R0가 최우선이다.

## 5. 역할 배정 제안

| 트랙 | 주담당 | 협업 |
|---|---|---|
| R0 병합 오케스트레이션 | 태동 (CI/DB/모바일 전반) | 창민 (Agent 병합 + smoke 기준), 각 브랜치 소유자 |
| R1 DB 배선 | 창민 | 태동 (DB RLS/migration) |
| R2 제품 기능 | 창민 | neong (2e 모바일 계약), 태동 (Flutter 측 구현) |
| R3 콘텐츠 루프 | 창민 | 의료 검수 기준 자문 필요 시 멘토 |
| R4 운영/품질 | 창민 + 태동 (CI/보안) | — |
| R5 데모 | 전원 | — |

## 6. 의사결정 게이트 (조건 충족 전 도입 금지)

| 결정 | 조건 | 출처 |
|---|---|---|
| vector DB / LangChain helper 실험 | 50+ claims, 100+ eval, 75~150 sections 근접, EvidenceBundle 94/94 유지 | 36번 Phase 6 |
| LangGraph 도입 | retrieval retry loop 실수요 또는 approval suspend/resume HITL 또는 multi-agent handoff 필요. `plan()` 결합 계약 회귀 테스트 선행 | 36번 Phase 7 |
| SGLang 모델 상향 (0.5B -> 후보 비교) | R2 2d 완료 후 answerable 품질 평가 기준으로 Qwen 상위 모델/Gemma 비교 smoke. boundary bypass 84/84 + slot mutation 0 유지가 통과 조건 | 31/32/35번, 37번 §13 |
| LangSmith cloud/self-hosted upload | PHI-free + ids-only + raw 없음 확인 + 배포 형태 명시 결정 | 36번 Phase 5 |
| LLM fine-tuning | 장기 보류. 형식/말투/요약 개선 목적에 한정, 의료 지식 주입 금지 | 26번 §6.2 |

## 7. 중단/롤백 조건

다음 신호가 보이면 해당 Phase를 멈추고 원인부터 잡는다.

- merge smoke에서 `failures` 1건 이상, 또는 answerable이 strict gate에서 조용히 deterministic fallback
- boundary LLM bypass 84/84 깨짐 — 즉시 release block
- `unsafe_polish_fallback_count` >= 1 — 해당 prompt/모델 변경 롤백 후 분석
- `source_stale_count` >= 1 — 콘텐츠 검수 전까지 해당 claim 비활성
- forbidden marker scan 검출 — 보안 사고로 취급, 즉시 수정
- 병합 후 confirmed record 계약 위반 (preview가 강한 컨텍스트로 유입) — Agent 입력 차단 후 adapter 수정

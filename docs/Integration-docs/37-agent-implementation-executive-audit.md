# 37. Agent 구현 현황 통합 총괄 감사

> 기준 시점: 2026-06-12 KST
> 대상 worktree: `feat/ai-agent-backend-integration`
> 관점: PM + 개발 총괄 팀장 관점의 기획 대비 구현 성숙도, 모듈/인터페이스, 품질, 보안, 성능, 운영 준비도, 팀 병합 리스크 감사
> 통합 범위: 기존 총괄 감사와 별도 보완 메모를 하나로 합친 최신 기준 문서다. 실행 순서는 [40-agent-llm-development-roadmap.md](./40-agent-llm-development-roadmap.md)를 따른다.

## 1. 총괄 결론

Lemon Aid Agent는 "아이디어 검증" 단계를 지나, 검수 근거 기반 건강 답변을 안전하게
닫는 핵심 runtime은 상당히 구현된 상태다. 특히 `reviewed claim ->
EvidenceBundle/AnswerCard -> renderer/LLM polish -> SafetyGuard` 축은 문서, 코드,
golden/eval/smoke, CI가 서로 맞물려 있다.

다만 제품 기획 전체인 "앱 맥락을 이해하고, 개인 건강 컨텍스트를 반영하며, 안전한
행동 제안과 운영 관측까지 갖춘 Agent" 기준으로 보면 production 완료가 아니라
pre-production hardening 단계다. 2026-06-12 후속 커밋으로 CI 부재와 app context dirty
변경은 1차 해소됐지만, 현재 가장 큰 리스크는 코드 내부 P0가 아니라 **팀 병합 정체와
PR #4의 초대형 규모**다.

한 줄 판정:

| 축 | 판정 | 이유 |
|---|---:|---|
| 기획 방향 부합 | 높음 | 수동 FAQ가 아니라 reviewed evidence를 `AnswerCard`로 정규화하고, 없으면 unknown으로 닫는 방향이 구현됨 |
| 핵심 의료 안전 runtime | 높음 | boundary/unknown/unsupported claim/SafetyGuard/LLM bypass 테스트와 smoke가 축적됨 |
| 앱 맥락 기반 Agent | 중상 | `UserHealthContextSnapshot`와 app-record adapter가 커밋됐고 tests/CI에 포함됨. live DB route wiring은 추가 gate 필요 |
| 인터페이스/모듈 규격 | 중간 | 주요 seam은 존재하지만 `knowledge.py`, `ChatbotAgent`, `renderers.py`, `user_health_context.py`가 커지고 있음 |
| 테스트 자동화 | 중상 | Agent Backend CI가 생겼고 PR #4에서 성공. 단 DB migration/live runtime은 opt-in 또는 수동 성격이 남음 |
| 보안/개인정보 | 중상 | raw prompt/OCR/provider payload 차단, owner scoping, secret handling이 구현됨. 보존/삭제/동의 정책은 미완성 |
| 성능/확장성 | 중간 | 현재 corpus 규모에서는 충분하지만 retrieval/context folding benchmark와 SLO가 부족 |
| 장애 예방/모니터링 | 중간 | raw-free trace, runtime metrics, alert code, warning log는 있음. dashboard/routing/retention은 남음 |
| 팀 통합 준비 | 위험 | PR #4는 draft/open, 709 files, +159,211/-2,145 lines. develop은 2026-05-11 이후 실질 통합 정체 |

## 2. 현재 구현 단계 지도

### 2.1 제품 목표 대비 구현 단계

| 제품 능력 | 현재 단계 | 근거 | 남은 gate |
|---|---|---|---|
| 검수 지식 기반 답변 | 구현/검증됨 | `05` PRD, `06` TDD, `07` TODO, `AnswerCardNormalizer`, MEDICAL-WIKI adapter | reviewed claim/section 규모 확장, stale/source governance 지속 |
| 모르면 모른다고 답변 | 구현/검증됨 | `unknown_no_reviewed_source`, unknown backlog, unknown route tests | unknown backlog triage -> reviewed source 승격 운영 루프 |
| 의료 boundary 선차단 | 구현/검증됨 | P0 interaction, emergency, lab-value no-LLM tests | boundary taxonomy 확장, UI/QA 시나리오 확대 |
| LLM은 판단자가 아니라 polish | 1차 구현 | SGLang polish slot sealing, boundary LLM bypass, structured output fallback | answerable live 품질 평가, 모델 변경 regression |
| 앱 context 반영 | 1차 구현 | `UserHealthContextSnapshot`, app record snapshot builder, route coverage | DB route wiring, consent/ownership integration, adapter contract doc |
| 개인화 memory | 일부 구현 | `agent_memory`, memory bundle, raw-free exclusion tests | conversation compaction, chat-derived memory write policy, DB writer |
| checklist/action agent | 계획/부분 구현 | `30-agent-llm-todo.md` PR H/I/J 항목 다수 미완료 | action approval contract, no-side-effect-before-confirmation tests |
| observability/eval | 1차 구현 | sanitized trace, optional LangSmith exporter, dry-run eval export, runtime metric report/alert code | dashboard, alert routing, trace retention, regression monitor |
| 팀 통합 | 미해결 | PR #4 draft, develop 정체, 여러 팀 브랜치 병렬 성장 | merge smoke, DB migration smoke, branch protection, PR 크기 규칙 |

### 2.2 최근 구현 흐름

최근 커밋 흐름은 구현 방향이 올바르게 좁혀지고 있음을 보여준다.

- `97c39a3 feat(ai): connect medical wiki reviewed claims`
- `d949368 feat(ai): consume medical wiki evidence bundles`
- `20b2bce feat(ai): add sanitized tracing and langsmith export gate`
- `9941651 fix(ai): tolerate sglang structured output formatting`
- `bea3582 fix(ai): seal sglang polish slots`
- `9cffbed feat(ai): harden agent context and observability`
- `2046d22 feat(ai): add merge smoke and polish slot guard`
- `752542d ci(ai): lock merge smoke gates`
- `0a91a7b fix(ci): skip external medical wiki evals when absent`

이 순서는 "지식 연결 -> evidence bundle 소비 -> 관측/평가 -> SGLang polish 안정화 ->
app context/observability hardening -> merge smoke/CI gate"로 이어져, deterministic core 우선
방향과 맞다.

## 3. 37번 초기 판정에서 갱신된 내용

초기 감사의 방향 판정은 유효하지만, 같은 날 후속 커밋으로 일부 P0/P1이 해소되었다.

| 초기 판정 | 당시 등급 | 현재 상태 | 근거 |
|---|---:|---|---|
| CI workflow 부재 | P0 | 해소 | `.github/workflows/agent-backend-ci.yml` 존재. PR/push trigger + manual SGLang live smoke opt-in. PR #4에서 `Agent Backend CI` 2회 SUCCESS |
| app context adapter dirty 변경 | P0 | 해소(1차) | `9cffbed feat(ai): harden agent context and observability`로 app-record snapshot hardening 커밋 완료 |
| 운영 observability 미완성 | P1 | 부분 해소 | `build_runtime_metrics_report()`, alert code 6종, `StructuredLogRuntimeMetricsReporter` 구현. dashboard/routing/retention은 미해결 |
| 모듈 분리 미착수 | P1 | 일부 착수 | `polish_slots.py` 분리 완료. 큰 모듈 분리는 미착수 |
| 병합 전 LLM 응답 게이트 부재 | 미언급 | 추가됨 | `run_agent_llm_merge_smoke.py`, `--require-answerable-llm`, CI no-LLM smoke 연결 |

주의: 감사 시점의 `HEAD`는 `origin/feat/ai-agent-backend-integration`과 동기화되어 있었지만,
이 문서를 통합하는 로컬 작업 중에는 문서 파일 변경으로 worktree가 dirty일 수 있다. 따라서
"origin 동기화"와 "로컬 clean"은 구분한다.

## 4. 팀 통합 감사

### 4.1 PR #4 규모 리스크 — P0

GitHub 실측 기준 PR #4(`feat/ai-agent-backend-integration -> develop`)는 다음 상태다.

| 항목 | 값 |
|---|---|
| 상태 | OPEN, draft |
| 변경 규모 | 709 changed files, +159,211 / -2,145 lines |
| CI | `Agent Backend CI` 2회 SUCCESS |
| 제목 | `feat(ai): add agent chat integration and sanitized tracing` |

CI가 통과해도 이 규모는 사람이 정상 리뷰하기 어렵다. 사실상 "신뢰 기반 일괄 반입"이며,
문제가 생겼을 때 되돌리기 단위도 너무 크다.

권장:

1. 통째 병합을 선택하더라도 병합 직후 `38`번 merge smoke를 필수 gate로 고정한다.
2. PR 본문의 "팀 최소 계약"을 `develop/docs/team-collaboration/` 규칙으로 승격한다.
3. 이후 PR은 도메인 단위 수백 라인 규모로 제한하는 규칙을 명문화한다.
4. Agent는 OCR/DB/food/mobile 산출물을 소비하므로, 입력 측 브랜치를 먼저 안정화한 뒤 마지막에 병합한다.

### 4.2 develop 정체 — P0

로컬 원격 ref 기준 `origin/develop` 최신 커밋은 `2026-05-11` docs-only다. 반면 팀 브랜치들은
6월 초까지 병렬로 성장했다. 한 달간 팀 작업이 통합 지점 없이 자란 셈이다.

Agent 코드가 안전해도, OCR/DB migration/food nutrition 브랜치와 충돌하면 Agent 입력 계약
(`confirmed record`, `nutrient_code`, reviewed source readiness)이 깨질 수 있다. 지금 가장 먼저
잡아야 할 것은 새 모델이나 큰 리팩터링이 아니라 병합 순서와 계약 smoke다.

## 5. 인터페이스 및 모듈화 감사

### 5.1 잘 잡힌 seam

| seam | 현재 의미 | 긍정 판단 |
|---|---|---|
| `ChatTurnModule.plan()` | 한 Chat Turn의 intent, retrieval, answerability 결정 | LLM 호출 전 결정 경계가 분리되어 안전 정책을 고정하기 좋음 |
| `AnswerCard` / `AnswerCardNormalizer` | 검색된 reviewed evidence를 답변용 내부 프레임으로 표준화 | raw chunk나 FAQ card로 흐르지 않게 하는 핵심 interface |
| `MedicalKnowledgeRetriever` 계열 | seed/DB/MEDICAL-WIKI evidence를 카드로 공급 | adapter 교체가 가능하고 eval fixture 연결이 쉬움 |
| `CardAnswerRenderer` / `UnknownRenderer` / `BoundaryRenderer` | answerability별 출력 경로 분리 | fail-closed와 boundary UX를 독립 테스트하기 좋음 |
| `SafetyGuard` / `SafetyEnvelope` | 금지 표현, unsupported fact, numeric claim, trace 차단 | 의료 boundary의 마지막 출구 점검으로 적절함 |
| `AgentTraceSpan` / recorder / LangSmith exporter | raw-free 관측 이벤트 | 운영 관측을 agent core와 느슨하게 연결하는 방향이 좋음 |
| `UserHealthContextSnapshot` | 앱 context를 agent가 소비 가능한 형태로 축약 | raw app payload와 agent prompt를 분리하려는 방향이 맞음 |

### 5.2 모듈화 리스크

현재 라인 수는 `Get-Content.Count` 기준이다.

| 파일 | 현재 실측 | 위험 | 권장 조치 |
|---|---:|---|---|
| `knowledge.py` | 1,982 lines | 분류, source registry, seed knowledge, eval case가 한 파일에 몰림 | `classification`, `seed_registry`, `policy`, `eval_cases`로 단계적 분리 |
| `agents/chatbot.py` | 1,333 lines | LLM request, fallback, renderer routing, trace, slot sealing, context formatting 집중 | `llm_polish.py`, `prompt_builder.py`, `response_router.py` 후보 분리 |
| `renderers.py` | 658 lines | boundary/card/general rendering과 source wording이 함께 증가 | answerability별 renderer 파일 분리 |
| `user_health_context.py` | 794 lines | 앱 DB row folding 규칙이 한 파일에 집중 | table별 mapper 함수 테스트 강화 + adapter contract doc |
| `polish_slots.py` | 75 lines | 분리 착수 | 작은 helper 분리는 긍정적이나 큰 모듈 분리는 별도 PR 필요 |

판단: interface 방향은 맞지만 구현 파일의 locality가 약해지는 구간에 들어섰다. 지금은 큰
재작성보다 "병합 이후 안정기에서 behavior no-change tests를 먼저 고정하고 작은 모듈부터
옮기는" 방식이 안전하다.

## 6. 기술 부채 및 중복 코드

| 영역 | 상태 | 위험도 | 설명 |
|---|---|---:|---|
| legacy seed knowledge와 MEDICAL-WIKI adapter 공존 | 의도된 과도기 | 중간 | fallback/seed가 완전히 사라진 것이 아니므로 source precedence 규칙이 계속 필요 |
| answerability 문자열 중복 | 존재 | 중간 | `unknown_no_reviewed_source`, `medical_decision_boundary` 등이 여러 파일/테스트/문서에 반복 |
| source metadata formatting 중복 | 존재 | 중간 | source basis가 `ChatbotAgent`, `renderers`, API contract에 흩어짐 |
| raw-field denylist 중복 | 존재하지만 의도됨 | 낮음~중간 | 보안상 중복은 괜찮지만 drift 감시 필요 |
| local smoke와 문서 로그 의존 | 존재 | 중간 | CI가 생겼지만 live DB/SGLang/full corpus 검증은 여전히 수동 또는 opt-in 성격 |

우선 제거할 중복은 raw denylist가 아니라 answerability/source/warning code registry다. raw
denylist는 보안 방어선이므로 중복 자체보다 "공통 forbidden marker test"로 drift를 잡는 편이
낫다.

## 7. 테스트 자동화와 게이트

### 7.1 강한 부분

- `backend/ai_agent_chat/tests`에 Chat Turn, chatbot, renderer, safety, SGLang client,
  tracing, LangSmith exporter, MEDICAL-WIKI adapter 테스트가 존재한다.
- `Nutrition-backend/tests/integration/api/test_ai_agent_api.py`가 route-level contract를 검증한다.
- `eval_medical_wiki_chatbot.py`, `eval_medical_wiki_evidence_bundles.py`,
  `run_agent_llm_merge_smoke.py`가 deterministic/evidence/merge smoke 경로를 제공한다.
- `.github/workflows/agent-backend-ci.yml`이 agent package tests, route contract tests, no-LLM
  merge smoke, dry-run eval, ruff, compileall을 실행한다.
- manual `workflow_dispatch`로 opt-in live SGLang strict smoke를 실행할 수 있다.

### 7.2 약한 부분

- PostgreSQL `127.0.0.1:55432`, `RUN_POSTGRES_MIGRATION_SMOKE`, `TEST_DATABASE_URL` 기반
  DB migration smoke는 아직 자동 완료 상태가 아니다.
- MEDICAL-WIKI sibling corpus가 없는 CI에서는 eval을 skip한다. 이는 합리적이지만 local full
  eval requirement를 PR 설명에 계속 남겨야 한다.
- SGLang live smoke는 manual opt-in이다. 정기 regression monitor는 아직 없다.
- coverage fail-under는 설정되어 있지만 많은 실무 명령은 `--no-cov`를 쓴다.

### 7.3 PR마다 권장 gate

```powershell
python -X utf8 -m pytest -q --no-cov backend\ai_agent_chat\tests
python -X utf8 -m pytest -q --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py
python -X utf8 backend\scripts\run_agent_llm_merge_smoke.py --llm none
python -X utf8 backend\scripts\eval_medical_wiki_chatbot.py --as-of 2026-06-10 --dry-run
python -X utf8 backend\scripts\eval_medical_wiki_evidence_bundles.py --as-of 2026-06-10 --dry-run
python -m ruff check backend\ai_agent_chat\src backend\ai_agent_chat\tests backend\scripts
python -m compileall backend\ai_agent_chat\src backend\scripts
git diff --check
```

live gate:

```powershell
python backend\scripts\check_ai_agent_runtime_prereqs.py
python backend\scripts\run_agent_llm_merge_smoke.py --llm sglang --timeout 90 --require-answerable-llm
```

DB-backed gate는 R1에서 별도 완성해야 한다.

## 8. 성능 및 확장성 감사

| 후보 | 현재 위험 | 근거 | 권장 감시 |
|---|---:|---|---|
| in-process BM25-lite retrieval | 낮음~중간 | 현재 42 claim/94 EvidenceBundle 규모에서는 충분. claim/section이 커지면 선형 scan 부담 증가 | 500/1k/5k claim fixture latency benchmark |
| `ChatbotAgent` response path | 중간 | prompt build, renderer, safety, trace가 한 클래스 안에서 순차 실행 | per-span `latency_ms` 실제 기록/집계 |
| `UserHealthContextSnapshot` app record folding | 중간 | meal/supplement/analysis rows를 여러 mapping으로 조합 | row count cap, newest-first ordering, large payload fuzz test |
| SGLang live call | 중간 | answerable polish에만 사용하지만 모델 상향 시 latency가 바로 UX 문제로 드러남 | provider latency SLO, fallback rate, timeout warning dashboard |
| structured output JSON extraction | 낮음~중간 | formatting tolerance가 최근 fix 대상 | malformed output regression set 유지 |

성능상 지금 당장 막힌 병목은 보이지 않는다. 하지만 corpus와 app context가 커지면 가장 먼저
문제될 곳은 retrieval scan과 app context folding이다.

## 9. 보안/개인정보 감사

### 9.1 강점

- `raw_prompt`, `raw_ocr_text`, `raw_provider_payload`, `debug_trace`, token 계열 field를
  차단하려는 denylist가 여러 계층에 있다.
- API route는 client `user_id`를 그대로 신뢰하지 않고 authenticated owner subject를 사용하는
  흐름이 보인다.
- agent memory는 owner subject hash 기반 접근과 raw/internal field exclusion을 갖는다.
- LangSmith exporter는 opt-in이고, SDK/API key 부재나 production block이 chat flow를 깨지
  않게 설계되어 있다.
- unknown backlog와 source detail contract는 raw question/source raw text를 사용자 artifact에
  노출하지 않는 테스트가 있다.

### 9.2 남은 위험

| 위험 | 등급 | 설명 | 권장 조치 |
|---|---:|---|---|
| 개인정보 수명주기 | P1 | `raw_chat_archive` 보관 기간, 삭제 요청, 탈퇴 시 memory 파기, chat-derived health info 동의 근거가 미완성 | 정책 문서 + 삭제 flow 테스트 |
| LangSmith/cloud upload 승인 경계 | P1 | dry-run은 안전하지만 실제 업로드 정책/승인 절차는 운영 gate 필요 | `LANGSMITH_EXPORT_ENABLED` production block + 승인 runbook |
| 자동 보안 audit 부족 | P1 | detect-secrets는 있으나 dependency audit, SAST, Bandit/pip-audit 계열 자동화가 약함 | CI에 `pip-audit` 또는 equivalent, Bandit scoped run 추가 |
| app context adapter raw field drift | P1 | 새 DB column이 생기면 raw denylist 우회 가능 | common forbidden marker fixture + recursive sanitizer contract |
| source governance 확대 | P1 | LLM-WIKI 내용은 직접 runtime 사용 금지. reviewed source 승격 절차 유지 필요 | claim-level review metadata/golden test 없이는 runtime 미반영 |

## 10. 운영 모니터링 상태

현재 있는 것:

- `/health` endpoint.
- `check_ai_agent_runtime_prereqs.py`로 PostgreSQL, SGLang, Ollama, medical source readiness 확인.
- `smoke_ai_agent_server.py`와 `run_agent_llm_merge_smoke.py`.
- sanitized `AgentTraceSpan`, structured log recorder, optional LangSmith exporter.
- `build_runtime_metrics_report()`로 sanitized span만 집계해 request id, claim id, source id 없이
  운영 지표를 만든다.
- `StructuredLogRuntimeMetricsReporter`가 `agent_runtime_metrics` JSON log를 남기고,
  alert code가 있으면 `WARNING`, 없으면 `INFO`로 기록한다.
- unknown backlog report script.

부족한 것:

- 최근 24h/주간 집계, baseline 비교, dashboard target.
- Slack `#prod-alerts` 같은 실제 alert routing rule.
- MEDICAL-WIKI eval pass rate와 live smoke 결과를 정기적으로 저장/비교하는 workflow.
- trace sink, 보존 기간, 개인정보 정책.

현재 구현된 alert code:

- `answerability_unknown_rate_high`
- `llm_polish_fallback_rate_high`
- `retrieval_no_match_rate_high`
- `unsafe_polish_fallback_present`
- `source_stale_present`
- `p95_chat_latency_high`

## 11. 제품 기능 백로그 감사

37번 초기 감사는 hardening 중심으로 다음 PR을 잡았지만, 26번 제품 방향과 30번 TODO 기준으로는
아직 제품 기능 절반이 남아 있다.

남은 주요 PR:

| PR | 상태 | 제품 의미 |
|---|---|---|
| PR C | 미완료 | conversation memory compaction |
| PR D | 미완료 | chat-derived memory 경계, 공식 DB 자동수정 차단 |
| PR E | 미완료 | 음식/영양제 알고리즘 adapter 감사 |
| PR F/G | 미완료 | 스마트 생활관리 점수 contract, 오늘 분석 wording hardening |
| PR H/I | 미완료 | checklist planner, action approval contract |
| PR J | 미완료 | BoundaryPlan 설명형 renderer |
| PR K | 미완료 | reviewed evidence & RAG eval 승격 루프 |
| PR L | 미완료 | mobile response contract, source/CTA/approval 표시 |
| PR M | 미완료 | E2E golden 시나리오 |

따라서 hardening만 계속하면 제품 차별 기능이 밀린다. 40번 로드맵처럼 R1 DB/runtime 배선 뒤
R2 제품 기능 트랙을 병렬로 올리는 것이 맞다.

## 12. 콘텐츠/코퍼스 확장 감사

현재 MEDICAL-WIKI backend adapter는 42 claim / 84 boundary input / 94 EvidenceBundle fixture와
answerable section fixture 10개 수준에서 검증되어 있다. 이 수치는 "챗봇이 사용자 관점에서
10개 주제만 답한다"는 의미가 아니라, 현재 MEDICAL-WIKI answerable fixture가 10개라는 뜻이다.
하지만 운영 coverage가 충분하다는 뜻도 아니다.

필요한 운영 루프:

1. unknown backlog triage.
2. 공식 source 또는 검수 자료 확인.
3. claim/boundary/allowed wording/blocked wording 등록.
4. `AnswerCardNormalizer`와 retrieval 테스트.
5. golden test 추가.
6. runtime 반영.

주간 cadence와 담당이 없는 unknown backlog 도구는 coverage를 늘리지 못한다. 40번의 R3 루프를
실제 운영 항목으로 고정해야 한다.

## 13. 모델 전략 감사

현재 SGLang primary는 `Qwen/Qwen2.5-0.5B-Instruct`다. 이 모델은 구조 검증과 live smoke에는
충분하지만, 데모/운영 polish 품질 목표로는 부족할 가능성이 있다.

다만 모델 상향은 지금 당장 P0가 아니다. 병합/DB/제품 기능/golden을 먼저 고정한 뒤 다음
게이트를 통과해야 한다.

- boundary bypass 84/84 유지.
- slot mutation 0 또는 deterministic reattach로 사용자-facing 계약 유지.
- answerable 품질 golden에서 Qwen 상위 모델/Gemma 후보 비교.
- latency, VRAM, 운영 비용 기록.
- Ollama fallback의 운영 범위 명시.

## 14. Flutter/API 표시 계약 감사

backend API가 `sources[]`, `answerability`, CTA/approval 후보를 내보내도 Flutter가 모든 상태를
올바르게 보여주는지는 별개다. Day10 screen smoke는 있었지만, 아래 상태 매트릭스의 위젯/golden
검증은 아직 부족하다.

- `answerable`
- `answerable_with_caution`
- `unknown_no_reviewed_source`
- `medical_decision_boundary`
- `urgent_escalation`
- approval-required action preview
- source detail display
- error/fallback/loading

따라서 "Flutter 검증 없음"이 아니라 "전체 상태 매트릭스의 화면 회귀 검증이 부족"하다고
판정한다.

## 15. 갱신된 리스크 우선순위

| 우선순위 | 리스크 | 상태 | 다음 조치 |
|---:|---|---|---|
| P0 | develop 병합 정체 + PR #4 규모 | 미해결 | R0 병합 순서 합의, PR 본문 계약 승격, merge smoke 필수화 |
| P0 | 병합 직후 입력 계약 회귀 | 일부 방어 | confirmed record, migration, OCR/food field smoke |
| P1 | DB-backed runtime 미배선 | 미해결 | PostgreSQL test DB, migration smoke, DB logger/memory/backlog |
| P1 | 제품 기능 백로그 PR C~M | 미착수 다수 | R2 제품 기능 트랙으로 재배치 |
| P1 | 콘텐츠 확장 운영 루프 | 도구만 존재 | 주간 triage cadence와 승격 기준 지정 |
| P1 | 개인정보 수명주기 정책 | 미해결 | retention/delete/consent 문서 + 테스트 |
| P1 | Flutter 표시 계약 실검증 | 부분 | 상태 매트릭스 widget/golden 추가 |
| P1 | 운영 observability 잔여 | 부분 | dashboard, alert routing, retention |
| P1 | 모델 전략 | 구조 검증 완료 | R2/R5 품질 gate 이후 모델 비교 |
| P2 | 파일 비대화 | 증가 추세 | 병합 이후 behavior no-change 분리 PR |
| P2 | 성능 benchmark / 보안 audit 자동화 | 미해결 | benchmark, pip-audit/Bandit, audit script |
| P2 | streaming/session/rate limit | 미해결 | 모델 상향 또는 데모 전 P1 승격 후보 |

## 16. 다음 실행 순서

이 문서의 실행 순서는 40번 로드맵이 단일 기준이다. 요약하면 다음 순서가 맞다.

1. **R0 팀 병합 게이트**: develop 정체 해소, PR #4 병합 방식 결정, merge smoke 필수화.
2. **R1 DB/Runtime 배선**: PostgreSQL test DB, migration smoke, DB-backed logger/memory/backlog, app context live route.
3. **R2 제품 기능 완성**: memory compaction, 분석 점수, checklist/action approval, BoundaryPlan, mobile contract, E2E golden.
4. **R3 콘텐츠 확장 루프**: unknown backlog -> reviewed source/claim -> golden update 주간 cadence.
5. **R4 운영 품질**: dashboard, alert routing, retention, 보안 audit, benchmark, 모듈 분리.
6. **R5 데모/릴리스 게이트**: persona E2E, P0/urgent/unknown live safety rehearsal, latency/UX 확인.

## 17. 최종 판정

Lemon Aid Agent는 "처음 기획한 방향대로 가고 있는가?"라는 질문에는 예, 꽤 정확히 가고
있다고 답할 수 있다. 의료/영양/복약 답변을 LLM 일반 지식에 맡기지 않고, 검수 지식
안에서만 답하고, 없으면 unknown으로 닫는 핵심 방향은 구현과 테스트가 따라왔다.

하지만 "이제 운영 서비스로 안정적으로 굴릴 수 있는가?"라는 질문에는 아직 조건부다.
다음 병목은 모델 하나를 바꾸는 일이 아니라 운영 discipline이다. 특히 병합 정체와 PR #4
규모를 먼저 해결하지 않으면, 아무리 agent core가 안전해도 팀 통합 단계에서 입력 계약이
흔들릴 수 있다.

따라서 현재 판정은 다음과 같다.

- 핵심 Agent runtime: pre-production candidate.
- 팀 통합 상태: release block.
- 제품 기능 완성도: core safety는 강하지만 오케스트레이터 기능은 진행 중.
- 다음 최우선 작업: R0 병합 게이트와 R1 DB/runtime 배선.

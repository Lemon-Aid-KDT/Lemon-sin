# 36. MEDICAL-WIKI RAG 실행 계획

이 문서는 MEDICAL-WIKI reviewed claim / EvidenceBundle adapter 이후 작업을 이어가기 위한 실행 기준이다. 실제 구현 결과와 검증 로그는 [09-grounded-chatbot-implementation-log.md](./09-grounded-chatbot-implementation-log.md)에 축적하고, 이 문서는 다음 단계에서 무엇을 해야 하는지 판단하는 계획 원본으로 유지한다.

## 현재 상태

| Phase | 상태 | 기준 |
| --- | --- | --- |
| Phase 0. 25 claim / 50 boundary adapter | 완료 | `97c39a3 feat(ai): connect medical wiki reviewed claims` |
| Phase 1. EvidenceBundle backend adapter | 완료 | `d949368 feat(ai): consume medical wiki evidence bundles` |
| Phase 2. API source detail contract | 완료 | `/api/v1/ai-agent/chat` route-level source contract test 추가, public source detail 필터/중복 제거 |
| Phase 3. claim + section retrieval baseline | smoke 완료, baseline 유지 대상 | claim + section retrieval smoke 60/60 |
| Phase 4. reranker 실험 | 완료 | baseline vs boundary-claim-first A/B, contextual expansion rank, 실패 분류 taxonomy 기록 |
| Phase 5. LangChain / vector DB 실험 | 대기 | 현재 25 claim / 5 section으로 도입 조건 미충족. production/runtime 도입 금지 |
| Phase 6. SGLang polish 실험 | smoke 완료, 정책 유지 대상 | boundary는 LLM bypass, answerable은 deterministic draft polish only |

현재 feature branch 기준:

- 작업 브랜치: `feat/ai-agent-backend-integration`
- 통합 방식: `develop` 직접 push 금지, PR로 통합
- PR 기준: `feat/ai-agent-backend-integration -> develop`
- MEDICAL-WIKI 위치: workspace root sibling. backend repo 내부로 복사하지 않는다.
- 제외 대상: `mobile/flutter_app/chrome-shot-profile/`, `mobile/flutter_app/*.png`, workspace-root `MEDICAL-WIKI/manifest/backend_deterministic_eval_results.jsonl`

## 불변 원칙

- LangChain, vector DB, reranker, SGLang은 의료 판단 계층이 아니다.
- runtime 답변은 계속 `reviewed claim -> EvidenceBundle/AnswerCard -> renderer/LLM polish -> SafetyGuard` 흐름을 통과해야 한다.
- raw source chunk, raw retrieval rank, matched terms, debug trace, raw prompt, raw LLM response, provider payload, user health data는 사용자 답변 artifact나 indexable runtime artifact에 넣지 않는다.
- safety boundary는 retrieval result, reviewed section, LLM polish보다 항상 우선한다.
- corpus 없는 CI에서는 MEDICAL-WIKI-dependent test를 skip한다.
- `sources[]` 확장은 additive field만 허용한다. 기존 Flutter DTO를 깨지 않는다.

## Phase 0. Reviewed Claim Adapter 완료 기록

완료 기준:

- 25 reviewed claim / 50 boundary eval backend adapter 연결
- 50/50 deterministic eval pass
- `ai_agent_chat` tests pass
- mobile screenshot / chrome profile 미포함
- feature branch push 완료
- develop 대상 PR 반영

고정된 검증:

```powershell
python -X utf8 backend\scripts\eval_medical_wiki_chatbot.py --as-of 2026-06-09
python -X utf8 -m pytest -q --no-cov backend\ai_agent_chat\tests
python -m ruff check backend\ai_agent_chat\src\lemon_ai_agent\medical_wiki_claims.py backend\ai_agent_chat\src\lemon_ai_agent\answer_card.py backend\ai_agent_chat\src\lemon_ai_agent\chat_turn.py backend\ai_agent_chat\src\lemon_ai_agent\renderers.py backend\scripts\eval_medical_wiki_chatbot.py backend\ai_agent_chat\tests\test_medical_wiki_claim_adapter.py backend\Nutrition-backend\tests\unit\scripts\test_eval_medical_wiki_chatbot.py
```

## Phase 1. EvidenceBundle Backend Adapter 완료 기록

완료 기준:

- `MEDICAL-WIKI/manifest/evidence_bundle_adapter_fixtures.jsonl` 60개 backend 소비
- boundary fixture 50개는 LLM 호출 없이 deterministic
- answerable fixture 10개는 deterministic draft 기반
- forbidden marker hit 0
- `source_id` / `linked_claim_id` 유지
- raw retrieval/debug trace 미사용

고정된 검증:

```powershell
python -X utf8 -m pytest -q --no-cov backend\ai_agent_chat\tests\test_medical_wiki_evidence_bundle_adapter.py backend\Nutrition-backend\tests\unit\scripts\test_eval_medical_wiki_evidence_bundles.py
python -X utf8 backend\scripts\eval_medical_wiki_evidence_bundles.py --as-of 2026-06-09 --dry-run
```

## Phase 2. Backend API Source Detail Contract

목표:

- backend API 응답에서 MEDICAL-WIKI claim/section source metadata가 UI에서 쓸 수 있는 형태로 유지되는지 고정한다.

구현 작업:

1. `/api/v1/ai-agent/chat` route-level integration test를 추가한다.
2. boundary route를 검증한다.
   - expected claim `source_id` 포함
   - section source가 boundary claim을 덮지 않음
   - raw text, debug trace, retrieval rank 미포함
3. answerable route를 검증한다.
   - safety anchor claim source 포함
   - reviewed section source 포함
   - claim source와 section source 중복 제거
   - raw text, debug trace, provider payload 미포함
4. unknown route를 검증한다.
   - `sources=[]`
   - raw question 저장 없음
5. route test에 MEDICAL-WIKI fixture가 필요하면 corpus 없는 CI에서는 skip한다.
6. route injection seam이 없으면 test-only factory override 또는 기존 agent construction seam을 사용한다. production route가 MEDICAL-WIKI fixture에 직접 의존하게 만들지 않는다.

최소 source detail field:

- `source_id`
- `source_family`
- `review_status`
- `version_label`
- `reviewed_at`
- `expires_at`
- `source_url`

완료 기준:

- `/api/v1/ai-agent/chat` integration test pass
- Flutter DTO 호환성 유지
- `sources[]`는 additive field로만 확장
- source detail에 raw text/debug 없음

2026-06-09 실행 결과:

- route-level integration test 3개 추가.
  - boundary: claim source가 먼저 유지되고 section source가 boundary claim을 덮지 않음.
  - answerable: safety anchor claim source와 reviewed section source를 모두 유지하고 같은 `source_id` 중복을 제거함.
  - unknown: `sources=[]`이며 raw question이 응답과 backlog event에 남지 않음.
- `ChatbotApiResponse.sources`는 `source_id`, `source_family`, `review_status`, `version_label`, `reviewed_at`, `expires_at`, `source_url`, `boundary_code`만 공개한다.
- 검증:

```powershell
python -X utf8 -m pytest -q --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py::test_chat_route_medical_wiki_boundary_sources_are_public_and_claim_first backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py::test_chat_route_medical_wiki_answerable_sources_are_deduped_and_public backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py::test_chat_route_medical_wiki_unknown_sources_stay_empty_and_raw_free
```

결과: `3 passed, 1 warning`.

## Phase 3. Claim + Section Retrieval Baseline

목표:

- runtime 도입 전 claim-only와 claim+section retrieval을 비교 가능한 benchmark로 유지한다.

입력:

- `MEDICAL-WIKI/manifest/indexable_reviewed_claims.jsonl`
- `MEDICAL-WIKI/manifest/indexable_reviewed_sections.jsonl`
- `MEDICAL-WIKI/manifest/chatbot_answer_eval_inputs.jsonl`
- `MEDICAL-WIKI/manifest/answerable_eval_inputs.jsonl`

작업:

1. claim-only baseline을 유지한다.
   - boundary query 50/50 top-k claim 통과
2. claim+section baseline을 유지한다.
   - answerable query 10/10 expected section top-1
   - boundary query에서 section이 safety claim보다 우선하지 않음
3. 결과 파일은 실험 산출물로만 취급한다.
   - production runtime artifact 아님
   - PR 포함 여부는 별도 판단

검증:

```powershell
python -X utf8 MEDICAL-WIKI\tools\run_claim_section_retrieval_smoke.py --as-of 2026-06-09 --dry-run
python -X utf8 MEDICAL-WIKI\tools\run_evidence_bundle_normalizer_smoke.py --as-of 2026-06-09 --dry-run
```

완료 기준:

- claim + section retrieval smoke 60/60 pass
- boundary 50/50 top-k claim 유지
- answerable 10/10 expected section top-1
- EvidenceBundle normalizer 60/60 유지

## Phase 4. Reranker 실험

목표:

- corpus가 커질 때 safety claim이 reviewed section에 밀리지 않는 reranking 규칙을 검증한다.

기본 정책:

- hard boundary claim은 section보다 우선한다.
- `urgent_escalation`, `medical_decision_boundary`, `safety_boundary` claim이 top-k 밖으로 밀리면 실패다.
- reranker는 후보 순서만 바꾸고 answerability를 완화하지 않는다.
- runtime route에는 아직 연결하지 않는다.

작업 순서:

1. 현재 BM25-lite / keyword baseline을 저장한다.
2. contextual query expansion 적용 전후를 비교한다.
3. lightweight reranker를 추가 실험한다.
   - boundary claim boost
   - linked claim boost
   - reviewed section은 linked claim이 있을 때만 answerable 후보로 사용
   - stale/expired source 제외
4. 실패 케이스를 분류한다.
   - synonym 부족
   - claim/section overlap
   - disease context 누락
   - boundary red flag 누락
5. production 후보는 baseline보다 안전할 때만 문서화한다.

완료 기준:

- boundary claim top-k recall 하락 없음
- answerable section recall 개선 또는 동등
- 실패 케이스 문서화
- runtime 연결 없음

2026-06-09 실행 결과:

- `run_claim_section_retrieval_smoke.py`가 baseline score 정렬과 boundary-claim-first rerank 결과를 함께 기록한다.
- answerable query는 contextual expansion 전후 expected section rank를 기록한다.
- 실패 원인은 `synonym_or_context_gap`, `claim_section_overlap`, `boundary_red_flag_missed`, `boundary_priority_regression`, `unclassified_failure`로 분류한다.
- 현재 corpus dry-run 및 결과 파일 갱신 요약:
  - total 60/60 pass
  - answerable section top-1 10/10
  - boundary claim top-k 50/50
  - reranker preserved boundary claim 50/50
  - baseline 대비 boundary priority 개선 1건
  - failure category count `{}`
  - runtime route 연결 없음
- 검증:

```powershell
python -X utf8 -m unittest MEDICAL-WIKI\tools\test_claim_section_retrieval_smoke.py
python -X utf8 MEDICAL-WIKI\tools\run_claim_section_retrieval_smoke.py --as-of 2026-06-09 --dry-run
python -X utf8 MEDICAL-WIKI\tools\run_claim_section_retrieval_smoke.py --as-of 2026-06-09
```

## Phase 5. LangChain / Vector DB 실험

목표:

- LangChain/vector DB를 helper-only retrieval experiment로만 평가한다.

도입 조건:

- 최소 50 reviewed claim
- 100개 이상 golden/boundary+answerable eval
- 75-150 reviewed section 목표에 근접
- EvidenceBundle adapter 60/60 이상 유지

실험 원칙:

- LangChain `Document`는 `indexable_reviewed_claims`와 `indexable_reviewed_sections`만 사용한다.
- raw source chunking 금지.
- vector result는 prompt로 직접 전달 금지.
- vector result는 반드시 `EvidenceBundle -> AnswerCardNormalizer`를 통과해야 한다.
- production dependency 승격은 별도 결정으로 남긴다.

검증:

- vector retrieval top-k vs baseline 비교
- section explanation이 boundary claim을 넘지 않는지 확인
- stale/expired source 제외
- forbidden marker scan

완료 기준:

- vector DB가 safety gate를 우회하지 않음
- baseline보다 recall이 좋아지거나 운영 가치가 문서화됨
- production dependency 승격 여부가 별도 결정으로 남음

## Phase 6. SGLang Structured Output / Polish 실험

목표:

- SGLang은 답변 생성자가 아니라 deterministic draft polish 역할로만 평가한다.

Boundary eval:

- 50 boundary 질문은 계속 LLM bypass가 성공 조건이다.
- `--llm sglang`에서도 provider는 deterministic이어야 한다.

Answerable eval:

- deterministic `AnswerDraft` 생성
- SGLang은 문장 polish만 수행
- final output은 deterministic slot reattach
- LLM이 source, caution, boundary id를 바꿔도 final은 원 슬롯 유지

검증:

```powershell
python -X utf8 MEDICAL-WIKI\tools\run_answerable_normalizer_polish_smoke.py --mode draft --dry-run
python -X utf8 MEDICAL-WIKI\tools\run_answerable_normalizer_polish_smoke.py --mode polish --llm sglang --dry-run --timeout 60
python -X utf8 backend\scripts\eval_medical_wiki_chatbot.py --as-of 2026-06-09 --llm sglang --dry-run
```

완료 기준:

- boundary LLM bypass 50/50
- answerable final output unsafe directive 0
- final source/caution/boundary slots mutation 0
- unsafe polish는 deterministic fallback

## 항상 실행할 gate

작업 전:

```powershell
git -C ai-agent-backend-integration status --short --branch
git -C ai-agent-backend-integration diff --check
```

backend 최소 gate:

```powershell
python -X utf8 -m pytest -q --no-cov backend\ai_agent_chat\tests
python -m ruff check backend\ai_agent_chat\src backend\ai_agent_chat\tests backend\scripts
```

MEDICAL-WIKI full gate:

```powershell
python -X utf8 backend\scripts\eval_medical_wiki_chatbot.py --as-of 2026-06-09 --dry-run
python -X utf8 backend\scripts\eval_medical_wiki_evidence_bundles.py --as-of 2026-06-09 --dry-run
rg -n -i "raw prompt|raw llm response|raw ocr|provider payload|debug trace|base64 image|exif|api[_-]?key|secret|token" MEDICAL-WIKI\manifest\indexable_reviewed_claims.jsonl MEDICAL-WIKI\manifest\reviewed_claims.jsonl MEDICAL-WIKI\manifest\chatbot_answer_eval_inputs.jsonl MEDICAL-WIKI\manifest\evidence_bundle_adapter_fixtures.jsonl
```

PR hygiene:

- 명시 파일만 stage한다.
- mobile screenshot/profile artifact는 stage하지 않는다.
- `develop`에는 직접 push하지 않는다.
- GitHub PR comment에는 MEDICAL-WIKI sibling requirement, corpus 없는 CI skip, local full eval requirement, LangChain/vector DB/reranker/SGLang 미도입 여부, raw RAG가 아니라 reviewed claim/EvidenceBundle adapter임을 적는다.

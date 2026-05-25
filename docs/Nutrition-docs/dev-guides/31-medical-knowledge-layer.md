# dev-guides/31 - 의료 지식층 설계

> 단계: MVP 안전성 및 아키텍처 정렬
> 관련 runtime TODO: `docs/superpowers/plans/2026-05-22-mvp-runtime-and-medical-knowledge-todo.md`
> 문서 번호 상태: 사용자 승인으로 31번 확정. 기존 `29-final-deliverables-index.md`와
> `30-post-p1-execution-checklist.md`를 유지하고, 이 문서를 후속 의료 지식층 설계로 둔다.

## 1. 결정

현재 MVP에서는 만성질환 의료 사실을 LLM에 fine-tuning하지 않는다.

Lemon Aid의 현재 제품 경계는 건강관리 참고 코칭이다. assistant는 설명, 요약,
추가 질문, 전문가 상담 권장을 할 수 있다. 그러나 진단, 치료, 처방, 복약 변경,
질환 관리 결정의 최종 판단 주체처럼 표현하면 안 된다.

만성질환 지식은 외부에서 확인 가능하고 교체 가능한 계층으로 다룬다.

- 제품 핵심 판단은 deterministic backend rule이 담당한다.
- 응답 경계와 위험 표현 차단은 SafetyGuard가 담당한다.
- 의료, 영양, 영양제 관련 사실은 source-versioned knowledge record로 관리한다.
- 설명 가능한 context는 retrieval 또는 lookup으로 가져온다.
- 사용자별 만성질환 정보는 명시 동의와 profile context 뒤에만 사용한다.

## 2. 지금 fine-tuning을 하지 않는 이유

fine-tuning은 현재 MVP에서 의료 사실을 저장하기에 적절한 위치가 아니다.

| 위험 | 이유 |
| --- | --- |
| 최신성 | 의료·영양 기준은 바뀔 수 있고, model weight는 빠르게 수정하기 어렵다. |
| 추적성 | 사용자, 리뷰어, 개발자가 어떤 출처를 근거로 주의 문구가 나왔는지 확인할 수 있어야 한다. |
| 안전 경계 | fine-tuned model도 backend policy gate가 없으면 불확실한 사실을 단정할 수 있다. |
| 법무·검수 부담 | 만성질환 안내는 표현 검수, 출처 검수, 업데이트 책임자가 필요하다. |
| 테스트 가능성 | deterministic rule과 versioned data가 model 내부 기억보다 회귀 테스트하기 쉽다. |

나중에 fine-tuning을 검토하더라도 범위는 비사실 영역으로 제한한다.

- 한국어 제품 말투
- 카드형 응답 형식
- 안전한 거절과 escalation 문구
- 간결한 설명 스타일

fine-tuning을 질환 사실, 약물 규칙, 금기 로직, 복용량 결정, 치료 권고를 주입하는
용도로 사용하지 않는다.

## 3. 계층별 책임

| 계층 | 담당 | 담당하면 안 되는 것 |
| --- | --- | --- |
| LLM | 한국어 설명, 요약, 대화 말투, 질문 응답 형식 | 최종 의료 판단, 숨겨진 의료 사실 저장, 복약·치료 결정 |
| Deterministic backend | 영양 threshold, 만성질환 우선 확인 flag, 동의 확인, feature flag | 자유문 형태의 의료 조언 |
| Knowledge source | versioned fact, source URL, review date, jurisdiction, applicability note | context 없는 사용자별 판단 |
| SafetyGuard | 위험 표현 차단, fallback message, 진단·치료·처방 경계 | 1차 임상 지식 저장소 |
| RAG/lookup | 검토된 snippet과 metadata 검색 | live 사용자 응답에서 unreviewed web search 사용 |
| User profile/context | 동의된 만성질환·복약 context | 질환 상태를 조용히 추론하거나 확정 |

## 4. 데이터 모델 초안

사용자 응답에 retrieval을 연결하기 전에 source-versioned record 모델을 먼저 둔다.

```text
medical_knowledge_source
  id
  source_type              # guideline, public-health, paper, internal-review
  title
  publisher
  url
  published_at
  reviewed_at
  version_label
  jurisdiction
  owner
  status                   # draft, reviewed, deprecated

medical_knowledge_item
  id
  source_id
  topic                    # hypertension, diabetes, kidney-disease, supplement-interaction
  audience                 # adult, older-adult, pregnancy, chronic-condition
  claim_summary
  applicability_notes
  caution_level            # info, caution, urgent-professional-consult
  allowed_user_wording
  prohibited_wording
  last_reviewed_at
```

MVP에서는 JSON 또는 markdown table로 시작해 PR에서 검수해도 된다. DB table이나
vector index는 source governance가 안정된 뒤에 붙인다.

현재 1차 구현은 DB/RAG가 아니라 코드 registry다.

- `backend/ai_agent_chat/src/lemon_ai_agent/knowledge.py`
  - `REVIEWED_MEDICAL_SOURCE_REGISTRY`: KDCA, KDRIs, MFDS, Semantic Scholar의
    source id, source family, review status, owner, env key를 보관한다.
  - `LLM_QA_EVAL_SET`: chatbot policy가 다루는 230개 MVP Q&A 회귀 케이스를 보관한다.
- `backend/Nutrition-backend/src/config.py`
  - `KDCA_HEALTHINFO_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` 등 source API key를
    Settings 필드로 읽는다.
- `backend/Nutrition-backend/src/services/medical_source_readiness.py`
  - live API 호출 없이 source status, API key configured 여부, review expiry를
    검사한다.

주의: 위 구현은 source metadata와 설정 경계를 잡은 것이다. live API retrieval,
RAG index, stale-source 자동 갱신은 아직 켜지지 않았다.

API key 발급 후 첫 확인 순서:

1. repo root `.env`, `backend/.env` 또는 실행 환경에 `KDCA_HEALTHINFO_API_KEY`, `MFDS_DATA_API_KEY`,
   필요 시 `SEMANTIC_SCHOLAR_API_KEY`를 설정한다.
2. `python backend/scripts/check_ai_agent_runtime_prereqs.py`를 실행한다.
   특정 dotenv 파일을 지정하려면 `--env-file path\to\.env`를 붙인다.
3. `kdca-healthinfo`와 `mfds-drug-safety`는 `ok`가 되어야 한다.
4. `semantic-scholar`는 key가 있어도 `not_reviewed`로 남는 것이 정상이다.
   이 source는 research backlog이며 사용자-facing 답변에 직접 쓰지 않는다.
5. live retrieval 또는 RAG를 붙이기 전에는 source별 rate limit, 실패 시 fallback,
   review expiry 갱신 책임자를 별도 PR에서 정의한다.

## 5. 만성질환 profile 사용 원칙

사용자 만성질환 정보는 민감 건강 정보다.

규칙:

- 명시적 sensitive-health consent 이후에만 사용한다.
- 사용자가 입력한 context로 취급하고, 앱이 확정한 질환 상태로 취급하지 않는다.
- 제품 동작에 필요한 최소 category만 저장한다.
- 입력이 불완전하거나 self-reported일 때는 불확실성을 표현한다.
- 음식, 영양제, OCR, 활동, chat text에서 새로운 만성질환을 추론하지 않는다.
- 사용자에게 약물, 치료, 복용량을 시작·중단·변경하라고 말하지 않는다.

허용 표현:

- "현재 입력된 정보 기준으로 주의가 필요할 수 있습니다."
- "만성질환 또는 복약 중인 약이 있다면 전문가와 확인하는 편이 안전합니다."
- "이 내용은 건강관리 참고 정보이며 진료를 대체하지 않습니다."

금지 표현:

- "이 질환입니다."
- "이 치료를 하면 됩니다."
- "이 약을 중단하세요."
- "이 용량으로 복용하세요."
- "이 음식/영양제는 누구에게나 안전합니다."

## 6. 응답 조립 계약

만성질환 context가 포함된 응답은 아래 순서로 만든다.

1. Backend가 동의된 user context와 확인된 food/supplement/activity entry를 모은다.
2. Deterministic rule이 관련 caution category를 찾는다.
3. Knowledge lookup이 검토된 source summary와 metadata를 가져온다.
4. LLM은 새 사실을 추가하지 않고 한국어 제품 말투로 다시 쓴다.
5. SafetyGuard가 최종 문장의 위험 단정과 internal trace 누출을 검사한다.
6. API response는 user-facing card만 반환한다.

필수 사용자 표시 섹션:

- summary: 현재 입력에서 이해할 수 있는 내용
- caution: 추가 주의가 필요한 이유
- next action: 낮은 위험도의 자기관리 행동 또는 전문가 상담
- source note: 구체적 사실을 표시할 때 source family 또는 version

아래 내부 필드는 기본 UI에 노출하지 않는다.

- raw OCR text
- raw LLM prompt 또는 response
- policy guard 문자열
- debug trace
- unreviewed retrieval snippet
- internal risk score 이름

## 7. 지식 출처 등급

| 등급 | 사용처 | 예시 source family |
| --- | --- | --- |
| A | 검수 후 제품 핵심 기준에 사용 | 국가 영양 기준, regulator guidance, 검토된 clinical/public-health guidance |
| B | 검수 후 설명 보조에 사용 | public-health education page, peer-reviewed summary |
| C | 연구 backlog에만 사용 | 신규 논문, 실험, 미검수 팀 노트 |

Tier C 내용은 사용자-facing 답변에 직접 retrieval하지 않는다.

초기 규제·거버넌스 참고 자료:

- FDA Artificial Intelligence in Software as a Medical Device:
  https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-software-medical-device
- WHO Ethics and governance of artificial intelligence for health:
  https://www.who.int/publications/i/item/9789240029200
- WHO LMM ethics and governance guidance news release:
  https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models
- KDCA 국가건강정보포털 OpenAPI 신청:
  https://health.kdca.go.kr/healthinfo/biz/health/portalUseGuidance/openApiReqst/openApiReqstRegistNew.do
- Semantic Scholar Academic Graph API:
  https://api.semanticscholar.org/api-docs/

이 참고 자료가 Lemon Aid를 규제 대상 의료기기 제품으로 만든다는 뜻은 아니다.
MVP가 건강관리 참고 코칭 assistant 경계에 머무는 동안에도 risk management,
governance, transparency, lifecycle thinking을 명시하기 위한 기준으로 사용한다.

## 8. MVP 구현 순서

1. 현재 chatbot과 daily-coaching 출력은 건강관리 참고 코칭 경계 안에 둔다.
2. 만성질환 지식용 reviewed source registry file을 추가한다. [완료: 코드 registry 1차]
3. 가치가 큰 소수 케이스부터 deterministic caution mapping을 추가한다.
4. 만성질환 출력의 금지 표현 테스트를 추가한다.
5. UI 문구가 준비된 뒤 source metadata를 backend response와 Flutter chatbot card
   footer에 추가한다. [완료: `source_families` API 응답, Flutter DTO parsing,
   chatbot 화면 source family chip]
6. source record, review workflow, stale-source behavior가 정리된 뒤 RAG를 검토한다.
   [부분 완료: readiness가 expired review를 `source_stale`로 차단]
7. safety test가 안정된 뒤 tone 또는 format 목적의 fine-tuning만 검토한다.

## 9. 검증 체크리스트

- [x] 어떤 출력도 Lemon Aid가 진단, 치료, 처방, 복약 변경을 한다고 표현하지 않는다.
      `ai_agent_chat/tests/test_safety_guard.py`가 진단·치료·약 중단·복용량 변경
      지시형 표현을 `SafetyGuard`에서 차단하는지 검증한다.
- [x] 만성질환 context는 명시 동의 뒤에만 사용한다.
      `test_daily_coaching_requires_sensitive_health_consent`와
      `test_chat_route_requires_sensitive_health_consent`가 동의 없는 daily-coaching/chat
      호출을 `consent_required`로 차단하는지 검증한다.
- [x] user-provided disease status를 confirmed medical fact로 조용히 승격하지 않는다.
- [x] 의료 사실 source family는 reviewed source record와 연결된다.
- [x] source readiness는 missing key, draft source, expired review를 구분한다.
- [ ] LLM output은 retrieved 또는 deterministic context 밖의 unsupported fact를 추가하지 못한다.
      [부분 완료: chatbot prompt는 listed source family 없는 신규 건강 사실과 supplied
      context 밖 판단을 금지하고, daily-coaching prompt는 supplied findings/recommendations
      밖 판단을 금지한다. `SafetyGuard.check_grounding()`은 출력 후에도 "연구에 따르면",
      "임상시험", "입증", "혈압을 낮춥니다" 같은 근거·효과 주장이 grounding context에
      없으면 deterministic fallback으로 되돌린다. 전체 medical fact verification은
      RAG/live retrieval 연결 전 추가 게이트로 남긴다.]
- [x] LLM이 단정 표현을 만들면 SafetyGuard fallback을 사용한다.
- [x] UI는 raw trace, raw findings, internal policy string을 숨긴다.
- [x] fine-tuning backlog는 tone, structure, safe refusal pattern으로 제한한다.
      이 문서의 2장과 8장은 질환 사실, 약물 규칙, 금기 로직, 복용량 결정, 치료 권고를
      fine-tuning 대상에서 제외하고 tone/format 목적만 검토하도록 제한한다.

## 10. 남은 결정 사항

- reviewed source record의 첫 만성질환 topic은 KDCA 고혈압/당뇨/신장질환 맥락으로 시작한다.
- source review와 expiry check 책임자를 정한다.
- chatbot card footer에는 source family chip을 표시한다.
  [완료: backend `/api/v1/ai-agent/chat` 응답은 `source_families`를 포함하고,
  Flutter `ChatbotResponse`가 이를 파싱하며 채팅 화면에 영양 기준/영양제 참고 등
  한국어 source family chip으로 표시한다. 구체 source record detail sheet는 RAG/live
  retrieval 적용 뒤 별도 UX로 검토한다.]
- chatbot과 daily-coaching snapshot에 금지 표현 자동 검사를 추가한다.
  [완료: chatbot LLM 출력, daily-coaching adapter/Flutter contract, `SafetyGuard`
  회귀 테스트에서 raw trace, 위험 단정 표현, 약 중단·복용량 변경 지시를 차단한다.]
- production-like response에 RAG index를 연결하기 전에 live retrieval 실패, rate limit,
  stale-source 자동 갱신 정책을 정의한다.

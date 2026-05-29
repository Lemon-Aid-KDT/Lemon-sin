# 09. 근거 기반 동적 답변 카드 챗봇 구현 로그

> Status: implementation log
> 작성일: 2026-05-29
> 기준 브랜치: `feat/ai-agent-backend-integration`
> PRD: [05-grounded-chatbot-prd.md](./05-grounded-chatbot-prd.md)
> TDD: [06-grounded-chatbot-tdd.md](./06-grounded-chatbot-tdd.md)
> TODO: [07-grounded-chatbot-todo.md](./07-grounded-chatbot-todo.md)
> TRD: [08-grounded-chatbot-trd.md](./08-grounded-chatbot-trd.md)

## 1. 구현 목적

이번 작업은 수동 카드 몇 개에 의존하는 챗봇에서 벗어나, 모든 건강 답변이 검수 지식
기반 `AnswerCard` 또는 boundary/unknown renderer를 통과하도록 첫 runtime 구현을
연결하는 작업이다.

핵심 구현 목표:

- `AnswerCard` 표준 타입 추가
- reviewed seed knowledge를 `AnswerCard`로 정규화
- 질문별 reviewed card retrieval
- reviewed card가 없으면 `unknown_no_reviewed_source`로 fail-closed
- LLM prompt와 deterministic fallback이 카드 기반 grounding을 사용
- API response에 `answerability`와 reviewed source metadata 추가
- production chat route에서 reviewed source governance DB 미준비 시 fail-closed
- 작업 내용을 테스트와 문서로 남김

## 2. 주요 변경

### 2.1 AnswerCard 계층 추가

추가 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/answer_card.py`
- `backend/ai_agent_chat/tests/test_answer_card_normalizer.py`

구현 내용:

- `Answerability` 타입 추가
  - `answerable`
  - `answerable_with_caution`
  - `needs_more_info`
  - `unknown_no_reviewed_source`
  - `medical_decision_boundary`
  - `urgent_escalation`
- `AnswerCard` dataclass 추가
- `KnowledgeRetrievalResult` dataclass 추가
- `AnswerCardNormalizer` 추가
- `MedicalKnowledgeRetriever` 추가
- draft, paper candidate, user-facing 불가 source를 카드로 만들지 않도록 차단
- 약/영양제 병용 caution 질문에서 무관한 범용 카드를 끌어오지 않도록 relevance filter 추가

### 2.2 ChatTurnModule 재배선

변경 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/chat_turn.py`
- `backend/ai_agent_chat/tests/test_chat_turn.py`

구현 내용:

- `ChatTurnPlan`에 아래 필드 추가
  - `answer_cards`
  - `answerability`
  - `retrieval_status`
  - `retrieval_warnings`
  - `sources`
- `requires_boundary_response`를 기존 category 기반에서 answerability 기반으로 변경
- unsupported 질문은 `unknown_no_reviewed_source`로 내려가도록 테스트 추가

### 2.3 reviewed seed card 보강

변경 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/knowledge.py`

구현 내용:

- `ChatIntentAnalysis.normalized_question` 추가
- 일반 건강기록 점검용 reviewed seed card 추가
  - `general_health_record_review`
- 일반 영양제 라벨 점검용 reviewed seed card 추가
  - `supplement_label_check`
- 기존 마그네슘/나트륨/당뇨/고혈압/신장질환 seed card는 `AnswerCard`로 변환되는
  grounding source로 사용

주의:

- 이번 작업의 seed card 추가는 coverage mechanism 확장이 아니라, `AnswerCard` adapter와
  fallback 경로를 검증하기 위한 v1 reviewed seed다.
- 새 topic coverage는 앞으로 source/evidence update와 retriever/normalizer 테스트를 통해
  확장해야 한다.

### 2.4 ChatbotAgent card-only/unknown 흐름

변경 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/agents/chatbot.py`
- `backend/ai_agent_chat/tests/test_chatbot_agent.py`

구현 내용:

- `unknown_no_reviewed_source`이면 LLM을 호출하지 않고 deterministic unknown 응답 반환
- LLM prompt의 reviewed grounding을 `AnswerCard` summary로 전환
- LLM system rule에 "provided reviewed answer cards만 factual grounding으로 사용" 규칙 추가
- LLM 출력 후 `must_not_say` phrase 검사 추가
- 성공/실패/fallback 응답에 `answerability`와 `sources` metadata 포함
- 마그네슘+혈압약 질문은 `answerable_with_caution`으로 유지
- 리튬+셀레늄처럼 reviewed card가 없는 병용 질문은 unknown으로 fail-closed

### 2.5 SafetyGuard 보강

변경 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/guards/safety.py`
- `backend/ai_agent_chat/tests/test_safety_guard.py`

구현 내용:

- `check_forbidden_phrases()` 추가
- AnswerCard의 `must_not_say` 표현이 LLM 출력에 나오면 fallback할 수 있게 연결
- 기존 금지 표현, unsupported fact, unsupported numeric claim 검증 유지

### 2.6 API 응답 계약 확장

변경 파일:

- `backend/ai_agent_chat/src/lemon_ai_agent/chat_session.py`
- `backend/Nutrition-backend/src/api/v1/ai_agent.py`
- `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`

구현 내용:

- `ChatbotResponse`에 `answerability`, `sources` 추가
- `ChatbotApiResponse`에 `answerability`, `sources` 추가
- `/api/v1/ai-agent/chat` route가 additive response field를 내려주도록 변경
- magnesium caution route test가 `answerability=answerable_with_caution`과 source metadata를 검증
- unknown route test가 LLM 미호출, `unknown_no_reviewed_source`, `sources=[]`를 검증

### 2.7 production source governance fail-closed

변경 파일:

- `backend/Nutrition-backend/src/api/v1/ai_agent.py`
- `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`

구현 내용:

- `_production_medical_source_gate()` 추가
- `settings.environment == "production"`이면 `build_medical_source_readiness_from_db()`를
  통해 DB-backed reviewed source readiness를 확인
- production에서 reviewed source governance가 준비되지 않으면 LLM client를 만들지 않고
  `unknown_no_reviewed_source` 응답 반환
- local/dev에서는 기존 registry-backed chatbot path 유지

## 3. 추가한 테스트

새 테스트 파일:

- `backend/ai_agent_chat/tests/test_answer_card_normalizer.py`

보강한 테스트:

- `backend/ai_agent_chat/tests/test_chat_turn.py`
- `backend/ai_agent_chat/tests/test_chatbot_agent.py`
- `backend/ai_agent_chat/tests/test_safety_guard.py`
- `backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py`

주요 검증:

- reviewed seed item -> `AnswerCard`
- draft/paper candidate item -> card 생성 거부
- 무관한 병용 질문 -> `no_match`
- 마그네슘+혈압약 -> reviewed caution card
- unsupported 질문 -> LLM 미호출 unknown 응답
- API response -> `answerability`, `sources`
- production source readiness 실패 -> LLM 미호출 fail-closed
- `must_not_say` phrase 차단

## 4. 실행한 검증

```powershell
python -m pytest -q --no-cov backend/ai_agent_chat/tests
```

결과:

```text
79 passed, 1 skipped
```

```powershell
python -m pytest -q --no-cov backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py
```

결과:

```text
15 passed, 1 warning
```

```powershell
python -m compileall backend/ai_agent_chat/src backend/Nutrition-backend/src/api/v1/ai_agent.py
```

결과:

```text
success
```

```powershell
python -m ruff check backend/ai_agent_chat/src backend/ai_agent_chat/tests backend/Nutrition-backend/src/api/v1/ai_agent.py backend/Nutrition-backend/tests/integration/api/test_ai_agent_api.py
```

결과:

```text
All checks passed!
```

## 5. 완료된 TODO 범위

이번 작업에서 완료한 범위:

- Phase 1: answerability, AnswerCard, unknown, API contract 테스트 추가
- Phase 2: `MedicalKnowledgeItem` -> `AnswerCard` seed adapter 구현
- Phase 3: AnswerCard normalizer 구현
- Phase 4: registry-backed retriever 구현
- Phase 5: ChatTurnModule answerability/card 기반 재배선
- Phase 6: ChatbotAgent unknown/card grounding 흐름 연결
- Phase 7: SafetyGuard `must_not_say` 검사 추가
- Phase 8: API response contract에 `answerability`, `sources` 추가
- Phase 9 일부: production chat route의 DB-backed source readiness fail-closed gate 연결
- Phase 10 일부: magnesium, unknown, emergency, P0, lab boundary, sodium golden behavior 유지/확장
- Phase 11: 지정된 테스트, compileall, ruff 검증 통과

## 6. 남은 후속 범위

이번 작업에서 일부러 남긴 범위:

- 실제 `medical_evidence_items` DB row를 읽어 `AnswerCard`로 변환하는 DB retriever
- `medical_rag_chunks` 또는 vector index 연결
- source owner/reviewer workflow UI 또는 admin seed
- KDRIs `approved -> reviewed` adapter 세부 연결
- Flutter UI에서 `sources[]` detail sheet 표시
- `needs_more_info` 상태의 별도 renderer 세분화

남긴 이유:

- PRD와 TDD가 정한 v1 순서는 먼저 reviewed seed/registry 기반 `AnswerCard` 계약과
  fail-closed behavior를 고정한 뒤, DB evidence/RAG를 별도 PR로 붙이는 것이다.
- RAG/vector DB는 답변 품질 보강 계층이며 safety boundary를 대체하지 않는다.

## 7. 완료 판정

이번 구현으로 현재 runtime은 다음 조건을 만족한다.

- 건강 답변 경로가 `AnswerCard`, boundary renderer, unknown renderer 중 하나를 사용한다.
- reviewed card가 없는 unsupported 병용 질문은 LLM으로 넘어가지 않는다.
- P0, 응급, 검사수치 치료 판단은 LLM을 호출하지 않는다.
- `/api/v1/ai-agent/chat`가 `answerability`와 reviewed source metadata를 내려준다.
- production 환경에서는 reviewed source governance DB readiness 실패 시 fail-closed한다.
- 테스트와 문서가 같은 answerability/source/safety 용어를 사용한다.

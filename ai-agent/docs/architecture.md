# AI Agent 아키텍처

## 목표

Agent 시스템은 정확히 확보된 음식과 영양제 섭취 데이터를 실제 건강관리 코칭으로
바꿉니다.

사용자에게 제공해야 할 결과는 다음과 같습니다.

- 식사에서 줄이면 좋은 부분
- 음식으로 먼저 보완하면 좋은 부분
- 음식 섭취가 어렵다면 검토할 수 있는 영양 성분
- 실천을 돕는 영양제 알림 또는 오늘의 작은 미션

단, Agent는 진단, 치료, 처방, 효과 보장을 해서는 안 됩니다. Lemon Aid의
판단은 건강관리 참고와 실천 보조에 머물러야 합니다.

## 구성 요소

### Intake Agent

OCR 결과와 앱에서 들어온 구조화 입력을 하루 섭취 기록으로 정규화합니다.

상용 버전에서는 원본 출처, OCR 결과, 사용자 승인 상태를 보존해야 합니다. 이
작업 공간도 `IntakeSource`를 통해 이미지 ID, 원본 OCR 문자열, 사용자 확인
여부를 결과에 남깁니다. 다만 OCR이 제품명, 성분, 함량 데이터를 이미 정확히
제공했다고 가정합니다.

OCR source가 아직 승인되지 않은 경우에는 `approval_status="requires_confirmation"`
상태의 preview-only 결과를 반환합니다. 이 상태에서는 findings, recommendations,
actions를 만들지 않습니다. 승인 후 다시 실행해야 deterministic engine 평가와
액션 제안이 진행됩니다.

### Nutrition Engine

음식과 영양제의 영양소를 결정론적으로 합산합니다. 이후 기준 섭취량과 상한량을
비교해 영양소별 부족, 적정, 과다, 위험 가능성을 계산합니다.

이 엔진은 LLM이 아니라 코드로 동작합니다. 따라서 영양소 계산과 기준 비교의
권위는 LLM이 아니라 이 엔진과 공식 기준 데이터에 있습니다.

현재 구현은 최소 정규화만 수행합니다. 영양소 이름은 lowercase/trim과 일부 alias
map을 적용하고, 단위는 `g/mg/mcg`와 비타민 D `IU -> mcg` 변환을 지원합니다.
OCR confidence, 성분명 전체 alias, 원문-정규화 매핑, 사용자 수정 반영은 실제
OCR/DB 통합 단계에서 확장해야 합니다.

### Supplement Engine

영양제 성분, 1회 섭취량, 일일 섭취 횟수를 사용해 성분별 일일 총량을 계산합니다.
제품명은 trace와 출처 확인 용도로만 보존하며, MVP 코칭은 특정 제품 추천이 아니라
성분 단위 제안으로 제한합니다.

### Health Trend Engine

최근 건강 흐름을 요약합니다. 예를 들면 식단 점수 흐름, 체중 흐름, 활동량 흐름,
향후 혈당 흐름 같은 데이터를 다룰 수 있습니다.

현재 MVP에서는 혈당과 CGM을 구현하지 않습니다. 대신 추세 입력을 범용 구조로
두어 이후 혈당, CGM, 체중, 활동량, 식단 점수를 같은 방식으로 확장할 수 있게
합니다.

### Personalization Agent

사용자 프로필, 목표, 만성질환, 복약 정보, 건강 흐름 요약을 코칭 제약 조건으로
바꿉니다.

이 Agent는 임상 규칙을 스스로 만들어서는 안 됩니다. 질환과 복약 정보는
"주의가 필요할 수 있음", "전문가 상담 권장" 같은 안전한 코칭 제약으로만
사용합니다.

### Coaching Agent

Nutrition Engine의 판단과 Personalization Agent의 제약 조건을 바탕으로 사용자
화면에 보여줄 코칭을 만듭니다.

코칭 우선순위는 다음과 같습니다.

1. 과다한 섭취 패턴을 줄이도록 제안합니다.
2. 부족한 영양소는 음식으로 먼저 보완하도록 제안합니다.
3. 음식 섭취가 어렵다면 성분 단위의 영양제 검토를 제안합니다.
4. 필요하면 알림이나 작은 일일 미션을 제안합니다.

MVP에서는 특정 제품 추천이 아니라 성분 중심 제안만 허용합니다.

### Risk & Policy Guard

진단, 처방, 치료 효과 보장, 약물 복용 단정, 특정 제품 구매 유도, 직접적인
의약품 추천 표현을 차단합니다.

또한 MVP에서는 영양제 제안이 특정 제품이 아니라 성분 수준에 머물도록 막습니다.
recommendation 문구뿐 아니라 trace line도 사용자 노출 전 검사합니다. 위험 문구가
있는 trace line은 원문을 숨기고 policy guard 차단 문구로 대체합니다.

### Action Agent

영양제 알림, 일일 미션 같은 액션을 준비합니다. 이 Agent는 어떤 액션도 사용자
명시 승인 없이 실행하지 않습니다.

### Chat Agent

"왜 이렇게 추천했어?" 같은 질문에 답합니다. 답변은 `DailyCoachingResult`의
findings, recommendations, actions, safety warnings, trace를 근거로만 만들며
새로운 건강 판단을 생성하지 않습니다.

LLM client가 없으면 trace 기반 deterministic template로 답합니다. LLM client가
주입되면 다음 최소 정보만 prompt에 포함합니다.

- date
- 상위 findings
- 상위 recommendations
- trace 요약

원본 이미지, 전체 OCR 원문, 실제 개인 식별 정보, 시크릿은 prompt에 넣지
않습니다. LLM 응답은 `SafetyGuard.check_text()`를 통과한 뒤에만 사용자에게
노출합니다. LLM 호출 실패, timeout, 안전 검사 실패 시 기존 deterministic fallback
답변을 반환하며 건강 판단 결과는 바꾸지 않습니다.

fallback 답변과 LLM prompt에 들어가는 trace는 모두 sanitized trace를 사용합니다.
trace sanitization warning은 테스트에서 확인 가능한 내부 상태 또는 결과 warning에
남깁니다.

### LLM Adapter

Chat Agent 뒤에는 `LocalLLMClient` Protocol을 둡니다.

```text
ChatAgent
-> LocalLLMClient
   -> FakeLLMClient
   -> OllamaClient
   -> OpenAICompatibleClient
-> SafetyGuard
-> 사용자 답변
```

- `FakeLLMClient`: 테스트용 provider입니다. 네트워크 호출 없이 고정 응답을
  반환합니다.
- `OllamaClient`: 로컬 개발용 provider입니다. 기본 endpoint는
  `http://127.0.0.1:11434`이고 `/api/chat`을 호출합니다. 공식 문서:
  [Ollama Chat API](https://docs.ollama.com/api/chat).
- `OpenAICompatibleClient`: vLLM 등 운영 후보 provider입니다. 기본 endpoint는
  `http://127.0.0.1:8000/v1`이고 `/chat/completions`를 호출합니다. 공식 문서:
  [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/),
  [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create).

Provider 선택은 앱 통합 시점의 설정 주입 문제로 분리합니다. 이번 단계에서는
`.env` 로딩 라이브러리를 추가하지 않습니다.

LLM runtime, OpenAI-compatible endpoint, 모델 serving 방식처럼 공식 문서가 있는
기술을 변경할 때는 해당 공식 문서를 먼저 확인하고, 아키텍처 문서나 결정 기록에
공식 URL을 남깁니다.

## LLM 전략

제품 방향은 서버에서 운영하는 AI입니다. 민감한 건강정보를 다루므로 외부 LLM API
키를 기본 경로로 두지 않습니다. Agent 계층 뒤에 자사 운영 또는 self-hosted
모델을 붙일 수 있도록 모델 provider 경계를 유지해야 합니다.

영양 계산, 건강 흐름 집계, 정책 판단의 최종 권위는 결정론적 엔진에 있습니다.
LLM은 구조화, 설명, 문장화, 코칭 표현 보조 역할을 맡습니다.

기존 `changmin-plan` 가이드의 `AgentInput`/`AgentOutput`, `agent_runs`,
`agent_memory` 계약은 FastAPI/DB 통합용 adapter에서 맞춥니다. 이 작업 공간의
`DailyHealthAgent`는 Health Agent 내부 deterministic 결과 모델로 유지합니다.

## 앱 통합 Adapter

`DailyHealthAgentAppAdapter`는 앱 계약과 내부 Agent 모델 사이의 얇은 경계입니다.

```text
FastAPI route 또는 app service
-> AgentInput
-> DailyHealthAgentAppAdapter
   -> DailyHealthAgent
   -> ChatAgent
   -> SafetyGuard
-> AgentOutput
-> agent_runs / agent_memory 연결점
```

adapter는 Pydantic `AgentInput`을 받아 내부 dataclass 입력으로 변환하고,
`DailyCoachingResult`를 Pydantic `AgentOutput`으로 변환합니다. 이때
`request_id`, `agent_name`, `used_tools`, `latency_ms`, `cost_usd`, `provider`를
채워 앱 로깅 계약과 맞춥니다.
Pydantic 계약은 공식 문서의
[Models](https://docs.pydantic.dev/latest/concepts/models/)와
[Fields](https://docs.pydantic.dev/latest/concepts/fields/)를 기준으로 유지합니다.

미승인 OCR source가 있으면 `status="preview"`와
`approval_status="requires_confirmation"`을 반환하고, findings/recommendations/actions는
비워 둡니다. 승인된 payload가 들어오면 deterministic engine을 다시 실행해
`status="completed"` 결과를 만듭니다.

trace는 기본 응답에 노출하지 않습니다. `include_debug_trace=True`일 때도 이미
`SafetyGuard`를 통과한 sanitized trace만 들어갑니다. 실제 DB 저장은 adapter의
`AgentRunLogger`와 `AgentMemoryWriter` Protocol 뒤에서 backend 모듈이 담당합니다.

## 검증 기준

현재 테스트는 다음 시나리오를 최소 기준으로 둡니다.

- 고나트륨 식사와 고혈압 맥락에서 상한량 초과를 위험 가능성으로 분류
- 단백질, 식이섬유, 비타민 D 부족에서 음식 우선 제안 생성
- 마그네슘, 철분, 칼슘 상한량 초과 처리
- 복약/질환 맥락에서 단정 표현 대신 전문가 검토 권장
- 특정 제품 구매 유도 문구 차단
- 향후 혈당 흐름 입력이 들어와도 진단 없이 최근 흐름 주의로만 설명
- 미승인 OCR source는 preview-only 결과로 멈추고 액션을 만들지 않음
- unsafe trace 원문이 fallback 답변이나 LLM prompt에 노출되지 않음
- 비타민 D alias와 `IU -> mcg` 단위 변환이 합산에 반영됨
- 앱 adapter가 `AgentInput`/`AgentOutput` mapping, preview/confirmed 상태,
  logging hook, memory hook, debug trace 제한을 지킴

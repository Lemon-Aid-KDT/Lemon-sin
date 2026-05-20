# Lemon Aid AI Agent

음식과 영양제 OCR로 확보한 신뢰 가능한 섭취 데이터를 건강관리 코칭으로
바꾸기 위한 서버 기반 AI Agent 작업 공간입니다.

이 패키지는 현재 앱 코드와 의도적으로 분리되어 있습니다. 먼저 상용화를 염두에 둔
AI Agent 경계를 작게 세우고, 이후 기존 Flutter/FastAPI 앱에 통합할 수 있게
만드는 것이 목적입니다.

현재 정의한 1차 경계는 다음과 같습니다.

- OCR 결과 기반 섭취 데이터 정규화
- 음식과 영양제 영양소 합산
- 영양제 성분별 일일 총량 계산
- 최근 건강 흐름 해석
- 사용자별 개인화 코칭
- 안전 표현 필터링
- 계산 trace 기반 설명 응답
- 사용자 승인 기반 액션 제안

## 제품 방향

Lemon Aid는 일반 챗봇이 아닙니다. Agent 시스템은 구조화된 섭취 데이터, 공식
영양 기준, 사용자 맥락, 안전 정책을 함께 사용해야 합니다. LLM은 이 흐름 안에서
문장을 정리하고 설명을 돕는 보조 엔진이지, 건강 판단의 단독 근거가 아닙니다.

MVP에서는 혈당과 CGM 연동을 제외합니다. 다만 스키마에는 범용 `health_trends`
입력을 남겨 두어, 이후 혈당과 유사한 건강 지표 흐름을 Agent 인터페이스 변경
없이 추가할 수 있게 합니다.

## 실행 흐름

```text
OCR 음식/영양제 결과
-> Intake Agent
-> Nutrition Engine
-> Supplement Engine
-> Health Trend Engine
-> Personalization Agent
-> Coaching Agent
-> Safety Guard
-> Action Agent
-> Chat Agent
-> 사용자 미리보기 및 승인
```

모든 결과는 원본 입력 출처, 사용자 확인 여부, 계산 trace를 보존합니다. Chat
Agent는 새 판단을 만들지 않고 이미 계산된 결과와 trace를 설명하는 역할만
맡습니다.

OCR 출처가 있고 아직 사용자가 확인하지 않은 입력은 preview-only 상태로 멈춥니다.
이 경우 `DailyCoachingResult.approval_status`는 `requires_confirmation`이며,
findings, recommendations, actions는 생성하지 않습니다. 승인된 OCR 또는 수동
mock 입력만 deterministic engine 평가로 넘어갑니다.

## Local LLM 전략

건강 판단은 `Nutrition Engine`, `Supplement Engine`, `Personalization Agent`,
`Coaching Agent`, `Safety Guard`가 결정론적으로 수행합니다. LLM은
`DailyCoachingResult`의 findings, recommendations, trace를 사용해 설명 문장을
정리하는 레이어로만 사용합니다.

Provider는 생성자 주입으로 선택합니다.

- 테스트 기본값: `FakeLLMClient`를 사용하며 네트워크를 호출하지 않습니다.
- 로컬 개발 기본 후보: `OllamaClient`로 `http://127.0.0.1:11434`의 Ollama
  `/api/chat` 엔드포인트를 호출합니다. 참고:
  [Ollama Chat API](https://docs.ollama.com/api/chat).
- 운영 후보: `SGLangClient`로 로컬/자가호스팅 SGLang의 `/v1/chat/completions`
  호환 서버를 호출합니다. vLLM은 같은 API 형태의 대체 backend로만 남깁니다. 참고:
  [SGLang GitHub](https://github.com/sgl-project/sglang),
  [SGLang Structured Outputs](https://docs.sglang.io/docs/advanced_features/structured_outputs),
  [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/),
  [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create).

외부 런타임이나 OpenAI-compatible API를 바꿀 때는 블로그나 2차 자료보다 공식
문서를 먼저 확인하고, 문서에는 해당 공식 URL을 함께 남깁니다.

예시:

```python
from lemon_ai_agent.agents.chat import ChatAgent
from lemon_ai_agent.llm import OllamaClient

chat_agent = ChatAgent(llm_client=OllamaClient(model="qwen2.5:7b-instruct"))
```

LLM 응답은 사용자에게 노출되기 전에 항상 `SafetyGuard`를 통과해야 합니다.
안전 검사를 통과하지 못하거나 로컬 LLM 연결이 실패하면 Chat Agent는 trace 기반
deterministic fallback 답변을 반환합니다. 이번 단계에서는 `.env` 로딩이나 모델
다운로드 자동화는 포함하지 않습니다.

trace도 사용자에게 보일 수 있으므로 출력 전 `SafetyGuard`를 통과합니다. 위험
표현이 포함된 trace line은 원문 대신 `trace item withheld by policy guard`로
대체합니다.

영양소 합산은 최소 정규화를 수행합니다. 현재는 이름 대소문자와 `비타민D` alias,
`g/mg/mcg` 변환, 비타민 D `IU -> mcg` 변환을 지원합니다. OCR confidence,
원문-정규화 매핑, 사용자 수정 반영, 전체 식약처 DB alias는 후속 통합 범위입니다.

## 앱 통합 Adapter

`DailyHealthAgent` 내부 모델은 dataclass로 유지하고, 앱 계약은
`DailyHealthAgentAppAdapter`가 Pydantic `AgentInput`/`AgentOutput`으로 맞춥니다.
Pydantic 모델/필드 사용은
[Pydantic 공식 문서](https://docs.pydantic.dev/latest/concepts/models/)와
[Fields 문서](https://docs.pydantic.dev/latest/concepts/fields/)를 기준으로 합니다.

adapter가 담당하는 일은 다음과 같습니다.

- `AgentInput.user_id`, `payload`, `context`를 `UserProfile`, `DailyIntake`,
  `HealthTrend`, `ReferenceRange`로 변환
- `DailyCoachingResult`를 앱 응답용 findings, recommendations, actions, message로
  변환
- 미승인 OCR source는 `status="preview"`와
  `approval_status="requires_confirmation"`으로 반환
- confirmed 결과만 `AgentMemoryWriter` 연결점으로 넘김
- `AgentRunLogger` 연결점에 request_id, used_tools, latency_ms, cost_usd, provider를
  기록
- trace 원문은 기본 응답에서 숨기고, 명시적으로 켠 debug trace도 sanitized trace만
  노출

현재 구현은 backend DB 없이 테스트 가능한 adapter 계층입니다. 실제 FastAPI route와
`agent_runs`/`agent_memory` 테이블 저장은 backend checkout에서 이어서 연결합니다.
다음 통합 작업은 [앱 통합 TODO](docs/app-integration-todo.md)를 기준으로 진행합니다.

## 로컬 검증

```powershell
python -m unittest discover ai-agent/tests
python -m compileall ai-agent\src
```

## 2026-05-19 update

`changmin-aiagent/ai-agent` also reflects the first personalization loop at the
standalone package boundary.

- `SGLangClient` is now available as the primary self-hosted operating
  candidate. It reuses the OpenAI-compatible `/v1/chat/completions` contract and
  supports `response_format` payloads such as JSON Schema structured output.
- `OpenAICompatibleClient` remains available for compatible backends. vLLM is
  documented as an alternative compatible backend, while SGLang is the current
  operating candidate.
- `DailyHealthAgent.run(..., agent_memory=...)` accepts summarized memory
  context. Repeated nutrient patterns from confirmed records can increase
  recommendation priority and add a short rationale.
- `DailyHealthAgentAppAdapter` reads `context["agent_memory"]`, adds
  `agent_memory` to `used_tools` when memory is present, and does not write run
  logs for unconfirmed OCR preview responses.
- This package still does not own backend DB persistence. Actual
  `agent_memory`/`agent_runs` table storage is implemented in the backend
  integration branch and connected through adapter protocols here.
- Backend PostgreSQL + pgvector migration smoke passed in the integration
  checkout. Local SGLang live smoke also passed against the WSL2/Docker server
  at `http://localhost:30000/v1` with `RUN_SGLANG_SMOKE=1`.

Official SGLang references:

- [SGLang GitHub](https://github.com/sgl-project/sglang)
- [SGLang Structured Outputs](https://docs.sglang.io/docs/advanced_features/structured_outputs)
- [SGLang Model Gateway](https://docs.sglang.io/docs/advanced_features/sgl_model_gateway)

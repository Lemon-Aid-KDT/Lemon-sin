# 의사결정 기록

## 2026-05-19: Backend integration memory loop and SGLang candidate

- 구현 기준 브랜치는 `ai-agent-backend-integration`이고, 이 문서는 `changmin-aiagent`
  설계 문서에 해당 변경 내용을 추적하기 위해 갱신한다.
- 1차 개인화는 모델 fine-tuning이 아니라 `agent_memory`에 사용자별 요약 기억을 저장하고
  다음 `daily-coaching` 실행 전 `context["agent_memory"]`로 다시 주입하는 방식으로 둔다.
- `agent_memory` 갱신 대상은 사용자가 확정한 음식/영양제 기록과 서버가 저장한
  `nutrition_analysis` 결과로 한정한다.
- `food_ocr`, `supplement_ocr` source가 `user_confirmed=false`이면 기존 원칙대로
  preview-only 응답을 반환하고 `agent_memory`, `agent_runs`를 쓰지 않는다.
- `agent_memory`에는 raw image, raw OCR text, raw LLM response, prompt 전문을 저장하지
  않는다. 반복 패턴, 부족/과다 nutrient, supplement ingredient 요약, chronic caution tag처럼
  coaching 근거가 되는 최소 요약만 저장한다.
- `/api/v1/ai-agent/daily-coaching`은 기존 `AgentInput`/`AgentOutput` 응답 계약을 유지하되,
  memory 사용 시 `used_tools`에 `agent_memory`를 포함한다.
- `agent_runs`는 non-preview 실행에 대해서만 request id, provider, model, latency, cost,
  used tools 같은 실행 메타데이터를 저장한다.
- provider 전략은 개발 기본값 `Ollama`를 유지하고, 운영 후보는 `SGLang`을 추가한다.
  SGLang은 OpenAI-compatible `/v1/chat/completions`와 JSON Schema structured output을
  지원하는 self-hosted 후보로 본다.
- vLLM은 최종 운영 후보에서 제외하고, 이번 결정에서는 "대체 가능한
  OpenAI-compatible backend" 수준으로 문서화한다.
- `ALLOW_EXTERNAL_LLM=false`일 때 SGLang endpoint는 `localhost`, `127.0.0.1`, `::1`
  loopback URL만 허용한다.
- LLM은 계속 건강 판단자가 아니라 설명/구조화 보조자다. deterministic nutrition/policy
  engine과 `SafetyGuard`가 최종 판단 및 노출 가능성의 기준이다.
- 개인정보 삭제 흐름은 `agent_memory`, `agent_runs`도 함께 삭제해야 한다.
- 검증 메모: integration 브랜치에서 변경 파일 기준 `ruff`, `compileall`, 대상 pytest 70개가
  통과했다. 단, 현재 로컬 Python 환경에 `pytest-cov`와 `alembic` 패키지가 없어 기본 pytest
  addopts와 Alembic setup test는 완전 실행하지 못했다.

## 2026-05-19: Standalone ai-agent sync

- `changmin-aiagent/ai-agent` 독립 패키지에도 `SGLangClient`,
  `LLMRequest.response_format`, `PersonalizationContext.agent_memory`,
  `DailyHealthAgent.run(..., agent_memory=...)`를 반영한다.
- 이 패키지는 DB table을 소유하지 않고, backend가 로드한 `context["agent_memory"]`
  요약을 소비하는 경계만 담당한다.
- repeated nutrient pattern은 recommendation rationale과 priority에 제한적으로
  반영한다. 이 값은 confirmed record 기반 요약이어야 한다.
- preview-only OCR 응답은 standalone adapter에서도 run log를 쓰지 않는다.
- vLLM은 `OpenAICompatibleClient`로 대체 가능한 compatible backend로 남기고,
  운영 후보 설명은 SGLang 중심으로 맞춘다.

## 2026-05-18: AI Agent 방향

- 작업 브랜치는 `changmin-aiagent`입니다.
- 새 Agent 작업은 `ai-agent/` 아래에 격리합니다.
- 여기서 말하는 MVP는 버리는 데모가 아니라, 상용화를 향한 최소 제품 경로입니다.
- 혈당과 CGM 연동은 MVP 구현 범위에서 제외합니다.
- Agent 인터페이스에는 범용 건강 흐름 입력을 유지합니다. 이후 혈당, CGM, 체중,
  활동량, 식단 점수 흐름을 추가할 수 있게 하기 위함입니다.
- 민감한 건강 데이터를 다루므로 외부 LLM API는 선호하는 운영 경로가 아닙니다.
  아키텍처는 서버 운영 또는 self-hosted LLM 사용을 전제로 둡니다.
- OCR 저신뢰 대응은 이번 작업의 중심이 아닙니다. 핵심 문제는 신뢰 가능한 OCR
  섭취 데이터를 안전한 건강관리 코칭으로 바꾸는 것입니다.
- MVP에서 영양제 제안은 성분 중심으로 제한합니다. 특정 제품 추천은 법무, 약사,
  광고, 이해상충 검토가 끝나기 전까지 범위 밖입니다.
- LLM 출력은 건강 판단의 최종 권위가 아닙니다. 공식 데이터, 결정론적 영양 로직,
  사용자 맥락, Safety Guard 정책이 최종 기준입니다.
- Chat Agent는 독립 판단자가 아니라 `DailyCoachingResult`와 trace를 설명하는
  얇은 레이어로 둡니다.
- Chat Agent의 LLM 연결은 생성자 주입으로 분리합니다. 테스트에서는
  `FakeLLMClient`를 기본으로 사용해 네트워크 의존성을 제거합니다.
- 로컬 개발용 LLM runtime 1차 후보는 Ollama입니다. 개발자는 필요한 모델을 직접
  준비하고 `OllamaClient(model=...)`를 주입합니다. 공식 문서는
  [Ollama Chat API](https://docs.ollama.com/api/chat)를 기준으로 확인합니다.
- 운영용 self-hosted serving 후보는 SGLang입니다.
  `SGLangClient`는 OpenAI-compatible `/v1/chat/completions` 호환 서버에 연결합니다.
  vLLM은 같은 API 형태를 따르는 대체 compatible backend로만 남깁니다.
  공식 문서는
  [SGLang Structured Outputs](https://docs.sglang.io/docs/advanced_features/structured_outputs),
  [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)와
  [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)를
  기준으로 확인합니다.
- provider 선택은 이번 단계에서 설정 파일이나 환경변수 로딩으로 묶지 않습니다.
  앱 통합 시 별도 설정 계층에서 주입합니다.
- 외부 LLM API로 실제 건강 데이터, 원본 OCR 전체, 이미지, 시크릿을 보내지 않는
  원칙을 유지합니다. prompt에는 설명에 필요한 최소 findings, recommendations,
  trace 요약만 포함합니다.
- LLM 응답은 `SafetyGuard`를 통과해야만 노출합니다. 실패하거나 안전하지 않으면
  deterministic fallback 답변을 반환하고 건강 판단 결과는 그대로 둡니다.
- 공식 문서가 있는 LLM runtime, provider, serving API를 추가하거나 바꿀 때는
  구현과 문서에 공식 문서 URL을 함께 남깁니다. 2차 자료는 보조 근거로만 봅니다.
- 미승인 OCR source는 deterministic 평가로 넘기지 않고 preview-only 결과로
  멈춥니다. 사용자 승인 후 다시 실행해야 recommendations와 actions가 생성됩니다.
- trace는 Chat fallback과 LLM prompt에 그대로 노출될 수 있으므로 `SafetyGuard`로
  검사합니다. 위험 문구가 포함된 trace line은 원문을 숨기고 차단 문구로 대체합니다.
- 영양소 합산은 최소 alias/unit 정규화를 먼저 적용합니다. 현재 범위는
  비타민 D alias, `g/mg/mcg`, 비타민 D `IU -> mcg` 변환이며 전체 OCR alias와
  confidence 처리는 후속 OCR/DB 통합 범위로 둡니다.
- 기존 기획 문서의 `AgentInput`/`AgentOutput`, `agent_runs`, `agent_memory`
  계약은 `DailyHealthAgent` 내부 모델에 직접 섞지 않고 FastAPI/DB 통합 adapter에서
  맞춥니다.
- 영양제 성분 총량은 Supplement Engine에서 별도 계산해 UI와 검토 흐름에서
  음식+영양제 합산 결과와 구분해 볼 수 있게 합니다.
- Intake 결과에는 OCR 원본 이미지 ID, OCR 텍스트, 사용자 확인 여부를 보존합니다.

## 2026-05-18: 앱 통합 Adapter 경계

- `DailyHealthAgent` 내부 dataclass 모델을 Pydantic으로 교체하지 않습니다.
- 앱/FastAPI 계약은 `DailyHealthAgentAppAdapter`의 Pydantic `AgentInput`과
  `AgentOutput`에서 맞춥니다.
- Pydantic 모델과 필드 정의는 공식 문서
  [Models](https://docs.pydantic.dev/latest/concepts/models/)와
  [Fields](https://docs.pydantic.dev/latest/concepts/fields/)를 기준으로 확인합니다.
- adapter는 `request_id`, `agent_name`, `used_tools`, `latency_ms`, `cost_usd`,
  `provider`를 채워 `agent_runs` 기록에 필요한 최소 값을 제공합니다.
- 실제 DB 테이블이 아직 이 checkout에 없으므로 `AgentRunLogger`와
  `AgentMemoryWriter` Protocol로 저장 연결점만 둡니다.
- 미승인 OCR source는 preview 응답으로 멈추고, 승인된 payload가 다시 들어올 때만
  deterministic engine을 실행해 completed 응답을 만듭니다.
- trace 원문은 기본 `AgentOutput`에 포함하지 않습니다. debug trace를 켜도
  `SafetyGuard`로 정제된 trace만 노출합니다.

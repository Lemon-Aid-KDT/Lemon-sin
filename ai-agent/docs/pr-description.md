# PR 설명 초안: traced coaching용 Local LLM adapter 추가

## 요약

이 PR은 `ai-agent/` 아래에 Lemon Aid AI Agent 독립 작업 공간을 추가합니다.

핵심 제품 원칙은 그대로 유지합니다. 건강 판단은 deterministic engine이 담당하고,
LLM은 설명/문장화 레이어로만 사용합니다. `DailyHealthAgent`는 findings,
recommendations, actions, safety warnings, trace를 결정론적으로 계산합니다.
`ChatAgent`는 선택적으로 local LLM을 호출해 설명 문장을 만들 수 있지만, 새로운
건강 판단을 생성하지 않습니다.

## 변경 범위

- daily nutrition/supplement coaching용 deterministic Health Agent orchestration 추가
- Local LLM adapter 계층 추가
  - `FakeLLMClient`: 테스트와 네트워크 없는 실행용
  - `OllamaClient`: 로컬 개발용
  - `OpenAICompatibleClient`: vLLM 또는 OpenAI-compatible serving endpoint용
- 앱 스타일 Pydantic `AgentInput`/`AgentOutput` 계약을 내부 dataclass 모델에
  연결하는 `DailyHealthAgentAppAdapter` 추가
- OCR, DB, CGM, 혈당 API 직접 연동은 이번 PR 범위에서 제외

## Mock 데이터 전제

- 음식 OCR은 mock `FoodIntake` 객체로 표현합니다.
- 영양제 OCR은 mock `SupplementIntake` 객체로 표현합니다.
- OCR source metadata는 mock `IntakeSource` 객체로 표현합니다.
- 사용자 DB 데이터는 mock `UserProfile` 객체로 표현합니다.
- 기준 섭취량 데이터는 `ReferenceRange` 리스트로 표현합니다.
- 혈당/CGM 연동은 구현하지 않고 `HealthTrend`를 mock 입력 경계로 둡니다.
- 실제 건강 데이터, 이미지, 시크릿, API key는 포함하지 않습니다.

## Local LLM Provider 전략

- 테스트 provider: `FakeLLMClient`
  - 네트워크 호출 없음
  - deterministic test를 위한 고정 응답
  - provider/model 값 고정: `fake` / `fake-local-llm`
- 로컬 개발 provider: `OllamaClient`
  - 기본 endpoint: `http://127.0.0.1:11434`
  - `/api/chat` 호출
  - 공식 문서: https://docs.ollama.com/api/chat
- 운영/서버 runtime 후보: `OpenAICompatibleClient`
  - 기본 endpoint: `http://127.0.0.1:8000/v1`
  - `/chat/completions` 호출
  - API key는 선택값이며 없으면 `EMPTY` 사용
  - vLLM 공식 문서:
    https://docs.vllm.ai/en/latest/serving/openai_compatible_server/
  - OpenAI-compatible API reference:
    https://platform.openai.com/docs/api-reference/chat/create

Provider 선택은 생성자 주입으로만 처리합니다. 이번 PR에서는 `.env` 로딩, 모델
다운로드 자동화, runtime process 관리 기능을 추가하지 않습니다.

## SafetyGuard fallback 정책

- LLM output은 사용자 노출 전 반드시 `SafetyGuard.check_text()`를 통과해야 합니다.
- unsafe LLM output은 deterministic `ChatAgent` fallback 답변으로 대체합니다.
- local LLM timeout/connection failure가 발생해도 health agent 결과는 실패하지
  않습니다.
- trace text는 fallback 답변 또는 LLM prompt에 들어가기 전에 sanitize합니다.
- unsafe trace line은 `trace item withheld by policy guard`로 대체합니다.
- adapter 응답 직전에도 사용자 노출 text를 다시 `SafetyGuard`로 검사합니다.
- 기본 `AgentOutput`은 raw trace를 노출하지 않습니다. debug trace를 명시적으로 켠
  경우에도 sanitized trace만 포함합니다.

## 앱 통합 경계

`DailyHealthAgentAppAdapter`는 앱 계약과 내부 Agent 모델 사이의 얇은 호환 계층입니다.

- `AgentInput.user_id` -> `UserProfile.user_id`
- `AgentInput.payload` -> `DailyIntake`, `HealthTrend`, `ReferenceRange`
- `AgentInput.context` -> `UserProfile` context
- `DailyCoachingResult` -> app-facing findings, recommendations, actions, message,
  used tools, latency, cost, provider, approval status
- 미승인 OCR source record는 `status="preview"`와
  `approval_status="requires_confirmation"`을 반환
- 승인된 payload는 `status="completed"` 결과 생성 가능
- `AgentRunLogger`와 `AgentMemoryWriter` Protocol로 backend table 없이 DB 통합 hook만
  제공

Pydantic 공식 문서:

- https://docs.pydantic.dev/latest/concepts/models/
- https://docs.pydantic.dev/latest/concepts/fields/

## 검증

로컬 검증 명령:

```powershell
python -m unittest discover ai-agent\tests
python -m compileall ai-agent\src
```

결과:

- `22 tests OK`
- `compileall` 성공

테스트 커버리지:

- 고나트륨 + 고혈압 맥락 주의 처리
- 단백질, 비타민 D, 식이섬유 부족 코칭
- 마그네슘, 철분, 칼슘 상한량 처리
- 복약/만성질환 맥락에서 단정 표현 회피
- 제품 구매 유도 차단
- 혈당 trend 진단 회피
- `FakeLLMClient` deterministic 동작
- safe LLM response passthrough
- unsafe LLM fallback
- LLM failure fallback
- `urlopen` mock 기반 Ollama HTTP payload 검증
- `urlopen` mock 기반 OpenAI-compatible HTTP payload 검증
- 미승인 OCR preview-only 응답
- unsafe trace sanitization
- nutrient alias와 vitamin D unit conversion
- app adapter mapping, preview/confirmed status, logging hook, memory hook,
  debug trace 제한

## 리뷰 참고

- 로컬 workspace에는 `gh` CLI가 없어 PR을 CLI로 생성하지 않았습니다.
- `changmin-aiagent`를 `changmin-plan`과 직접 비교하면 branch history divergence
  때문에 관련 없는 `docs/` 삭제가 함께 잡힙니다. PR 생성 전 대상 base branch를
  확인해야 합니다.
- 의도한 리뷰 범위는 `ai-agent/`입니다.
- 실제 FastAPI route-level test와 DB persistence 연결은 backend checkout/branch가
  정해진 뒤 진행합니다.

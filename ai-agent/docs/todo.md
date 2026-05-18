# Lemon Aid AI Agent + Local LLM 구현/검증/병합 TODO 계획

## Summary

현재 `changmin-aiagent/ai-agent`의 Health Agent 구현을 기준으로, 로컬 LLM 연결
구조까지 포함해 병합 가능한 상태로 정리한다. 핵심 원칙은 **건강 판단은
deterministic engine이 하고, LLM은 설명/문장화만 담당**하는 것이다.

구현 기본값은 `FakeLLMClient`로 테스트 안정성을 확보하고, 개발용 런타임은
`Ollama`, 운영 후보는 `vLLM/OpenAI-compatible endpoint`로 열어둔다.

## Key Changes

- `DailyHealthAgent`는 기존처럼 nutrition/supplement/policy 판단을 만든다.
- `ChatAgent`는 `DailyCoachingResult.trace`, findings, recommendations만 받아
  설명을 생성한다.
- 새 LLM adapter 계층을 추가한다:
  - `FakeLLMClient`: 테스트용, 네트워크 없음
  - `OllamaClient`: 개발용 로컬 LLM, 기본 endpoint `http://127.0.0.1:11434`
  - `OpenAICompatibleClient`: vLLM 등 `/v1/chat/completions` 호환 서버용
- LLM 출력은 사용자 노출 전 반드시 `SafetyGuard`를 통과한다.
- OCR/DB 미완성 부분은 mock dataclass 입력으로 고정한다.

## Review Hardening Addendum

아래 항목은 기존 guide와 현재 `ai-agent` 구현의 계약 차이를 검토한 뒤 병합 전
우선 보강 대상으로 확정한 내용이다.

- [x] 미승인 OCR source는 deterministic 평가로 넘기지 않고 preview-only 결과로
  멈춘다.
- [x] `DailyCoachingResult.approval_status`로 `confirmed`와
  `requires_confirmation` 상태를 구분한다.
- [x] trace line은 사용자 노출 전 `SafetyGuard`로 검사하고, 위험 문구는 원문을
  숨긴다.
- [x] Chat fallback과 LLM prompt는 sanitized trace만 사용한다.
- [x] Nutrition 합산 전에 최소 nutrient alias와 unit conversion을 적용한다.
  - `Vitamin D`, `vitamin D`, `비타민D` -> `vitamin d`
  - `g/mg/mcg` 변환
  - vitamin D `IU -> mcg` 변환
- [x] 기존 `AgentInput`/`AgentOutput`, `agent_runs`, `agent_memory` 계약은 이번
  내부 Agent 모델에 직접 섞지 않고 FastAPI/DB 통합 adapter 후속 작업으로 둔다.

## Detailed TODO

### 1. 작업 전 상태 확인

- [ ] `changmin-aiagent` 브랜치인지 확인
  `git branch --show-current`

- [ ] 작업트리 확인
  `git status --short`

- [ ] 변경 범위가 `ai-agent/` 안에만 있는지 확인
  `git diff --stat`

- [ ] 현재 테스트 baseline 확인
  `python -m unittest discover ai-agent/tests`

- [ ] Python compile baseline 확인
  `python -m compileall ai-agent\src`

- [ ] `__pycache__`가 git 추적 대상에 없는지 확인
  `git status --short`

### 2. Mock 전제 고정

- [ ] 음식 OCR은 `FoodIntake` mock 객체로 대체한다.
- [ ] 영양제 OCR은 `SupplementIntake` mock 객체로 대체한다.
- [ ] OCR 원본 출처는 `IntakeSource` mock 객체로 대체한다.
- [ ] 사용자 DB 조회는 `UserProfile` mock 객체로 대체한다.
- [ ] 기준 섭취량 DB는 `ReferenceRange` 리스트로 대체한다.
- [ ] 혈당/CGM 연동은 구현하지 않고 `HealthTrend` mock 입력만 사용한다.
- [ ] 실제 건강 데이터, 이미지, 시크릿, API key는 테스트/문서/커밋에 넣지
  않는다.

### 3. Local LLM Adapter 설계

- [ ] `ai-agent/src/lemon_ai_agent/llm/` 패키지를 만든다.
- [ ] `base.py`에 공통 타입을 둔다:
  - `LLMMessage(role: Literal["system", "user", "assistant"], content: str)`
  - `LLMRequest(messages: list[LLMMessage], temperature: float = 0.2, max_tokens: int = 500)`
  - `LLMResponse(text: str, provider: str, model: str)`
  - `LocalLLMClient` Protocol with `generate(request: LLMRequest) -> LLMResponse`

- [ ] `fake.py`에 `FakeLLMClient`를 만든다.
  - 네트워크 호출 없음
  - 테스트에서 고정 응답 반환
  - provider는 `"fake"`, model은 `"fake-local-llm"`

- [ ] `ollama.py`에 `OllamaClient`를 만든다.
  - 기본 endpoint: `http://127.0.0.1:11434`
  - 기본 model: 설정에서 주입, 테스트 기본값은 `"qwen2.5:7b-instruct"` 같은
    문자열만 사용
  - stdlib `urllib.request`로 `/api/chat` 호출
  - timeout 기본값 30초
  - 연결 실패 시 `RuntimeError("Ollama request failed: ...")`
  - 공식 문서: [Ollama Chat API](https://docs.ollama.com/api/chat)

- [ ] `openai_compatible.py`에 `OpenAICompatibleClient`를 만든다.
  - 기본 endpoint: `http://127.0.0.1:8000/v1`
  - vLLM 서버의 `/chat/completions` 호출
  - API key는 선택값
  - key가 없으면 `"EMPTY"`를 사용
  - timeout 기본값 30초
  - 연결 실패 시 `RuntimeError("OpenAI-compatible request failed: ...")`
  - 공식 문서:
    [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/),
    [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

- [ ] `llm/__init__.py`에서 public export 정리:
  - `FakeLLMClient`
  - `OllamaClient`
  - `OpenAICompatibleClient`
  - `LLMMessage`
  - `LLMRequest`
  - `LLMResponse`
  - `LocalLLMClient`

### 4. ChatAgent에 LLM 연결

- [ ] `ChatAgent` 생성자에 선택적 `llm_client`를 받게 한다.
  - 기본값은 `None`
  - `None`이면 기존 deterministic template 답변 사용
  - client가 있으면 LLM으로 문장화 시도

- [ ] LLM prompt에는 최소 정보만 넣는다.
  - 포함: date, top findings, top recommendations, trace 요약
  - 제외: 원본 OCR 전체, 원본 이미지, 실제 개인 식별 정보, 시크릿

- [ ] system message에는 안전 경계를 명시한다.
  - 진단하지 말 것
  - 치료/처방하지 말 것
  - 특정 제품 구매를 유도하지 말 것
  - “현재 입력된 정보 기준”, “주의가 필요할 수 있음”, “전문가 상담 권장” 표현 사용

- [ ] LLM 응답은 `SafetyGuard.check_text()`로 검사한다.
  - 통과하면 LLM 응답 반환
  - 실패하면 deterministic fallback 답변 반환
  - warning은 추후 추적 가능하게 내부 결과 또는 테스트에서 확인 가능한 방식으로 유지

- [ ] LLM 실패 시 전체 Agent가 실패하지 않게 한다.
  - timeout/connection error 발생 시 fallback 답변 반환
  - 건강 판단 결과는 변하지 않음

### 5. Provider 선택 정책

- [ ] MVP 기본 테스트 provider는 `FakeLLMClient`로 한다.
- [ ] 로컬 개발 문서 기본 provider는 Ollama로 안내한다.
- [ ] 운영 후보 문서에는 vLLM/OpenAI-compatible endpoint를 안내한다.
- [ ] 이번 단계에서는 `.env` 로딩 라이브러리를 추가하지 않는다.
- [ ] provider 선택은 코드 생성자 주입 방식으로 처리한다.
  - 예: `ChatAgent(llm_client=OllamaClient(...))`
  - 앱 통합 시점에 설정 파일/환경변수 연결을 별도 작업으로 분리
- [ ] 공식 문서가 있는 provider/runtime은 구현과 문서에 공식 URL을 함께 남긴다.

### 6. 테스트 TODO

- [ ] `FakeLLMClient` 단위 테스트 추가
  - 입력 messages를 받고 고정 응답을 반환해야 함
  - provider/model 값이 고정되어야 함

- [ ] `ChatAgent` deterministic fallback 테스트 추가
  - llm client가 없으면 기존 trace 기반 답변을 반환해야 함
  - `diagnosis`, `diabetes`, `prescribe` 같은 표현이 없어야 함

- [ ] `ChatAgent + FakeLLMClient` 테스트 추가
  - fake 응답이 안전하면 그대로 반환해야 함

- [ ] unsafe LLM 응답 차단 테스트 추가
  - fake 응답: `"당뇨입니다. 이 제품을 구매하세요."`
  - 기대: 해당 응답을 반환하지 않고 fallback 반환

- [ ] LLM 실패 fallback 테스트 추가
  - fake client가 `RuntimeError`를 던지게 구성
  - 기대: ChatAgent가 예외를 밖으로 던지지 않고 fallback 반환

- [ ] Ollama client HTTP payload 테스트 추가
  - 실제 Ollama 서버 호출 금지
  - `urllib.request.urlopen` mock으로 요청 body 검증
  - endpoint는 `/api/chat`
  - messages, model, temperature, max_tokens 포함 확인

- [ ] OpenAI-compatible client HTTP payload 테스트 추가
  - 실제 vLLM 서버 호출 금지
  - `urllib.request.urlopen` mock으로 요청 body 검증
  - endpoint는 `/chat/completions`
  - Authorization header 처리 확인

- [ ] 기존 Health Agent 테스트 유지
  - 고나트륨/고혈압
  - 단백질/비타민D/식이섬유 부족
  - 마그네슘/철분/칼슘 상한량 초과
  - 복약 주의 문구
  - 제품 구매 유도 차단
  - 혈당 trend 진단 회피

- [ ] 전체 테스트 실행
  `python -m unittest discover ai-agent/tests`

- [ ] Python compile 실행
  `python -m compileall ai-agent\src`

### 7. 문서 TODO

- [ ] `ai-agent/README.md`에 Local LLM 전략 추가
  - 판단은 deterministic engine
  - LLM은 설명/문장화
  - 개발 기본값: Ollama
  - 운영 후보: vLLM/OpenAI-compatible
  - 테스트 기본값: FakeLLMClient

- [ ] `ai-agent/docs/architecture.md`에 LLM adapter 계층 추가
  - `ChatAgent -> LocalLLMClient -> Fake/Ollama/OpenAI-compatible`
  - LLM 출력은 SafetyGuard 통과 후 노출
  - 실패 시 fallback

- [ ] `ai-agent/docs/decision-log.md`에 의사결정 추가
  - Ollama는 개발용 기본 후보
  - vLLM은 운영용 고성능 serving 후보
  - provider는 생성자 주입으로 분리
  - 외부 LLM API로 실제 건강 데이터를 보내지 않는 원칙 유지
  - 공식 문서가 있는 provider/runtime은 공식 URL을 남기는 원칙 유지

- [ ] 문서 재읽기 검증
  `Get-Content -Encoding UTF8 -Path ai-agent\README.md`
  `Get-Content -Encoding UTF8 -Path ai-agent\docs\architecture.md`
  `Get-Content -Encoding UTF8 -Path ai-agent\docs\decision-log.md`

### 8. 충돌 방지 TODO

- [ ] 새 파일은 `llm/` 하위에만 추가해 기존 파일 충돌을 줄인다.
- [ ] 기존 `ChatAgent` 변경은 생성자/메서드 확장에 한정한다.
- [ ] `DailyHealthAgent`의 건강 판단 흐름은 변경하지 않는다.
- [ ] 기존 schema 필드를 rename하지 않는다.
- [ ] 기존 테스트 이름을 바꾸지 않고 새 테스트만 추가한다.
- [ ] 대량 포맷팅, 줄바꿈 정리, import 정렬 자동화는 하지 않는다.
- [ ] `ai-agent/` 밖 파일은 수정하지 않는다.
- [ ] 병합 전 `git diff --stat`으로 변경 범위를 확인한다.
- [ ] 병합 전 원격 최신화는 `git fetch origin`까지만 하고, rebase/merge는 충돌
  가능성을 확인한 뒤 진행한다.

### 9. 최종 검증 TODO

- [ ] 전체 테스트 통과 확인
  `python -m unittest discover ai-agent/tests`

- [ ] compile 통과 확인
  `python -m compileall ai-agent\src`

- [ ] 안전 문구 수동 점검
  - 진단 표현 없음
  - 치료/처방 표현 없음
  - 효과 보장 없음
  - 특정 제품 구매 유도 없음
  - 복약 단정 없음

- [ ] LLM 네트워크 테스트가 실제 네트워크에 의존하지 않는지 확인
  - unit test는 mock/fake만 사용
  - Ollama/vLLM 서버가 없어도 테스트 통과해야 함

- [ ] 최종 git 상태 확인
  `git status --short`

- [ ] 최종 diff 확인
  `git diff -- ai-agent`

### 10. 병합 준비 TODO

- [ ] staging 범위 제한
  `git add ai-agent/README.md ai-agent/docs/architecture.md ai-agent/docs/decision-log.md ai-agent/docs/todo.md ai-agent/src/lemon_ai_agent ai-agent/tests`

- [ ] staged diff 확인
  `git diff --cached --stat`

- [ ] 권장 커밋 메시지
  `feat(ai): add local llm adapter for traced coaching`

- [ ] 커밋 후 테스트 재실행
  `python -m unittest discover ai-agent/tests`
  `python -m compileall ai-agent\src`

- [ ] push 전 브랜치/상태 확인
  `git branch --show-current`
  `git status --short`

- [ ] push 대상
  `origin/changmin-aiagent`

- [ ] PR 설명에 포함
  - mock 데이터 전제
  - Local LLM provider 전략
  - Ollama/vLLM 차이
  - 공식 문서 링크
  - LLM은 판단이 아니라 설명 레이어라는 원칙
  - SafetyGuard fallback 정책
  - 테스트/compile 결과

## Assumptions

- 실제 OCR, DB, CGM, 혈당 API 연동은 이번 작업 범위가 아니다.
- 실제 Ollama/vLLM 서버를 띄우는 것은 이번 unit test 범위가 아니다.
- 로컬 LLM 연결은 네트워크 client 구현까지만 하고, 자동 실행/모델 다운로드는
  하지 않는다.
- 테스트는 항상 `FakeLLMClient` 또는 HTTP mock으로만 수행한다.
- Lemon Aid의 건강 판단 최종 권위는 LLM이 아니라 `NutritionEngine`,
  `SupplementEngine`, `SafetyGuard`, 기준 데이터다.
- Ollama는 개발 편의성 때문에 1차 추천 런타임이고, vLLM은 운영/서버 처리량이
  필요해질 때 연결할 후보로 둔다.

## 공식 참고 문서

- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

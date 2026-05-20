# Lemon Aid AI Agent + Local LLM 구현/검증/병합 TODO 계획

## Summary

현재 `changmin-aiagent/ai-agent`의 Health Agent 구현을 기준으로, 로컬 LLM 연결
구조까지 포함해 병합 가능한 상태로 정리한다. 핵심 원칙은 **건강 판단은
deterministic engine이 하고, LLM은 설명/문장화만 담당**하는 것이다.

구현 기본값은 `FakeLLMClient`로 테스트 안정성을 확보하고, 개발용 런타임은
`Ollama`, 운영 후보는 `SGLang/OpenAI-compatible endpoint`로 열어둔다.
vLLM은 대체 가능한 OpenAI-compatible backend로만 남긴다.

## Key Changes

- `DailyHealthAgent`는 기존처럼 nutrition/supplement/policy 판단을 만든다.
- `ChatAgent`는 `DailyCoachingResult.trace`, findings, recommendations만 받아
  설명을 생성한다.
- 새 LLM adapter 계층을 추가한다:
  - `FakeLLMClient`: 테스트용, 네트워크 없음
  - `OllamaClient`: 개발용 로컬 LLM, 기본 endpoint `http://127.0.0.1:11434`
  - `SGLangClient`: 운영 후보 로컬/자가호스팅 `/v1/chat/completions` 호환 서버용
  - `OpenAICompatibleClient`: vLLM 등 대체 compatible backend용
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

- [x] `changmin-aiagent` 브랜치인지 확인
  `git branch --show-current`

- [x] 작업트리 확인
  `git status --short`

- [x] 변경 범위가 `ai-agent/` 안에만 있는지 확인
  `git diff --stat`

- [x] 현재 테스트 baseline 확인
  `python -m unittest discover ai-agent/tests`

- [x] Python compile baseline 확인
  `python -m compileall ai-agent\src`

- [x] `__pycache__`가 git 추적 대상에 없는지 확인
  `git status --short`

### 2. Mock 전제 고정

- [x] 음식 OCR은 `FoodIntake` mock 객체로 대체한다.
- [x] 영양제 OCR은 `SupplementIntake` mock 객체로 대체한다.
- [x] OCR 원본 출처는 `IntakeSource` mock 객체로 대체한다.
- [x] 사용자 DB 조회는 `UserProfile` mock 객체로 대체한다.
- [x] 기준 섭취량 DB는 `ReferenceRange` 리스트로 대체한다.
- [x] 혈당/CGM 연동은 구현하지 않고 `HealthTrend` mock 입력만 사용한다.
- [x] 실제 건강 데이터, 이미지, 시크릿, API key는 테스트/문서/커밋에 넣지
  않는다.

### 3. Local LLM Adapter 설계

- [x] `ai-agent/src/lemon_ai_agent/llm/` 패키지를 만든다.
- [x] `base.py`에 공통 타입을 둔다:
  - `LLMMessage(role: Literal["system", "user", "assistant"], content: str)`
  - `LLMRequest(messages: list[LLMMessage], temperature: float = 0.2, max_tokens: int = 500)`
  - `LLMResponse(text: str, provider: str, model: str)`
  - `LocalLLMClient` Protocol with `generate(request: LLMRequest) -> LLMResponse`

- [x] `fake.py`에 `FakeLLMClient`를 만든다.
  - 네트워크 호출 없음
  - 테스트에서 고정 응답 반환
  - provider는 `"fake"`, model은 `"fake-local-llm"`

- [x] `ollama.py`에 `OllamaClient`를 만든다.
  - 기본 endpoint: `http://127.0.0.1:11434`
  - 기본 model: 설정에서 주입, 테스트 기본값은 `"qwen2.5:7b-instruct"` 같은
    문자열만 사용
  - stdlib `urllib.request`로 `/api/chat` 호출
  - timeout 기본값 30초
  - 연결 실패 시 `RuntimeError("Ollama request failed: ...")`
  - 공식 문서: [Ollama Chat API](https://docs.ollama.com/api/chat)

- [x] `openai_compatible.py`에 `OpenAICompatibleClient`를 만든다.
  - 기본 endpoint: `http://127.0.0.1:8000/v1`
  - OpenAI-compatible 서버의 `/chat/completions` 호출
  - API key는 선택값
  - key가 없으면 `"EMPTY"`를 사용
  - timeout 기본값 30초
  - 연결 실패 시 `RuntimeError("OpenAI-compatible request failed: ...")`
  - 공식 문서:
    [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/),
    [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

- [x] `llm/__init__.py`에서 public export 정리:
  - `FakeLLMClient`
  - `OllamaClient`
  - `OpenAICompatibleClient`
  - `LLMMessage`
  - `LLMRequest`
  - `LLMResponse`
  - `LocalLLMClient`

### 4. ChatAgent에 LLM 연결

- [x] `ChatAgent` 생성자에 선택적 `llm_client`를 받게 한다.
  - 기본값은 `None`
  - `None`이면 기존 deterministic template 답변 사용
  - client가 있으면 LLM으로 문장화 시도

- [x] LLM prompt에는 최소 정보만 넣는다.
  - 포함: date, top findings, top recommendations, trace 요약
  - 제외: 원본 OCR 전체, 원본 이미지, 실제 개인 식별 정보, 시크릿

- [x] system message에는 안전 경계를 명시한다.
  - 진단하지 말 것
  - 치료/처방하지 말 것
  - 특정 제품 구매를 유도하지 말 것
  - “현재 입력된 정보 기준”, “주의가 필요할 수 있음”, “전문가 상담 권장” 표현 사용

- [x] LLM 응답은 `SafetyGuard.check_text()`로 검사한다.
  - 통과하면 LLM 응답 반환
  - 실패하면 deterministic fallback 답변 반환
  - warning은 추후 추적 가능하게 내부 결과 또는 테스트에서 확인 가능한 방식으로 유지

- [x] LLM 실패 시 전체 Agent가 실패하지 않게 한다.
  - timeout/connection error 발생 시 fallback 답변 반환
  - 건강 판단 결과는 변하지 않음

### 5. Provider 선택 정책

- [x] MVP 기본 테스트 provider는 `FakeLLMClient`로 한다.
- [x] 로컬 개발 문서 기본 provider는 Ollama로 안내한다.
- [x] 운영 후보 문서에는 SGLang/OpenAI-compatible endpoint를 안내한다.
  - vLLM은 대체 가능한 compatible backend로만 남긴다.
- [x] 이번 단계에서는 `.env` 로딩 라이브러리를 추가하지 않는다.
- [x] provider 선택은 코드 생성자 주입 방식으로 처리한다.
  - 예: `ChatAgent(llm_client=OllamaClient(...))`
  - 앱 통합 시점에 설정 파일/환경변수 연결을 별도 작업으로 분리
- [x] 공식 문서가 있는 provider/runtime은 구현과 문서에 공식 URL을 함께 남긴다.

### 6. 테스트 TODO

- [x] `FakeLLMClient` 단위 테스트 추가
  - 입력 messages를 받고 고정 응답을 반환해야 함
  - provider/model 값이 고정되어야 함

- [x] `ChatAgent` deterministic fallback 테스트 추가
  - llm client가 없으면 기존 trace 기반 답변을 반환해야 함
  - `diagnosis`, `diabetes`, `prescribe` 같은 표현이 없어야 함

- [x] `ChatAgent + FakeLLMClient` 테스트 추가
  - fake 응답이 안전하면 그대로 반환해야 함

- [x] unsafe LLM 응답 차단 테스트 추가
  - fake 응답: `"당뇨입니다. 이 제품을 구매하세요."`
  - 기대: 해당 응답을 반환하지 않고 fallback 반환

- [x] LLM 실패 fallback 테스트 추가
  - fake client가 `RuntimeError`를 던지게 구성
  - 기대: ChatAgent가 예외를 밖으로 던지지 않고 fallback 반환

- [x] Ollama client HTTP payload 테스트 추가
  - 실제 Ollama 서버 호출 금지
  - `urllib.request.urlopen` mock으로 요청 body 검증
  - endpoint는 `/api/chat`
  - messages, model, temperature, max_tokens 포함 확인

- [x] OpenAI-compatible client HTTP payload 테스트 추가
  - 실제 OpenAI-compatible 서버 호출 금지
  - `urllib.request.urlopen` mock으로 요청 body 검증
  - endpoint는 `/chat/completions`
  - Authorization header 처리 확인

- [x] 기존 Health Agent 테스트 유지
  - 고나트륨/고혈압
  - 단백질/비타민D/식이섬유 부족
  - 마그네슘/철분/칼슘 상한량 초과
  - 복약 주의 문구
  - 제품 구매 유도 차단
  - 혈당 trend 진단 회피

- [x] 전체 테스트 실행
  `python -m unittest discover ai-agent/tests`

- [x] Python compile 실행
  `python -m compileall ai-agent\src`

### 7. 문서 TODO

- [x] `ai-agent/README.md`에 Local LLM 전략 추가
  - 판단은 deterministic engine
  - LLM은 설명/문장화
  - 개발 기본값: Ollama
  - 운영 후보: SGLang/OpenAI-compatible
  - 테스트 기본값: FakeLLMClient

- [x] `ai-agent/docs/architecture.md`에 LLM adapter 계층 추가
  - `ChatAgent -> LocalLLMClient -> Fake/Ollama/OpenAI-compatible`
  - LLM 출력은 SafetyGuard 통과 후 노출
  - 실패 시 fallback

- [x] `ai-agent/docs/decision-log.md`에 의사결정 추가
  - Ollama는 개발용 기본 후보
  - SGLang은 운영 후보 self-hosted serving
  - vLLM은 대체 가능한 OpenAI-compatible backend
  - provider는 생성자 주입으로 분리
  - 외부 LLM API로 실제 건강 데이터를 보내지 않는 원칙 유지
  - 공식 문서가 있는 provider/runtime은 공식 URL을 남기는 원칙 유지

- [x] 문서 재읽기 검증
  `Get-Content -Encoding UTF8 -Path ai-agent\README.md`
  `Get-Content -Encoding UTF8 -Path ai-agent\docs\architecture.md`
  `Get-Content -Encoding UTF8 -Path ai-agent\docs\decision-log.md`

### 8. 충돌 방지 TODO

- [x] 새 파일은 `llm/` 하위에만 추가해 기존 파일 충돌을 줄인다.
- [x] 기존 `ChatAgent` 변경은 생성자/메서드 확장에 한정한다.
- [x] `DailyHealthAgent`의 건강 판단 흐름은 변경하지 않는다.
- [x] 기존 schema 필드를 rename하지 않는다.
- [x] 기존 테스트 이름을 바꾸지 않고 새 테스트만 추가한다.
- [x] 대량 포맷팅, 줄바꿈 정리, import 정렬 자동화는 하지 않는다.
- [x] `ai-agent/` 밖 파일은 수정하지 않는다.
- [x] 병합 전 `git diff --stat`으로 변경 범위를 확인한다.
- [x] 병합 전 원격 최신화는 `git fetch origin`까지만 하고, rebase/merge는 충돌
  가능성을 확인한 뒤 진행한다.

### 9. 최종 검증 TODO

- [x] 전체 테스트 통과 확인
  `python -m unittest discover ai-agent/tests`

- [x] compile 통과 확인
  `python -m compileall ai-agent\src`

- [x] 안전 문구 수동 점검
  - 진단 표현 없음
  - 치료/처방 표현 없음
  - 효과 보장 없음
  - 특정 제품 구매 유도 없음
  - 복약 단정 없음

- [x] LLM 네트워크 테스트가 실제 네트워크에 의존하지 않는지 확인
  - unit test는 mock/fake만 사용
  - Ollama/SGLang/vLLM 서버가 없어도 테스트 통과해야 함

- [x] 최종 git 상태 확인
  `git status --short`

- [x] 최종 diff 확인
  `git diff -- ai-agent`

### 10. 병합 준비 TODO

- [x] staging 범위 제한
  `git add ai-agent/README.md ai-agent/docs/architecture.md ai-agent/docs/decision-log.md ai-agent/docs/todo.md ai-agent/src/lemon_ai_agent ai-agent/tests`

- [x] staged diff 확인
  `git diff --cached --stat`

- [x] 권장 커밋 메시지
  `feat(ai): add local llm adapter for traced coaching`

- [x] 커밋 후 테스트 재실행
  `python -m unittest discover ai-agent/tests`
  `python -m compileall ai-agent\src`

- [x] push 전 브랜치/상태 확인
  `git branch --show-current`
  `git status --short`

- [x] push 대상
  `origin/changmin-aiagent`

- [x] PR 설명에 포함
  - mock 데이터 전제
  - Local LLM provider 전략
  - Ollama/SGLang/vLLM 차이
  - 공식 문서 링크
  - LLM은 판단이 아니라 설명 레이어라는 원칙
  - SafetyGuard fallback 정책
  - 테스트/compile 결과

## 2026-05-19 Personalization memory loop follow-up

이번 항목은 `ai-agent-backend-integration` 구현 내용을 `changmin-aiagent` TODO 관점에서
재정리한 것이다.

### 완료 처리

- [x] `AgentMemoryWriter` hook 수준에 머물던 장기 memory 저장을 backend DB service로 1차 구현했다.
- [x] `agent_memory`와 `agent_runs` ORM model 및 Alembic revision 초안을 추가했다.
- [x] confirmed `daily-coaching` 결과만 memory에 반영하도록 했다.
- [x] unconfirmed OCR preview는 memory/run log를 쓰지 않는 정책을 유지했다.
- [x] memory 주입 시 반복 nutrient pattern을 recommendation priority와 rationale에 반영했다.
- [x] raw image, raw OCR text, raw LLM response, prompt 전문을 memory에 저장하지 않는 sanitizer를 추가했다.
- [x] SGLang을 운영 후보 provider로 추가하고 개발 기본 provider는 Ollama로 유지했다.
- [x] SGLang은 `ALLOW_EXTERNAL_LLM=false`일 때 loopback endpoint만 허용하도록 설정 검증을 추가했다.

### 계속 남은 항목

- [x] `agent_memory` summary schema를 실제 사용자 피드백 기준으로 안정화한다.
  - `schema_version`, canonical nutrient key, recent finding limit, forbidden raw key sanitizer를 테스트로 고정했다.
- [x] `(name, unit)` 기반 nutrient aggregation을 canonical nutrient id/unit conversion 중심으로 더 정리한다.
  - backend memory summary에서 `vitamin_d`/`Vitamin-D`를 `vitamin d`로 canonicalize하고 Vitamin D `IU -> mcg`를 적용한다.
- [x] supplement ingredient memory가 food-first coaching 원칙을 침범하지 않는지 안전 리뷰한다.
  - supplement memory는 `supplement_ingredients`에만 쌓고 `repeated_nutrient_patterns`를 만들지 않도록 테스트했다.
- [x] Alembic dependency가 있는 환경에서 `test_alembic_setup.py`를 다시 실행한다.
  - `requirements-dev.txt` 설치 후 Alembic head `0007_create_agent_memory_tables` 로드 테스트를 통과했다.
- [x] SGLang 공식 문서 링크와 운영 방법을 별도 backend 운영 문서에 추가한다.
  - `docs/Nutrition-docs/dev-guides/26-operations-manual.md`에 opt-in SGLang smoke와 공식 링크를 추가했다.

## 2026-05-19 changmin-aiagent package sync

`ai-agent-backend-integration`에서 확정한 memory loop와 SGLang 운영 후보 결정을
`changmin-aiagent/ai-agent` 독립 패키지에도 반영했다.

### 완료

- [x] `LLMRequest.response_format`를 추가해 OpenAI-compatible JSON Schema
  structured output payload를 보낼 수 있게 했다.
- [x] `SGLangClient`를 추가하고 provider label을 `sglang`으로 기록한다.
- [x] `OpenAICompatibleClient`는 vLLM 전용 문맥에서 분리해 범용 compatible
  backend adapter로 유지했다.
- [x] `PersonalizationContext.agent_memory`와
  `DailyHealthAgent.run(..., agent_memory=...)`를 추가했다.
- [x] `context["agent_memory"]`가 있으면 app adapter가 Agent에 주입하고
  `used_tools`에 `agent_memory`를 포함한다.
- [x] 반복 nutrient pattern이 recommendation priority와 rationale에 반영된다.
- [x] unconfirmed OCR preview는 standalone adapter에서도 run log를 남기지 않는다.
- [x] SGLang `response_format=json_schema` payload와 memory recommendation 동작을
  unit test로 고정했다.

### 추천 작업 순서

- [x] 1순위: canonical nutrient id/unit conversion을 `NutritionEngine`과
  backend memory summary schema 기준으로 맞춘다.
- [x] 2순위: backend integration 환경에서 Alembic head와 PostgreSQL
  upgrade/downgrade를 실제로 검증한다.
  - Alembic head 로드는 검증 완료. offline SQL 렌더링으로 `agent_memory`/`agent_runs` DDL 생성도 확인했다.
  - `RUN_POSTGRES_MIGRATION_SMOKE=1` + `TEST_DATABASE_URL` 기반 opt-in migration smoke test는 추가했다.
  - Chocolatey PostgreSQL 설치를 시도했지만 비관리자 권한과 `C:\ProgramData\chocolatey\lib` lock 접근 문제로 실패했다.
  - WSL 실행 파일은 있으나 Linux 배포판이 설치되어 있지 않아 WSL 기반 smoke로 전환할 수 없었다.
  - `winget`은 현재 로그온 세션 문제로 실행되지 않았고, `conda`는 PATH에서 찾을 수 없었다.
  - `wsl --install -d Ubuntu`는 `ERROR_ALREADY_EXISTS`로 실패했고,
    `wsl --list --online`은 `WININET_E_CANNOT_CONNECT`로 배포판 목록을 받지 못했다.
  - 이후 PATH 밖의 `C:\Users\KDS13\anaconda3\Scripts\conda.exe`는 발견했고
    `lemon-sglang` 환경을 통해 PostgreSQL 16.10 + pgvector 0.8.1 runtime을 구성했다.
  - Alembic 기본 `alembic_version.version_num VARCHAR(32)`가
    `0005_create_learning_vector_tables` revision id를 저장하지 못해 실패한 문제를
    `backend/alembic/env.py`에서 version table 길이 80으로 확장해 해결했다.
  - fresh DB `lemon_agent_smoke`에서
    `RUN_POSTGRES_MIGRATION_SMOKE=1` + `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_smoke`
    기준 upgrade/downgrade smoke가 `1 passed`로 통과했다.
- [x] 3순위: opt-in local SGLang smoke test 문서를 추가하고, 운영 설정에서
  `ALLOW_EXTERNAL_LLM=false` loopback 제한을 재확인한다.
  - `python -m pip install sglang`도 시도했지만 `flashinfer_python` build 중 Windows symlink 권한(`WinError 1314`)으로 실패했다.
  - `backend/scripts/check_ai_agent_runtime_prereqs.py`로 live smoke 전제조건을 확인할 수 있게 했다.
  - preflight는 `TEST_DATABASE_URL`과 `SGLANG_BASE_URL`의 host/port를 읽어
    임시 PostgreSQL port와 SGLang endpoint를 실제 설정 기준으로 점검한다.
  - 이전 세션에서는 WSL 배포판과 Docker 접근이 없어 live smoke를 실행할 수 없었다.
  - 이후 사용자가 `Ubuntu-Dev` WSL2 배포판, Docker Desktop, NVIDIA GPU passthrough,
    SGLang CUDA 12.9 runtime을 구성했다.
  - conda Python 3.11 환경에서도 `python -m pip install sglang`은 같은
    `flashinfer_python` symlink 권한(`WinError 1314`)으로 실패했다.
  - native Windows 설치 대신 WSL2/Docker runtime의
    `lmsysorg/sglang:latest-cu129-runtime` 서버를 사용한다.
  - `http://localhost:30000/v1` 기준 `/v1/models`, `/v1/chat/completions`,
    `RUN_SGLANG_SMOKE=1` ai-agent live smoke가 통과했다.
  - 긴 Docker 실행 명령은 `scripts/start-local-sglang.ps1`와
    `scripts/check-local-sglang.ps1`로 정리했다.
- [x] 4순위: memory summary 품질 기준을 만든다. 예: 반복 pattern이 너무 쉽게
  priority를 올리지 않는지, 최근 confirmed record만 반영되는지.
- [x] 5순위: supplement ingredient memory가 food-first coaching 원칙을 침범하지
  않는지 safety review checklist를 추가한다.

### 추가 검증 메모

- [x] privacy 삭제 단위 테스트가 `agent_memory`, `agent_runs` 삭제와
  `deleted_counts` 반영까지 검증하도록 갱신했다.
- [x] 전체 Nutrition backend 테스트 suite는 실행했으나, 이번 작업과 무관한 KDRIs
  dataset/source manifest checksum 불일치 5건으로 실패했다.
  - memory/SGLang 관련 targeted test와 privacy/config test는 통과했다.
  - PostgreSQL live migration smoke도 conda PostgreSQL + pgvector 환경에서 통과했다.
  - KDRIs checksum 정합성은 별도 데이터/manifest 정리 작업으로 분리한다.

## Assumptions

- 실제 OCR, DB, CGM, 혈당 API 연동은 이번 작업 범위가 아니다.
- 실제 Ollama/SGLang/vLLM 서버를 띄우는 것은 이번 unit test 범위가 아니다.
- 로컬 LLM 연결은 네트워크 client 구현까지만 하고, 자동 실행/모델 다운로드는
  하지 않는다.
- 테스트는 항상 `FakeLLMClient` 또는 HTTP mock으로만 수행한다.
- Lemon Aid의 건강 판단 최종 권위는 LLM이 아니라 `NutritionEngine`,
  `SupplementEngine`, `SafetyGuard`, 기준 데이터다.
- Ollama는 개발 편의성 때문에 1차 추천 런타임이고, SGLang은 운영 후보로 둔다.
  vLLM은 필요 시 대체 가능한 OpenAI-compatible backend로만 남긴다.

## 공식 참고 문서

- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [SGLang GitHub](https://github.com/sgl-project/sglang)
- [SGLang Structured Outputs](https://docs.sglang.io/docs/advanced_features/structured_outputs)
- [SGLang Model Gateway](https://docs.sglang.io/docs/advanced_features/sgl_model_gateway)
- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

# AI Agent 앱 통합 TODO

## Summary

`ai-agent` MVP는 deterministic Health Agent와 Local LLM 설명 레이어를 검증하는
독립 작업 공간이다. 실제 Lemon Aid 앱에 붙일 때는 이 내부 모델을 기존
FastAPI/DB/승인 흐름 계약에 맞추는 adapter를 통해 연결한다.

핵심 원칙은 `DailyHealthAgent`를 앱 계약에 직접 끼워 넣지 않고, 얇은 adapter가
`AgentInput`/`AgentOutput`, `agent_runs`, `agent_memory`, preview/approval 흐름을
연결하게 하는 것이다. 현재 `ai-agent` 안에는 backend DB 없이 테스트 가능한
`DailyHealthAgentAppAdapter`가 추가되어 있으며, 실제 FastAPI route와 DB 저장은
backend checkout에서 이어서 붙인다.

## Integration TODO

### 1. 계약 확인

- [x] `changmin-plan/docs/planning/guide/06-ai-agents.md`의 `AgentInput`,
  `AgentOutput` 계약을 실제 backend 코드와 대조한다.
- [x] backend에 이미 존재하는 Pydantic 모델, API route, DB logging 모듈을 확인한다.
- [x] `agent_runs`와 `agent_memory` 테이블/모듈의 현재 구현 여부를 확인한다.
- [x] 앱의 preview/approval API 흐름이 현재 어디에 구현되어 있는지 확인한다.

현재 확인 결과:

- 최초 확인 시점의 backend checkout은 `C:\MyWorkspace\lemon_aid\main\backend`였고,
  당시에는 `AgentInput`/`AgentOutput`, route, DB logging 구현이 없었다.
- 2026-05-19 기준 `ai-agent-backend-integration` 브랜치에는
  `/api/v1/ai-agent/daily-coaching`, `AgentInput`/`AgentOutput` adapter,
  `agent_runs`, `agent_memory` 1차 저장 구현이 추가되어 있다.
- 따라서 이 문서에서 "아직 backend DB 저장이 없다"는 표현은 `changmin-aiagent`
  단독 checkout에 대한 설명으로만 유지하고, 실제 backend 통합 상태는 아래
  2026-05-19 업데이트 섹션을 기준으로 본다.

### 2. Adapter 설계

- [x] `DailyHealthAgent` 입력 adapter를 설계한다.
  - `AgentInput.user_id` -> `UserProfile.user_id`
  - `AgentInput.payload` -> `DailyIntake`, `HealthTrend`, `ReferenceRange`
  - `AgentInput.context` -> `UserProfile` 또는 personalization context source
- [x] `DailyCoachingResult` 출력 adapter를 설계한다.
  - findings/recommendations/actions를 앱 응답 스키마로 변환
  - `approval_status="requires_confirmation"`이면 저장/액션 실행 없이 preview 응답
  - `approval_status="confirmed"`일 때만 후속 저장/액션 후보로 연결
- [x] adapter는 `DailyHealthAgent` 내부 dataclass를 Pydantic으로 강제 교체하지
  않는다.
- [x] adapter에서 `request_id`, `agent_name`, `used_tools`, `latency_ms`,
  `cost_usd`를 채운다.

현재 구현 파일:

- `src/lemon_ai_agent/adapters/app.py`
- `src/lemon_ai_agent/adapters/__init__.py`

### 3. 승인 전/후 흐름

- [x] OCR 분석 직후에는 사용자 preview를 반환한다.
- [x] 사용자가 수정/승인하기 전에는 DB 저장, 알림 등록, 캘린더 등록, 복용 기록
  같은 action을 실행하지 않는다.
- [x] 승인 후 동일 request 또는 승인 payload로 `DailyHealthAgent`를 다시 실행한다.
- [x] 미승인 OCR source가 남아 있으면 `requires_confirmation`으로 멈추는 현재
  방어선을 유지한다.

### 4. 로깅과 메모리

- [x] adapter 호출 단위로 `agent_runs`에 성공/실패, latency, cost, provider,
  request_id를 기록한다.
- [x] `FakeLLMClient` 사용 시 cost는 `0`으로 기록한다.
- [x] Ollama/vLLM 같은 self-hosted provider는 API 비용 대신 runtime/provider 정보를
  기록한다.
- [x] `agent_memory` 갱신은 평가 완료 후 별도 단계로 연결한다.

`changmin-aiagent`의 독립 Agent 패키지 구현은 DB 없이 `AgentRunLogger`와
`AgentMemoryWriter` Protocol로 연결점을 제공한다. 실제 `agent_runs`/`agent_memory`
테이블 저장은 `ai-agent-backend-integration` 브랜치의 backend DB 모듈에서 1차 구현했다.

### 5. 안전성

- [x] adapter 응답 직전에도 사용자 노출 text를 `SafetyGuard`로 검사한다.
- [x] trace 원문은 기본 응답에 노출하지 않고, 디버그/내부 로그용으로만 제한한다.
- [x] LLM prompt에는 원본 이미지, 전체 OCR 원문, 개인 식별 정보, 시크릿을 넣지
  않는다.
- [x] 건강 판단은 `DailyHealthAgent` deterministic 결과를 기준으로 하고, LLM 응답은
  설명 레이어로만 유지한다.

### 6. 테스트

- [x] adapter input mapping 테스트
- [x] `requires_confirmation` preview 응답 테스트
- [x] 승인 후 confirmed 응답 테스트
- [x] unsafe trace/text 차단 테스트
- [x] `agent_runs` logging mock 테스트
- [x] LLM provider가 없어도 `FakeLLMClient`로 통과하는 테스트
- [x] FastAPI route가 있다면 route-level 테스트 추가
  - `tests/integration/api/test_ai_agent_api.py` 4건을 실행해 daily-coaching route 계약을 확인했다.

현재 route-level 테스트는 이 checkout 안에 FastAPI backend route가 없어서 보류한다.

## 2026-05-19 Backend integration update

이 섹션은 `ai-agent-backend-integration` 브랜치 기준으로 확인된 1차 backend 통합 상태를
정리한다. `changmin-aiagent`의 `ai-agent` 패키지는 여전히 독립 Agent 런타임 기준 문서이며,
실제 FastAPI/DB 저장 구현은 integration 브랜치에 있다.

### 완료로 갱신된 항목

- [x] `/api/v1/ai-agent/daily-coaching` route가 `DailyHealthAgentAppAdapter`를 호출한다.
- [x] route 진입 시 sensitive health analysis consent가 없으면 기존처럼 403 fail-closed 한다.
- [x] Agent 실행 전 `agent_memory`를 로드해 `context["agent_memory"]`로 주입한다.
- [x] confirmed coaching 결과만 `agent_memory`에 요약 저장한다.
- [x] unconfirmed OCR source는 preview-only로 반환하고 memory/run log를 쓰지 않는다.
- [x] non-preview Agent 실행은 `agent_runs`에 provider, model, latency, cost, used tools를 저장한다.
- [x] supplement 확정 등록 후 user supplement ingredient 요약을 memory에 반영한다.
- [x] `nutrition_analysis` 저장 후 부족/과다/priority nutrient 패턴을 memory에 반영한다.
- [x] user data deletion 흐름에서 `agent_memory`, `agent_runs`도 삭제 대상에 포함한다.
- [x] `used_tools`는 memory가 주입된 coaching에서 `agent_memory`를 포함한다.
- [x] SGLang provider 후보를 추가하고 OpenAI-compatible payload와 JSON Schema response format을 지원한다.

### 남은 확인 항목

- [x] Alembic runtime 환경에서 head가 `0007_create_agent_memory_tables`로 로드되는지 확인한다.
- [x] 실제 PostgreSQL test database에서 migration upgrade/downgrade를 실행한다.
  - 로컬 5432와 Docker CLI는 사용할 수 없었지만, conda `lemon-sglang` 환경의
    PostgreSQL 16.10 + pgvector 0.8.1로 test DB를 구성했다.
  - `tests/integration/db/test_alembic_migration_smoke.py`를 추가해
    `RUN_POSTGRES_MIGRATION_SMOKE=1` + `TEST_DATABASE_URL`이 있을 때 upgrade/downgrade를 실행하게 했다.
  - `python -m alembic -c alembic.ini upgrade head --sql`로 `agent_memory`/`agent_runs` DDL 렌더링은 확인했다.
  - `choco install postgresql --yes --no-progress`는 비관리자 권한과 Chocolatey lock 접근 문제로 실패했다.
  - WSL 실행 파일은 있으나 Linux 배포판이 설치되어 있지 않고, `winget`은 로그온 세션 문제로 실행되지 않았다.
  - `wsl --install -d Ubuntu`는 `ERROR_ALREADY_EXISTS`로 실패했고,
    `wsl --list --online`은 `WININET_E_CANNOT_CONNECT`로 실패했다.
  - PATH 밖의 `C:\Users\KDS13\anaconda3\Scripts\conda.exe`는 발견했고
    `lemon-sglang` 환경으로 PostgreSQL runtime과 pgvector extension을 준비했다.
  - Alembic 기본 version table 길이 32가 긴 revision id를 저장하지 못하는 문제는
    `backend/alembic/env.py`에서 `version_num` 길이 80으로 확장해 해결했다.
  - fresh DB `lemon_agent_smoke`에서 opt-in migration smoke가 `1 passed`로 통과했다.
- [x] 실제 SGLang local server로 smoke test를 수행한다.
  - 2026-05-20 기준 사용자가 WSL2 + Docker Desktop + NVIDIA GPU 환경에서
    `lmsysorg/sglang:latest-cu129-runtime` 서버를 `127.0.0.1:30000`에 띄웠다.
  - `GET /v1/models`와 `POST /v1/chat/completions`가 로컬 SGLang 서버에서 성공했다.
  - `ai-agent/tests/test_sglang_live_smoke.py`를 추가해 `SGLangClient`가 실제
    `/v1/chat/completions` endpoint를 호출하는지 opt-in으로 검증한다.
  - `RUN_SGLANG_SMOKE=1`과
    `SGLANG_BASE_URL=http://localhost:30000/v1`,
    `SGLANG_MODEL=Qwen/Qwen2.5-0.5B-Instruct`,
    `SGLANG_API_KEY=EMPTY` 기준 live smoke가 `1 test OK`로 통과했다.
  - `python -m pip install sglang`은 `flashinfer_python` build 중 Windows symlink 권한(`WinError 1314`)으로 실패했다.
  - `backend/scripts/check_ai_agent_runtime_prereqs.py`로 PostgreSQL/SGLang live smoke 전제조건을 점검한다.
  - 이전 세션에서는 WSL 배포판과 Docker 접근이 없어 live smoke가 불가했지만,
    현재는 사용자 로컬 WSL2/Docker runtime에서 검증이 완료되었다.
  - WSL Ubuntu 설치도 이전에는 등록 상태/네트워크 문제로 완료하지 못했지만,
    현재는 `Ubuntu-Dev` 배포판으로 진행했다.
  - conda Python 3.11 환경에서도 `python -m pip install sglang`은 같은
    `flashinfer_python` symlink 권한(`WinError 1314`)으로 실패했다.
  - 앞으로 SGLang은 native Windows 설치 대신 WSL2/Docker runtime을 기준으로 검증한다.
- [x] 장기 memory 품질 평가 기준을 정한다. 예: 반복 nutrient pattern이 과도하게 recommendation을 밀어 올리지 않는지.
- [x] production 설정에서 SGLang loopback 제한과 `ALLOW_EXTERNAL_LLM` 정책을 운영 문서에 반영한다.

## 2026-05-19 standalone package sync

`changmin-aiagent/ai-agent` 독립 패키지에도 backend integration에서 필요한 소비
경계를 반영했다.

- [x] `SGLangClient`와 `LLMRequest.response_format`를 추가했다.
- [x] `DailyHealthAgent.run(..., agent_memory=...)`로 memory context를 받을 수
  있게 했다.
- [x] app adapter가 `context["agent_memory"]`를 Agent에 전달하고 memory가 있으면
  `used_tools`에 `agent_memory`를 포함한다.
- [x] unconfirmed OCR preview는 standalone adapter에서도 run log를 남기지 않는다.
- [x] 반복 nutrient pattern 기반 추천 문구/우선순위 반영을 테스트했다.

실제 SGLang local server smoke는 2026-05-20에 WSL2/Docker runtime으로 통과했다.
PostgreSQL test database migration upgrade/downgrade는 conda PostgreSQL + pgvector
환경에서 통과했고, SGLang provider live smoke도 `RUN_SGLANG_SMOKE=1` 기준
`1 test OK`로 확인했다. 다음 app/backend 통합 작업은 이 runtime baseline을
backend route smoke 또는 재사용 가능한 server startup 방식으로 확장하는 것이다.

전체 Nutrition backend test suite도 한 번 실행했지만, 이번 app/backend 통합 변경과
무관한 KDRIs dataset/source manifest checksum 불일치 5건으로 실패했다. 이 이슈는
AI Agent memory loop와 SGLang provider 작업의 완료 조건이 아니라 별도 데이터
manifest 정리 작업으로 분리한다.

## Assumptions

- 실제 앱 통합 전까지 `ai-agent`는 독립 패키지 형태를 유지한다.
- `AgentInput`/`AgentOutput` 호환성은 adapter에서 맞추고, 내부 dataclass 모델은
  유지한다.
- OCR/DB/CGM/혈당 API 직접 연동은 adapter 이후 별도 작업이다.
- LLM provider 변경 시 공식 문서를 먼저 확인하고 문서에 공식 URL을 남긴다.

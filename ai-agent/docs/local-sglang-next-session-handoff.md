# 로컬 SGLang 다음 세션 인수인계

작성일: 2026-05-20

이 문서는 새 Codex/AI 채팅 세션이 현재 로컬 SGLang 작업을 바로 이어가기 위한
인수인계 문서입니다. 실행 절차 자체는
`docs/local-sglang-runtime-checklist.md`를 기준으로 하고, 이 문서는 다음 작업
순서와 판단 기준을 고정합니다.

## 다음 세션에서 먼저 읽을 문서

1. `docs/local-sglang-runtime-checklist.md`
   - WSL2, Docker, NVIDIA GPU, SGLang 서버 실행 및 검증 절차
   - API key 판단
   - PowerShell 검증 명령
2. `README.md`
   - ai-agent의 현재 역할과 Local LLM 전략
3. `docs/todo.md`
   - ai-agent 구현/검증 TODO
4. `docs/app-integration-todo.md`
   - Lemon Aid app/backend 연동 TODO

## 현재까지 확인된 런타임 상태

- Windows + WSL2 + Docker Desktop + NVIDIA GPU 조합은 동작 확인됨.
- `Ubuntu-Dev`에서 `nvidia-smi`가 정상 동작함.
- Docker GPU passthrough는 NVIDIA CUDA `nbody` 샘플로 확인됨.
- `lmsysorg/sglang:latest`는 CUDA `>=13.0` 요구로 실패했음.
- 현재 PC에는 `lmsysorg/sglang:latest-cu129-runtime`을 사용해야 함.
- SGLang 서버는 아래 구성으로 성공했음.
  - Base URL: `http://localhost:30000/v1`
  - Model: `Qwen/Qwen2.5-0.5B-Instruct`
  - API key: 실제 key 불필요, client가 요구하면 `EMPTY` 사용
- `/v1/models`와 `/v1/chat/completions` 호출이 성공했음.
- PowerShell에서 모델 응답 텍스트로 아래 문장을 확인함.
- ai-agent의 `SGLangClient` live smoke test도 통과했음.
  - 실행 명령: `python -m unittest ai-agent.tests.test_sglang_live_smoke`
  - opt-in 환경변수: `RUN_SGLANG_SMOKE=1`
  - 결과: `Ran 1 test ... OK`

```text
Hello! How can I assist you today?
```

## 다음 작업의 목표

로컬 SGLang 서버를 Lemon Aid ai-agent의 OpenAI-compatible LLM provider 경로에서
실제 호출하는 검증은 완료되었습니다. 다음 작업은 이 검증 결과를 기준으로
런타임 실행 방식을 더 재사용 가능하게 정리하고, 필요하면 backend integration
흐름에서 같은 endpoint를 사용하도록 연결하는 것입니다.

LLM은 다음 역할만 맡아야 합니다.

- findings/recommendations/trace를 사용자에게 읽기 쉬운 문장으로 정리
- 이미 계산된 결과를 설명
- 건강 판단, 보충제 위험 판단, 정책 판단을 새로 만들지 않음

## 다음 세션 시작 체크

새 세션은 바로 구현하지 말고 아래 상태 확인부터 수행합니다.

```powershell
git -C changmin-aiagent status --short
```

주의: 현재 `changmin-aiagent`에는 이미 여러 수정 파일이 있습니다. 이 문서 작업
이전부터 존재하던 변경도 섞여 있으므로, 다음 세션은 사용자 변경을 되돌리지
않고 현재 diff를 읽은 뒤 이어가야 합니다.

SGLang 서버가 켜져 있는지 확인합니다.

```powershell
.\ai-agent\scripts\check-local-sglang.ps1
```

응답이 없으면 `docs/local-sglang-runtime-checklist.md`의 "수동 서버 실행 순서"에
따라 서버를 다시 띄우거나, 아래 스크립트를 사용합니다.

```powershell
.\ai-agent\scripts\start-local-sglang.ps1
```

## 권장 작업 순서

1. 현재 diff와 관련 파일을 읽습니다.
   - `src/lemon_ai_agent/llm/sglang.py`
   - `src/lemon_ai_agent/llm/openai_compatible.py`
   - `src/lemon_ai_agent/agents/chat.py`
   - `src/lemon_ai_agent/orchestrator.py`
   - `tests/test_llm_and_chat_agent.py`
   - `tests/test_app_adapter.py`
2. SGLang client가 실제 OpenAI-compatible endpoint를 어떻게 호출하는지 확인합니다.
3. 환경변수 이름을 확정합니다.
   - `SGLANG_BASE_URL=http://localhost:30000/v1`
   - `SGLANG_MODEL=Qwen/Qwen2.5-0.5B-Instruct`
   - `SGLANG_API_KEY=EMPTY`
4. 이미 추가된 단독 smoke test를 필요할 때 재실행합니다.
   - `RUN_SGLANG_SMOKE=1`일 때만 live SGLang 서버를 호출합니다.
   - 서버가 없거나 opt-in이 없으면 기본 테스트에서 skip됩니다.
5. ai-agent flow에서 LLM이 문장화 계층으로만 쓰이는지 계속 유지합니다.
   - deterministic result가 바뀌지 않아야 함
   - unsafe output 또는 provider 오류 시 deterministic fallback으로 돌아가야 함
6. 긴 Docker 실행 명령은 `scripts/start-local-sglang.ps1`와
   `scripts/check-local-sglang.ps1`로 정리되어 있습니다. 다음 단계에서는
   백그라운드 컨테이너나 Docker Compose로 바꿀지 결정합니다.

## 테스트 기준

기본 테스트:

```powershell
python -m unittest discover ai-agent/tests
python -m compileall ai-agent\src
```

SGLang live smoke test는 서버 의존성이 있으므로 기본 테스트와 분리합니다.
서버가 켜져 있을 때만 실행하고, 꺼져 있으면 skip 처리해야 합니다.

## 구현 시 지켜야 할 경계

- 실제 API key, Hugging Face token, 개인 건강 데이터는 문서나 테스트 fixture에
  넣지 않습니다.
- LLM provider 오류가 사용자 응답 실패로 바로 이어지지 않게 deterministic
  fallback을 유지합니다.
- LLM 출력은 SafetyGuard를 우회하지 않아야 합니다.
- trace나 fallback 문구도 사용자에게 보일 수 있으므로 safety/sanitization 대상입니다.
- PostgreSQL, backend DB persistence, `agent_memory`/`agent_runs` 연동은 별도
  backend integration 범위입니다. 이 문서의 다음 작업은 로컬 SGLang provider
  runtime smoke와 ai-agent 연결 확인에 한정합니다.

## 완료로 볼 수 있는 상태

- 로컬 SGLang 서버가 `localhost:30000/v1`에서 응답함.
- ai-agent의 SGLang/OpenAI-compatible client가 해당 endpoint를 호출함.
- opt-in live smoke test가 모델 응답을 받아옴.
- 기본 unit test와 compile check가 통과함.
- 문서에 실제 실행/검증 명령이 남음.
- 안전 경계가 유지됨.

위 항목은 2026-05-20 기준 완료되었습니다. 이후 세션에서는 이를 완료된 baseline으로
보고, 서버 재실행 자동화나 backend route smoke로 범위를 확장합니다.

## 다음 세션의 첫 응답 가이드

새 세션에서 사용자가 "이어서 해줘"라고 하면 다음처럼 진행합니다.

1. 먼저 현재 상태를 확인한다고 말합니다.
2. `git status --short`와 `.\ai-agent\scripts\check-local-sglang.ps1` 확인부터 수행합니다.
3. 서버가 꺼져 있으면 사용자에게 서버를 다시 띄우는 명령을 안내하거나,
   사용자가 허용하면 `.\ai-agent\scripts\start-local-sglang.ps1`로 함께 재실행합니다.
4. 서버가 켜져 있으면 `.\ai-agent\scripts\check-local-sglang.ps1 -RunLiveSmoke`로 baseline을 확인한 뒤
   서버 재실행 자동화 또는 backend route smoke 작업으로 넘어갑니다.

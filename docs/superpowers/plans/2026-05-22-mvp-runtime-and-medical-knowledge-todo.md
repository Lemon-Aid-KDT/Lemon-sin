# MVP 런타임 및 의료 지식층 TODO

> 작성일: 2026-05-22
> 작업 위치: `C:\MyWorkspace\lemon_aid\ai-agent-backend-integration`
> 범위: Flutter web, FastAPI, 로컬 SGLang, AI Agent MVP smoke, 만성질환 지식 경계

## 목표

MVP 확인 전에 런타임 문제가 제품 문제처럼 보이지 않도록 FastAPI 재시작,
Flutter web 포트, CORS 허용 origin, AI Agent chat smoke 순서를 고정한다.
만성질환 정보는 LLM 자체 학습 과제가 아니라 별도 의료 지식층 설계 과제로
분리한다.

## 현재 제품 경계

- Lemon Aid는 현재 의료기기, 진단 서비스, 처방 서비스가 아니다.
- 사용자에게 보여주는 출력은 건강관리 참고 코칭, 주의 안내, 전문가 상담 권장
  범위로 제한한다.
- LLM은 설명과 대화 말투를 담당한다.
- 영양 기준, 주의 조건, 금기 가능성, 동의 경계는 deterministic backend,
  SafetyGuard, 검증된 knowledge source가 담당한다.
- 지금 단계에서 만성질환 의료 사실을 fine-tuning으로 모델 내부에 주입하지 않는다.

## 추적해야 할 런타임 문제

최근 브라우저에서 `localhost:61747 -> 127.0.0.1:18080` 형태의 CORS 오류가
발생했다면, 이는 무시할 수 있는 콘솔 경고가 아니다. FastAPI가 실행 중이어도
허용 origin이 현재 Flutter web origin과 다르면 `/api/v1/ai-agent/chat` 호출은
브라우저에서 차단된다.

대표 원인:

- Flutter web이 매번 임의 포트로 떠서 FastAPI `ALLOWED_ORIGINS`와 다름
- FastAPI를 이전 환경변수로 띄운 프로세스가 살아 있음
- backend 코드를 수정했지만 FastAPI를 재시작하지 않음
- Flutter를 repo root에서 실행해 `pubspec.yaml`을 찾지 못함
- `LEMON_API_BASE_URL`이 web 기준 주소와 다르게 설정됨
- `.env.example` 또는 실행 환경의 `ALLOWED_ORIGINS`에 고정 Flutter web origin
  `http://localhost:52100`이 빠져 있음

## 로컬 기본 포트

| 구성요소 | 기본값 | 메모 |
| --- | --- | --- |
| FastAPI | `http://127.0.0.1:18080` | `scripts/start_ai_agent_dev_stack.ps1`가 실행 |
| Flutter web | `http://localhost:52100` | CORS 기본 허용 origin |
| PostgreSQL dev | `127.0.0.1:55432` | `.local/postgres-dev-data` 사용 |
| SGLang | `http://127.0.0.1:30000/v1` | OpenAI-compatible endpoint |

## 깨끗한 재시작 체크리스트

### 1. Flutter가 사용할 origin으로 FastAPI 실행

```powershell
cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
powershell -ExecutionPolicy Bypass -File scripts\start_ai_agent_dev_stack.ps1 -Foreground -FlutterWebOrigin http://localhost:52100
```

이 PowerShell 창은 계속 열어 둔다. `18080`에서 FastAPI가 이미 실행 중이라면,
기존 프로세스를 먼저 종료하거나 같은 `ALLOWED_ORIGINS`로 시작된 프로세스인지
확인한다.

### 2. FastAPI가 현재 코드로 떠 있는지 확인

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
(Invoke-RestMethod http://127.0.0.1:18080/openapi.json).paths.Keys | Select-String "/api/v1/ai-agent/chat"
```

기대 결과:

- `/health`가 `status = ok`를 반환한다.
- OpenAPI에 `/api/v1/ai-agent/chat`가 포함되어 있다.

chat route가 보이지 않으면 브라우저 테스트를 진행해도 의미가 없다. 이 worktree에서
backend를 다시 시작한다.

### 3. Flutter 앱 디렉터리에서 Flutter web 실행

```powershell
cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration\mobile\flutter_app
C:\src\flutter\bin\flutter.bat pub get
C:\src\flutter\bin\flutter.bat run -d chrome --web-port 52100 --dart-define=LEMON_API_BASE_URL=http://localhost:18080
```

repo root에서 실행하지 않는다. Chrome이 다른 포트로 열리면 중단 후
`--web-port 52100`으로 다시 실행하거나, 실제 포트에 맞춰 FastAPI를
`-FlutterWebOrigin http://localhost:<actual-port>`로 다시 시작한다.

### 4. 브라우저 smoke

- dashboard에 진입한다.
- dashboard action으로 chatbot 화면에 들어간다.
- 낮은 위험도의 건강관리 질문을 보낸다.
- `POST /api/v1/ai-agent/chat` 요청이 CORS 실패 없이 도달하는지 확인한다.
- 응답에 raw trace, raw findings, 내부 policy 문자열, 진단 단정, 치료 지시,
  처방 지시가 노출되지 않는지 확인한다.

### 5. 선택 사항: backend 전체 smoke

SGLang과 PostgreSQL이 준비되어 있고 UI 작업 전에 backend end-to-end 확인이
필요할 때만 실행한다.

```powershell
cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
$env:TEST_DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev"
$env:SGLANG_BASE_URL="http://127.0.0.1:30000/v1"
$env:SGLANG_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
$env:SGLANG_API_KEY="EMPTY"
python backend\scripts\smoke_ai_agent_server.py
```

이 스크립트는 FastAPI boot, 민감 건강 분석 동의 생성,
`/api/v1/ai-agent/daily-coaching`, `/api/v1/ai-agent/chat`, SGLang 또는
deterministic provider 동작, `agent_memory` 재주입을 확인한다. `--skip-db-upgrade`는
대상 DB schema가 이미 Alembic head임을 확인한 경우에만 사용한다. Flutter 브라우저
CORS 확인을 대체하지는 않는다.

이미 `scripts/start_ai_agent_dev_stack.ps1`로 FastAPI가 떠 있고 SGLang 서버만 아직
준비되지 않은 경우에는 deterministic fallback 배관만 먼저 확인할 수 있다.

```powershell
cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
python backend\scripts\smoke_ai_agent_server.py `
  --database-url postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev `
  --skip-db-upgrade `
  --skip-sglang-check `
  --use-existing-server
```

이 모드는 SGLang `/v1/models` readiness를 생략하고 기존 FastAPI 서버를 호출한다.
2026-05-24 확인 결과 `first_provider=deterministic`,
`second_provider=deterministic`, `second_used_tools`에 `agent_memory`가 포함됐다.

## CORS가 계속 실패할 때

아래 순서로 확인한다.

1. DevTools에 표시된 브라우저 origin을 확인한다. 예: `http://localhost:61747`.
2. FastAPI 시작 명령의 `-FlutterWebOrigin` 값이 그 origin과 정확히 같은지 확인한다.
3. `18080`에 묶인 오래된 FastAPI 프로세스가 남아 있지 않은지 확인한다.
4. Flutter web이 `LEMON_API_BASE_URL=http://localhost:18080`을 사용하는지 확인한다.
5. 재시작 후에도 OpenAPI에 `/api/v1/ai-agent/chat`가 포함되어 있는지 확인한다.

임시 디버깅에서도 CORS 허용 범위를 넓히기보다 Flutter web 포트를 고정해서 확인한다.

## 의료 지식층 TODO

위 runtime smoke는 MVP 배관이 연결되었는지만 확인한다. chatbot이 만성질환 의료
질문에 답할 준비가 되었다는 뜻은 아니다. chatbot 범위를 확장하기 전에 다음을
정리한다.

- 의료 지식층 문서 작성:
  `docs/Nutrition-docs/dev-guides/31-medical-knowledge-layer.md`
- 문서 번호 충돌 해결 완료:
  기존 `29-final-deliverables-index.md`와 `30-post-p1-execution-checklist.md`를
  유지하고, 의료 지식층 문서는 사용자 승인으로 31번에 둔다.
- 만성질환 사실은 LLM fine-tuning 밖에 둔다.
- source versioning과 review ownership은 1차 코드 registry로 정의한다.
- stale-source behavior는 live retrieval 또는 RAG 연결 전 readiness에서
  `source_stale`로 fail-closed하는 1차 정책을 둔다.
- 위험한 용어가 제품 약속처럼 쓰이지 않는지 테스트 또는 리뷰 체크를 추가한다.
- 개인화된 만성질환 정보 사용은 명시 동의와 profile context 뒤에만 둔다.

## 완료 기준

- [x] FastAPI `/openapi.json`에 `/api/v1/ai-agent/chat`가 포함되어 있다.
- [x] Flutter web을 `mobile/flutter_app`에서 고정 포트로 실행한다.
- [x] 현재 Flutter origin이 FastAPI CORS 설정에 포함되어 있다.
- [x] dashboard에서 chatbot 화면을 열 수 있다.
      `flutter test`의 `dashboard opens chatbot screen` 위젯 테스트와
      `http://127.0.0.1:52100/`, `/chat` HTTP 200 응답으로 확인했다.
- [x] chatbot 요청이 CORS origin `http://localhost:52100` 헤더를 포함해 성공한다.
- [x] 응답이 건강관리 참고 코칭 경계 안에 머문다.
      2026-05-24 API-level smoke에서 약물/영양제 병용 질문이 deterministic
      boundary response로 반환되고 `Drug interaction boundary applied` warning을
      포함함을 확인했다.
- [x] 의료 지식층 문서가 존재하며, 현재 MVP에서 medical-fact fine-tuning을
      배제한다고 명시한다.
- [x] 의료 지식층 문서 번호가 기존 dev-guides `29`/`30`과 충돌하지 않도록
      사용자 승인 후 31번으로 확정되어 있다.
- [x] backend Settings가 `KDCA_HEALTHINFO_TOPIC_IDS_FILE`, `KDCA_HEALTHINFO_TOPIC_IDS`,
  `KDCA_HEALTHINFO_API_KEY`(legacy), `SEMANTIC_SCHOLAR_API_KEY`
      등 source API key placeholder를 실제 설정 필드로 읽는다.
- [x] `.env.example`의 `ALLOWED_ORIGINS`가 Flutter web 고정 포트
      `http://localhost:52100`과 `http://127.0.0.1:52100`을 포함한다.
- [x] backend AI Agent package가 reviewed source registry와 Q&A eval set 회귀
      테스트를 가진다.
- [x] source readiness가 missing key, draft source, expired review를 secret 없이
      구분한다.
- [x] `backend/scripts/check_ai_agent_runtime_prereqs.py`가 runtime port와 함께
      medical source readiness를 출력하고, 기본 실행에서 앱과 같은 `.env`
      후보를 읽으며 `--env-file`/`--ignore-env-file`로 명시 제어할 수 있다.
      PostgreSQL/SGLang smoke readiness는 기본 상태 출력이고,
      `--require-postgres-smoke`, `--require-sglang-smoke`를 붙일 때만 종료코드
      실패로 판정한다.
- [x] `--require-medical-sources` strict gate로 키 누락, 미검수 source, source id
      오타를 종료코드 실패로 판정한다.
- [x] `--require-ollama` strict gate로 개발용 Ollama port와 configured model 존재를
      종료코드 실패/성공으로 판정한다.
- [x] `--require-ollama-parser-smoke` strict gate로 local Ollama structured parser
      경로를 실제 OCR sample 기반 종료코드 실패/성공으로 판정한다.

## 아직 외부 준비가 필요한 항목

- SGLang live smoke: 2026-05-25 재검증 완료. Docker Desktop을 시작하면 기존
  `lemon-sglang` 컨테이너가 `127.0.0.1:30000`에 올라오고, `Qwen/Qwen2.5-0.5B-Instruct`
  기준 standalone ai-agent live smoke와 backend FastAPI smoke가 모두 통과했다.
- PostgreSQL migration live smoke: 2026-05-25 `RUN_POSTGRES_MIGRATION_SMOKE=1`,
  `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev`
  기준 1 passed로 재검증했다.
- source API key/topic id: `KDCA_HEALTHINFO_TOPIC_IDS_FILE` 또는
  `KDCA_HEALTHINFO_TOPIC_IDS`, `MFDS_DATA_API_KEY`가 설정되면
  `kdca-healthinfo`, `mfds-drug-safety` readiness가 `ok`가 되어야 한다.
- Semantic Scholar: `SEMANTIC_SCHOLAR_API_KEY`가 설정되어도 현재는 research
  backlog source라서 `not_reviewed`가 정상이다. 사용자-facing retrieval에
  연결하려면 별도 source review가 필요하다.
- Ollama live readiness: 2026-05-25 Windows Ollama 0.24.0 설치와
  `qwen3.5:9b` pull 이후 `--require-ollama --require-ollama-parser-smoke`가 통과했다.
  `/api/chat` non-streaming smoke와 `RUN_OLLAMA_TESTS=true` 기반
  `OllamaSupplementParser` structured-output live pytest도 통과했다.

## KDCA key 수령 후 바로 실행할 명령

2026-05-25 기준 `GOOGLE_CLOUD_API_KEY`는 Google Vision OCR을 실제로 켤 때만
필요하므로 이 PR 준비 범위에서는 blocker가 아니다. 질병관리청 키를 발급받으면
아래 순서로 readiness만 재확인한다.

```powershell
cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
$env:KDCA_HEALTHINFO_TOPIC_IDS_FILE="backend/Nutrition-backend/config/kdca_healthinfo_topics.local.json"
$env:MFDS_DATA_API_KEY="<issued-mfds-key-if-required>"
python backend\scripts\check_ai_agent_runtime_prereqs.py `
  --require-medical-sources kdca-healthinfo mfds-drug-safety
```

키를 repo root `.env` 또는 `backend/.env`에 넣어두었으면 위 `$env:` 줄은 생략해도 된다.
별도 파일에 둔 경우에는 다음처럼 명시한다.

```powershell
python backend\scripts\check_ai_agent_runtime_prereqs.py `
  --env-file C:\path\to\.env `
  --require-medical-sources kdca-healthinfo mfds-drug-safety
```

기대 결과:

- `medical source kdca-healthinfo: ok`
- `medical source mfds-drug-safety: ok` 또는 이번 범위에서 MFDS를 제외하기로 명시한
  경우 strict 대상에서 `mfds-drug-safety`를 제거
- `medical source kdris-2025: ok`
- `medical source semantic-scholar: missing (not_reviewed)`는 정상
- SGLang live smoke와 PostgreSQL migration smoke는 2026-05-25에 opt-in 환경변수
  기준 통과했다. Docker Desktop 또는 `lemon-sglang` 컨테이너가 꺼져 있으면
  다시 `missing`으로 보일 수 있다. 해당 runtime까지 종료코드로 강제하려면
  `--require-postgres-smoke --require-sglang-smoke`를 추가한다.
- 개발용 Ollama를 재확인하려면 Ollama 서버가 켜져 있는 상태에서 다음을 실행한다:

```powershell
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-ollama --require-ollama-parser-smoke
```

기대 결과:

- `Ollama port 127.0.0.1:11434: ok`
- `OLLAMA_MODEL: ok`
- `Ollama parser smoke: ok`
- `Required Ollama runtime is not ready` 메시지가 없어야 함

2026-05-25 검증 결과: `qwen3.5:9b` 기준 위 조건이 통과했고,
`OllamaSupplementParser`가 Vitamin D 25 mcg OCR 예시를 schema-validated JSON으로
파싱했다. 반복 실행은
`$env:RUN_OLLAMA_TESTS='true'; python -m pytest -q --no-cov Nutrition-backend\tests\integration\llm\test_real_ollama_parser.py`
로 한다.

## 2026-05-25 live smoke 재검증 기록

```powershell
cd C:\MyWorkspace\lemon_aid
Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
curl.exe -sS http://127.0.0.1:30000/v1/models

cd C:\MyWorkspace\lemon_aid\changmin-aiagent
$env:RUN_SGLANG_SMOKE="1"
$env:SGLANG_BASE_URL="http://127.0.0.1:30000/v1"
$env:SGLANG_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
$env:SGLANG_API_KEY="EMPTY"
python -m unittest ai-agent.tests.test_sglang_live_smoke

cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
python backend\scripts\smoke_ai_agent_server.py `
  --server-url http://127.0.0.1:18081 `
  --database-url postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev `
  --sglang-base-url http://127.0.0.1:30000/v1 `
  --sglang-model Qwen/Qwen2.5-0.5B-Instruct `
  --timeout 120
```

검증 결과:

- standalone SGLang live smoke: `Ran 1 test ... OK`
- backend smoke: `first_provider=sglang`, `second_provider=sglang`, `chat_provider=sglang`
- backend smoke: `second_used_tools`에 `agent_memory` 포함
- backend smoke: `chat_used_tools`에 `agent_memory` 포함
- preflight: SGLang port/env와 PostgreSQL port/env는 `ok`
- 아직 남은 API/topic readiness: `KDCA_HEALTHINFO_TOPIC_IDS_FILE`의 주제별 4자리 ID,
  필요 시 `MFDS_DATA_API_KEY`

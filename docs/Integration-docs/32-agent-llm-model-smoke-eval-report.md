# 32. Agent/LLM Model Smoke/Eval Report

> Status: current-state smoke/eval report
> 작성일: 2026-06-04
> 기준 worktree: `feat/ai-agent-backend-integration`
> 기준 문서: [31-agent-llm-runtime-decision-eval.md](./31-agent-llm-runtime-decision-eval.md)

## 1. 목적

이 문서는 모델 최종 선정 문서가 아니다. 현재 실행 가능한 narrow current-state 검증 결과를
남기고, 모델 채택 전에 반드시 통과해야 하는 live smoke gate를 분리한다.

grill-me 결정:

- Eval은 `2단계 eval + live smoke 필수`로 한다.
- 현재 가능한 deterministic/golden eval과 runtime prereq는 바로 실행한다.
- 모델 채택 전에는 SGLang에서 Qwen baseline과 Gemma 후보 live smoke를 모두 통과해야 한다.

## 2. 현재 실행 결과

### 2.1 Runtime prereq

실행:

```powershell
python backend\scripts\check_ai_agent_runtime_prereqs.py --ignore-env-file
```

결과 요약:

| 항목 | 상태 |
| --- | --- |
| Docker | ok |
| WSL | ok |
| conda executable | ok |
| PostgreSQL smoke port `127.0.0.1:55432` | missing |
| SGLang port `127.0.0.1:30000` | missing |
| Ollama port `127.0.0.1:11434` | ok |
| `sglang` Python package | missing |
| `torch` Python package | missing |
| `RUN_POSTGRES_MIGRATION_SMOKE` | missing |
| `TEST_DATABASE_URL` | missing |
| `RUN_SGLANG_SMOKE` | missing |
| `SGLANG_MODEL` | ok |
| `OLLAMA_MODEL` | ok |

Medical source readiness:

| Source | 상태 |
| --- | --- |
| `kdris-2025` | ok |
| `cdc-public-health` | ok |
| `niddk-diabetes-living` | ok |
| `niddk-kidney-disease` | ok |
| `nih-ods-magnesium` | ok |
| `medlineplus-lithium` | ok |
| `kdca-healthinfo` | missing topic ids |
| `mfds-drug-safety` | missing api key |
| `semantic-scholar` | not reviewed |

판정:

- deterministic/offline eval은 실행 가능하다.
- SGLang live smoke는 현재 환경에서 실행 불가다.
- PostgreSQL live migration smoke도 현재 환경에서 실행 불가다.
- Ollama 서버 포트는 열려 있지만 이것만으로 모델 채택 증거는 아니다.

### 2.2 Deterministic golden eval

실행:

```powershell
python backend\scripts\eval_chatbot_golden.py
```

결과:

```text
status: pass
case_count: 20
failed: 0
```

통과 범위:

- 고혈압/나트륨 답변
- 혈압약/마그네슘 caution 답변
- 가슴 통증/숨참 urgent escalation
- 신장질환/칼륨 답변
- 당뇨/과식 후 다음 끼니 조절
- vitamin D 음식 후보
- reviewed source 없는 철분 질문 unknown 처리
- 자몽/고지혈증 약 boundary
- 리튬/셀레늄 boundary
- label-only supplement unknown 처리
- structured lookup 필요 질문
- 오늘 분석 pending/ready/stale 상태
- health analysis readiness level
- visible analysis stale context

판정:

- 현재 deterministic safety, answerability, source, unknown, analysis snapshot 계약은 pass다.
- 이 결과는 runtime 후보 채택의 필요조건이지 충분조건은 아니다.

### 2.3 Deterministic manual smoke

실행:

```powershell
python backend\scripts\ask_chatbot_agent.py --preset magnesium-blood-pressure-med --llm none
```

결과 요약:

- provider: `deterministic`
- answerability: `answerable_with_caution`
- source: `nih-ods-magnesium`
- 답변은 제품 라벨, 함량, 혈압약 종류, 신장 기능, 이상 증상, 약사/의사 확인을 포함했다.
- 병용 가능/불가 또는 복용량 결정 표현은 하지 않았다.

판정:

- LLM 없이도 핵심 의료 boundary와 source-grounded fallback은 동작한다.

### 2.4 Day 7 local runtime smoke

실행일: 2026-06-06

SGLang/Qwen live smoke 확인:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-sglang-smoke
```

결과 요약:

| 항목 | 상태 |
| --- | --- |
| Docker Desktop Linux engine | blocked: `dockerDesktopLinuxEngine` pipe unavailable |
| PostgreSQL smoke port `127.0.0.1:55432` | missing |
| SGLang port `127.0.0.1:30000` | missing |
| `sglang` Python package | missing |
| `torch` Python package | missing |
| `RUN_SGLANG_SMOKE` | missing |
| `TEST_DATABASE_URL` | missing |

판정:

- 초기 상태에서는 SGLang Qwen live smoke가 통과하지 못했다.
- 원인은 모델 품질 문제가 아니라 Docker/SGLang/PostgreSQL 실행 전제 미충족이었다.
- 아래 2.5에서 Docker Desktop, `lemon-sglang`, conda PostgreSQL을 복구해 Qwen baseline live smoke를 통과시켰다.

Ollama fallback 확인:

```powershell
C:\Users\KDS13\AppData\Local\Programs\Ollama\ollama.exe list
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-ollama
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-ollama-parser-smoke
python backend\scripts\ask_chatbot_agent.py --preset hypertension-sodium-dinner --llm ollama --model qwen3.5:9b --mode raw --timeout 120
python backend\scripts\ask_chatbot_agent.py --preset hypertension-sodium-dinner --llm ollama --model qwen3.5:9b --timeout 120
python backend\scripts\ask_chatbot_agent.py --preset p0-grapefruit-lipid-med --llm ollama --model qwen3.5:9b --timeout 120
```

결과 요약:

| 항목 | 상태 |
| --- | --- |
| Ollama model | `qwen3.5:9b` present |
| Ollama port `127.0.0.1:11434` | ok |
| Ollama parser smoke | ok, 약 9초 |
| Raw Ollama chat | pass: provider `ollama`, model `qwen3.5:9b`, 약 21초 |
| Chatbot guarded sodium path | safe fallback: provider `deterministic`, warning `LLM response text was empty`, 약 15초 |
| Chatbot guarded P0 boundary path | pass: provider `deterministic`, answerability `medical_decision_boundary`, warning `boundary_code:p0_grapefruit_statin`, 1초 미만 |

판정:

- Ollama 자체와 parser smoke는 Day 10 fallback 후보로 실행 가능하다.
- 다만 guarded chatbot path에서는 Qwen 응답이 빈 LLM 응답으로 정규화되어 deterministic renderer로 안전하게 fallback됐다.
- P0 자몽/고지혈증 약 boundary는 fallback 경로에서도 `medical_decision_boundary`와 source를 유지했다.
- 따라서 Day 10 demo runtime 후보는 `SGLang live smoke 복구 전까지 deterministic safety baseline + Ollama dev fallback`으로 둔다.
- Ollama fallback은 production runtime이 아니라 local demo/degradation path로만 취급한다.

### 2.5 Day 7 follow-up: SGLang Qwen baseline recovered

실행일: 2026-06-06

복구 절차:

```powershell
Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
docker start lemon-sglang
python backend\scripts\smoke_ai_agent_server.py --database-url postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev --sglang-base-url http://127.0.0.1:30000/v1 --sglang-model Qwen/Qwen2.5-0.5B-Instruct --timeout 120
```

복구 결과:

| 항목 | 상태 |
| --- | --- |
| Docker daemon | ok |
| `lemon-sglang` container | running |
| SGLang `/v1/models` | `Qwen/Qwen2.5-0.5B-Instruct` |
| PostgreSQL port `127.0.0.1:55432` | ok |
| strict preflight | ok with `--require-postgres-smoke --require-sglang-smoke` |
| Qwen chatbot smoke | pass: provider `sglang`, answerability `answerable`, source `kdris-2025`, 약 4초 |
| FastAPI + PostgreSQL + SGLang smoke | pass: `first_provider=sglang`, `second_provider=sglang`, `chat_provider=sglang`, unknown backlog delta `+1`, 약 10초 |
| Existing FastAPI server smoke | pass: `http://127.0.0.1:18080`, `chat_provider=sglang`, unknown backlog delta `+1`, 약 3초 |
| SGLang pytest smoke | pass: 3 passed |

추가 실행:

```powershell
$env:RUN_POSTGRES_MIGRATION_SMOKE='1'
$env:TEST_DATABASE_URL='postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev'
$env:RUN_SGLANG_SMOKE='1'
$env:SGLANG_BASE_URL='http://127.0.0.1:30000/v1'
$env:SGLANG_MODEL='Qwen/Qwen2.5-0.5B-Instruct'
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-postgres-smoke --require-sglang-smoke

python backend\scripts\ask_chatbot_agent.py --preset hypertension-sodium-dinner --llm sglang --model Qwen/Qwen2.5-0.5B-Instruct --endpoint http://127.0.0.1:30000/v1 --timeout 120

python backend\scripts\smoke_ai_agent_server.py --use-existing-server --skip-db-upgrade --database-url postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev --sglang-base-url http://127.0.0.1:30000/v1 --sglang-model Qwen/Qwen2.5-0.5B-Instruct --timeout 120

$env:RUN_SGLANG_SMOKE='1'
$env:SGLANG_BASE_URL='http://127.0.0.1:30000/v1'
$env:SGLANG_MODEL='Qwen/Qwen2.5-0.5B-Instruct'
python -m pytest -q --no-cov backend/ai_agent_chat/tests/test_sglang_smoke.py backend/ai_agent_chat/tests/test_sglang_client.py backend/ai_agent_chat/tests/test_chatbot_agent.py::test_chatbot_structured_json_output_is_rendered_to_answer_sections
```

Qwen baseline 판정:

- SGLang Qwen baseline은 live smoke 기준으로 다시 `pass`다.
- FastAPI route도 `/api/v1/ai-agent/chat` canonical endpoint에서 provider `sglang`와 reviewed source 계약을 유지했다.
- Qwen 답변에는 반복 표현이 있어 Day 8 비교에서는 latency뿐 아니라 section 품질과 반복/중복 문구를 함께 봐야 한다.

Gemma 후보 준비 상태:

| 항목 | 상태 |
| --- | --- |
| SGLang served models | Qwen only |
| SGLang container HF cache | `models--Qwen--Qwen2.5-0.5B-Instruct` only |
| Ollama models | `qwen3.5:9b` only |
| GPU memory | 8GB class, current Qwen serving uses about 5.5GB |

Gemma 비교 판정:

- 현재 로컬에는 Gemma 후보 모델이 설치되어 있지 않아 Gemma live smoke는 아직 실행할 수 없다.
- Day 8은 먼저 실제 후보 tag를 `google/gemma-3n-E2B` 또는 별도 Ollama/SGLang tag로 확정하고 모델 다운로드/서빙 방식을 정해야 한다.
- 같은 SGLang endpoint에서 Gemma를 비교하려면 Qwen 컨테이너와 별도 port로 Gemma 컨테이너를 띄우거나, Qwen 컨테이너를 내리고 Gemma 모델로 재기동해야 한다.
- 모델 기본값 변경은 여전히 금지한다. Qwen baseline은 통과했지만 Gemma 후보 smoke가 없기 때문이다.

## 3. 아직 통과하지 못한 필수 gate

아래 항목은 모델 채택 전 필수다.

| Gate | 현재 상태 | 필요 작업 |
| --- | --- | --- |
| SGLang Qwen live smoke | 통과 | 2026-06-06 `lemon-sglang` 복구 후 Qwen baseline smoke 통과 |
| SGLang Gemma live smoke | 미통과 | Gemma 후보 모델명/tag 확정 후 같은 prompt/schema로 smoke |
| structured JSON schema live validation | 미통과 | live model 응답을 Pydantic/JSON Schema로 검증 |
| latency 기록 | 미통과 | 각 case의 total latency, timeout, 실패율 기록 |
| Ollama strict parser smoke | 별도 확인 필요 | fallback으로 유지할 경우 모델 tag와 parser smoke 재확인 |
| PostgreSQL live smoke | 미통과 | `TEST_DATABASE_URL`와 test DB 준비 후 migration/server smoke |

## 4. Live smoke 필수 후보

### 4.1 Qwen baseline

SGLang baseline:

```text
SGLANG_BASE_URL=http://127.0.0.1:30000/v1
SGLANG_MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

목적:

- 현재 repo baseline이므로 비교 기준으로 유지한다.
- Gemma 후보가 더 나은지 판단하려면 Qwen 결과가 필요하다.

### 4.2 Gemma 후보

공식 확인 후보:

```text
google/gemma-3n-E2B
```

목적:

- 사용자가 전환을 고려하는 Gemma E2B 계열 후보를 실제 Agent workload에서 검증한다.
- `Gemma 4 E2B`라는 표현은 실제 provider tag 확인 전까지 확정명으로 쓰지 않는다.

공식 참고:

- https://ai.google.dev/gemma/docs/gemma-3n
- https://huggingface.co/google/gemma-3n-E2B

## 5. Live smoke 명령 초안

### 5.1 SGLang readiness

```powershell
$env:RUN_SGLANG_SMOKE='1'
$env:SGLANG_BASE_URL='http://127.0.0.1:30000/v1'
$env:SGLANG_MODEL='Qwen/Qwen2.5-0.5B-Instruct'
python backend\scripts\check_ai_agent_runtime_prereqs.py --require-sglang-smoke
```

### 5.2 Qwen chatbot smoke

```powershell
python backend\scripts\ask_chatbot_agent.py `
  --preset magnesium-blood-pressure-med `
  --llm sglang `
  --model Qwen/Qwen2.5-0.5B-Instruct `
  --endpoint http://127.0.0.1:30000/v1 `
  --timeout 120
```

### 5.3 Gemma chatbot smoke

실제 모델명은 SGLang 서버 기동 시 확인한 tag로 바꾼다.

```powershell
python backend\scripts\ask_chatbot_agent.py `
  --preset magnesium-blood-pressure-med `
  --llm sglang `
  --model google/gemma-3n-E2B `
  --endpoint http://127.0.0.1:30000/v1 `
  --timeout 120
```

### 5.4 Golden subset smoke

최소 live subset:

```powershell
python backend\scripts\eval_chatbot_golden.py --case magnesium_blood_pressure_med
python backend\scripts\eval_chatbot_golden.py --case urgent_chest_pain_shortness_of_breath
python backend\scripts\eval_chatbot_golden.py --case unknown_iron_food_candidates
```

주의:

- 현재 `eval_chatbot_golden.py`는 deterministic `ChatbotAgent()` 기준이다.
- live LLM golden eval로 쓰려면 provider 주입 옵션을 추가하거나 별도 script가 필요하다.

## 6. 채택 기준

Qwen baseline 또는 Gemma 후보는 아래를 모두 만족해야 한다.

- SGLang server가 `/v1/models`와 `/v1/chat/completions`에 응답한다.
- 같은 prompt에서 JSON schema 또는 structured section이 parse된다.
- deterministic golden eval과 같은 answerability/safety/source 계약을 깨지 않는다.
- 금지 문구와 unsupported medical fact가 나오면 fallback된다.
- `sources[]`, `answerability`, `requires_user_approval`, `ctas[]` 계약이 유지된다.
- raw OCR/raw prompt/raw LLM output/internal trace가 응답에 노출되지 않는다.
- latency와 timeout을 기록한다.

## 7. 현재 결론

현재 채택 판정:

| 후보 | 판정 |
| --- | --- |
| deterministic renderer | `accepted_as_safety_baseline` |
| SGLang Qwen baseline | `accepted_as_current_runtime_baseline` |
| SGLang Gemma E2B 후보 | `candidate_needs_live_smoke` |
| Ollama Qwen | `dev_fallback_needs_parser_smoke` |
| 외부 상용 API | `not_default_runtime` |

모델 기본값 변경은 아직 하면 안 된다. SGLang Qwen과 Gemma live smoke가 모두 통과한 뒤
별도 PR에서 env 기본값과 운영 문서를 바꾼다.

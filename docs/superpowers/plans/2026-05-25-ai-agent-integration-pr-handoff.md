# AI Agent 통합 PR handoff

> 작성일: 2026-05-25
> 브랜치: `feat/ai-agent-backend-integration`
> 권장 base: `develop`
> PR 상태 권장값: Draft

## PR 제목

```text
[codex] Integrate AI agent backend and local LLM runtime
```

## PR 본문

```markdown
## Summary

This draft PR publishes the AI Agent backend/mobile integration branch for team review.

What is included:
- FastAPI AI Agent routes for `/api/v1/ai-agent/daily-coaching` and `/api/v1/ai-agent/chat`
- `agent_memory` persistence and reinjection flow
- local/self-hosted LLM provider paths for SGLang and Ollama
- bounded Korean health-coaching chatbot policy with source-family metadata and safety boundaries
- Ollama structured supplement parser smoke gate
- mobile Flutter contracts for confirmed food/supplement/activity payloads and chatbot source families
- runtime/docs updates for strict preflight and handoff

## Validation

Current local validation completed on 2026-05-25:
- `python -m pytest -q --no-cov ai_agent_chat\tests Nutrition-backend\tests\integration\api\test_ai_agent_api.py Nutrition-backend\tests\unit\services\test_agent_memory.py Nutrition-backend\tests\unit\services\test_medical_source_readiness.py Nutrition-backend\tests\unit\scripts\test_smoke_ai_agent_server.py Nutrition-backend\tests\unit\scripts\test_check_ai_agent_runtime_prereqs.py Nutrition-backend\tests\unit\llm\test_ollama_parser.py Nutrition-backend\tests\unit\llm\test_ollama_vision_assist.py Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py Nutrition-backend\tests\integration\llm\test_real_ollama_parser.py` -> `106 passed, 2 skipped`
- `RUN_OLLAMA_TESTS=true python -m pytest -q --no-cov Nutrition-backend\tests\integration\llm\test_real_ollama_parser.py` -> `1 passed`
- `python backend\scripts\check_ai_agent_runtime_prereqs.py --require-postgres-smoke --require-sglang-smoke --require-ollama --require-ollama-parser-smoke` with local env -> passed
- `python backend\scripts\smoke_ai_agent_server.py --server-url http://127.0.0.1:18082 --database-url postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_dev --sglang-base-url http://127.0.0.1:30000/v1 --sglang-model Qwen/Qwen2.5-0.5B-Instruct --timeout 120` -> `status=ok`, `first_provider=sglang`, `second_provider=sglang`, `chat_provider=sglang`, `agent_memory` used
- `python -m unittest ai-agent.tests.test_sglang_live_smoke` in `changmin-aiagent` with SGLang env -> OK
- `flutter analyze` in `mobile/flutter_app` -> No issues
- `flutter test` in `mobile/flutter_app` -> All tests passed

## Known blocker before ready-for-review

The final strict medical-source gate still needs the issued KDCA key:

```powershell
python backend\scripts\check_ai_agent_runtime_prereqs.py `
  --require-postgres-smoke `
  --require-sglang-smoke `
  --require-medical-sources kdca-healthinfo mfds-drug-safety `
  --require-ollama `
  --require-ollama-parser-smoke
```

Current result: all runtime/LLM gates pass, but `kdca-healthinfo=missing_topic_ids`
fails until `KDCA_HEALTHINFO_TOPIC_IDS_FILE` points at the local
`backend/Nutrition-backend/config/kdca_healthinfo_topics.local.json` file with
all required KDCA 4-digit XML topic identifiers filled.

## Review notes

This is intentionally a draft because the branch is large and `origin/develop` has diverged. It should be reviewed as an integration branch, not as a small isolated patch.
```

## Codex 실행 결과

GitHub connector로 PR 생성을 시도했지만 다음 권한 오류로 실패했다.

```text
403 Resource not accessible by integration
```

현재 작업 머신에서는 `gh` CLI도 PATH에 없으므로, GitHub UI에서 위 제목과 본문으로
draft PR을 생성하는 방식이 가장 안전하다.

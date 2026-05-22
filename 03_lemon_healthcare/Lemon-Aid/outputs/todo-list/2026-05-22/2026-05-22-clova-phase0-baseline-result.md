# 2026-05-22 CLOVA Phase 0 Baseline Result

## Scope

- 실행 루트: `$LEMON_AID_ROOT`
- 브랜치: `feat/ocr-quality-gates`
- 승인 범위: archive의 16개 supplement fixture 이미지를 NAVER CLOVA OCR로 1회 전송
- 원칙: raw OCR text, raw provider payload, request header, secret, image bytes는 출력/저장하지 않음

## Official References

- NAVER Cloud CLOVA OCR API docs: https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
- NAVER Cloud General OCR API docs: https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocr
- HTTPX multipart/file upload docs used by the local API smoke helper: https://www.python-httpx.org/quickstart/#sending-multipart-file-uploads

## Inputs

- Collector manifest:
  `$LEMON_HEALTHCARE_ROOT/_archive/yeong-Lemon-Aid/data/supplement_images/private_workspace/stage0_naver_chronic/manifest.json`
- Evaluation manifest seed:
  `$LEMON_HEALTHCARE_ROOT/_archive/yeong-Lemon-Aid/data/supplement_images/private_workspace/stage0_naver_chronic/manifest-three-tier.jsonl`
- Env file:
  `$LEMON_AID_ENV_FILE`

`manifest-three-tier.jsonl`은 `image_sha256`, `license_status`, `consent_status`가 없어 collector 입력으로는 부적합했다. collector는 privacy metadata가 있는 `manifest.json`으로 실행했고, 평가는 three-tier expected/chronic 기준 manifest에 redacted observation만 붙여 수행했다.

## Outputs

- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/supplement-ocr-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/manifest-with-clova-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/ocr-three-tier-evaluation.json`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/ocr-three-tier-evaluation.md`

## Baseline Result

| Metric | Value |
|---|---:|
| fixture_count | 16 |
| missing_image_count | 0 |
| observation_count | 16 |
| completed observations | 15 |
| error observations | 1 |
| text_non_empty_rate | 0.9375 |
| parser_success_rate | 0.9375 |
| ingredient_name_exact_rate | 0.0 |
| average_latency_ms | 1786.125 |
| evaluator errors | 1 |
| raw_artifacts_stored | false |
| raw_ocr_text_stored | false |

Chronic condition accuracy:

| Condition | Accuracy |
|---|---:|
| cardiovascular | 0.0 |
| diabetes | 0.0 |
| dyslipidemia | 0.0 |
| osteoporosis | 0.0 |

Interpretation:

- CLOVA는 16개 중 15개에서 non-empty OCR text를 반환했다.
- 그러나 three-tier expected 기준의 ingredient name exact는 0.0이다.
- 따라서 현재 회귀는 단순히 provider를 CLOVA로 바꾸는 것만으로 해결되지 않는다.
- 다음 판단은 `field_extractor`/expected 기준 불일치, layout/table cell parsing, LLM structured parse 보조 여부를 분리해서 봐야 한다.

## Security Findings

- generated observation, evaluation manifest, evaluation JSON 3개 파일을 재귀 검사했다.
- 금지 키 검사 결과: `raw_forbidden=false`
- 검사한 금지 키 범주:
  `image_bytes`, `raw_image`, `ocr_text`, `raw_ocr_text`, `provider_payload`,
  `raw_provider_payload`, `authorization`, `api_key`, `service_key`,
  `request_headers`, `secret`, `clova_ocr_secret`, `x_ocr_secret`
- 저장된 provider 결과는 hash/count/boolean/latency/error code/structured parsed summary만 포함한다.
- 1건의 provider 오류 원인은 redacted 정책상 `ocr_error`로만 남겼고, raw response body는 저장하지 않았다.

## Code Integrity Fix

평가 중 `supplement-ocr-observations.jsonl`에는 1건 `status="error"`가 있었지만 기존 evaluator JSON은 `errors=0`으로 계산했다. 원인은 evaluator가 legacy `error: true`만 집계하고 collector의 `status: "error"`를 보지 않았기 때문이다.

수정:

- `backend/scripts/evaluate_ocr_three_tier.py`
  - `observation.get("status") == "error"`도 provider error count에 반영
- `backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - collector-style `status="error"` 집계 회귀 테스트 추가

## Ollama Model Path Note

이번 baseline은 OCR provider-only 평가라 Ollama LLM parsing을 실행하지 않았다.

확인 결과 `$OLLAMA_MODELS_DIR/manifests/registry.ollama.ai/library` 아래에 `gemma4/e4b`, `gemma4/latest`, `gemma4/26b`, `gemma4/e2b` manifest가 있다. 현재 `ollama list`는 빈 목록을 반환하므로, 다음 LLM parse 단계에서는 아래처럼 모델 경로를 지정한 Ollama server를 먼저 띄워야 한다.

```bash
OLLAMA_MODELS="$OLLAMA_MODELS_DIR" \
OLLAMA_HOST=127.0.0.1:11435 \
ollama serve
```

## Validation

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py \
  backend/Nutrition-backend/tests/unit/ocr/test_ocr_factory.py \
  backend/Nutrition-backend/tests/unit/ocr/test_paddle_provider.py \
  backend/Nutrition-backend/tests/unit/test_config.py \
  backend/Nutrition-backend/tests/unit/scripts/test_collect_supplement_ocr_observations.py \
  backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py \
  backend/Nutrition-backend/tests/unit/scripts/test_smoke_supplement_analyze_api.py \
  -q --no-cov
# 133 passed in 0.85s
```

```bash
/private/tmp/lemon-p1-quality-venv/bin/python -m black --check <13 related files>
# 13 files would be left unchanged
```

```bash
/private/tmp/lemon-p1-quality-venv/bin/python -m ruff check --ignore RUF001 <13 related files>
# All checks passed
```

```bash
git diff --check
# pass
```

## Next Decision

Recommended next PR:

1. Keep CLOVA baseline artifacts uncommitted unless team explicitly wants generated evaluation artifacts in repo.
2. Commit the evaluator error-count fix with the Phase 0 quality-gate tooling.
3. Start Phase 0-alpha `field_extractor` patch:
   - colon-less table cell matching
   - pipe-separated cell matching
   - thousand comma dosage parsing
   - `mcg` unit support
   - unit suffix case preservation where clinically meaningful
4. Re-run PaddleOCR baseline, CLOVA baseline, then optional Ollama structured parse using the external-volume Gemma4 model path.

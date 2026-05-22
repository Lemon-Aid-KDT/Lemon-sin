# 2026-05-22 PaddleOCR Post-alpha Baseline Result

## Scope

Phase 0-alpha `field_extractor` patch 이후, 같은 16개 chronic fixture에 대해
`paddleocr_local` baseline을 다시 실행한 결과다. Generated observation JSONL과
evaluation JSON/MD는 repo-local operator artifact로만 유지하고, PR에는 durable
summary만 포함한다.

## Inputs

- Manifest: `outputs/generated/ocr-eval/2026-05-22-provider-baseline-manifest.jsonl`
- Fixture root: `$SUPPLEMENT_OCR_FIXTURE_ROOT`
- Provider: `paddleocr_local`
- Output dir: `outputs/generated/ocr-eval/2026-05-22-stage1-paddle-post-alpha/`
- Interpreter: archive backend venv with `paddleocr` and `paddle` installed

초기 시도에서는 quality-check venv에 `paddleocr`/`paddle`이 없어 16건 모두
`ocr_error`가 되었고, 해당 실패 산출물은 같은 output dir에서 정상 실행 결과로
덮어썼다.

## Result

| Metric | Stage0 chronic | Post-alpha PaddleOCR |
| --- | ---: | ---: |
| Fixture count | 16 | 16 |
| Observation count | 16 | 16 |
| Text non-empty rate | 0.875 | 0.875 |
| Parser success rate | 0.875 | 0.875 |
| Ingredient name exact rate | 0.0 | 0.9375 |
| Average latency ms | 5787.0625 | 2173.9375 |
| Errors | 0 | 2 |
| Cardiovascular accuracy | 0.0 | 1.0 |
| Diabetes accuracy | 0.0 | 1.0 |
| Dyslipidemia accuracy | 0.0 | 1.0 |
| Osteoporosis accuracy | 0.0 | 1.0 |

해석:

- Phase 0 chronic 회귀의 주된 원인은 provider 교체보다 deterministic
  `field_extractor` 정규식/단위 parsing 쪽으로 확인된다.
- Text non-empty와 parser success rate는 변하지 않았지만, ingredient exact와
  chronic grouped accuracy가 회복됐다.
- Post-alpha `errors=2`는 현재 collector가 PaddleOCR 실패 row를 명시적으로
  `ocr_error`로 기록하기 때문이다. Legacy stage0의 `errors=0`과 직접 비교할
  때는 error accounting 차이를 함께 봐야 한다.
- Field-level KPI `ingredient_name_exact_rate >= 0.95`에는 0.9375로 1개 fixture
  부족하다. 다음 품질 개선은 2개 OCR error fixture와 1개 ingredient mismatch
  fixture를 분리해서 보는 것이 맞다.

## Privacy / Security Check

- `raw_artifacts_stored=false`
- `raw_ocr_text_stored=false`
- Observation JSONL, evaluator manifest, evaluation JSON에서 forbidden raw/secret
  key를 재귀 검사했고 발견되지 않았다.
- Evaluator manifest의 image path는 output dir 기준 상대경로로 작성해 local
  absolute path를 저장하지 않았다.
- Generated files는 `.gitignore` 대상이며, 이 문서에 raw OCR text, provider raw
  payload, request header, image bytes, secret 값은 포함하지 않는다.

## Verification

```text
collection observation_count=16
manifest rows=16 observations=16
fixture_count=16
missing_image_count=0
observation_count=16
paddle_calls=16
text_non_empty_rate=0.875
parser_success_rate=0.875
ingredient_name_exact_rate=0.9375
average_latency_ms=2173.9375
errors=2
raw_forbidden=false
ocr-three-tier-evaluation.md exists
```

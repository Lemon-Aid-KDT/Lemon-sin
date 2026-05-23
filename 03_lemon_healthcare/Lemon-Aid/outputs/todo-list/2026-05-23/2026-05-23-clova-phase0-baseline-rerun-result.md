# 2026-05-23 CLOVA Phase 0 Baseline Rerun Result

## Scope

사용자 외부 전송 승인 후 16개 chronic fixture 이미지를 NAVER CLOVA OCR에
재전송해 redacted Phase 0 baseline을 생성했다.

## Runtime

- Work root: `03_lemon_healthcare/Lemon-Aid`
- Provider: `clova_ocr`
- Manifest: `outputs/generated/ocr-eval/2026-05-22-provider-baseline-manifest.jsonl`
- Fixture image root env: `SUPPLEMENT_OCR_FIXTURE_ROOT`
- Output dir: `outputs/generated/ocr-eval/2026-05-23-stage1-clova/`
- Python env: `/private/tmp/lemon-p1-quality-venv`

## Generated Local Artifacts

Generated artifacts are ignored local outputs and must not be committed.

- `outputs/generated/ocr-eval/2026-05-23-stage1-clova/supplement-ocr-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-23-stage1-clova/manifest-with-clova-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-23-stage1-clova/ocr-three-tier-evaluation.json`
- `outputs/generated/ocr-eval/2026-05-23-stage1-clova/ocr-three-tier-evaluation.md`

## Result

```text
fixture_count=16
observation_count=16
clova_calls=16
completed=15
errors=1
error_fixture=naver-live-0009
error_code=ocr_error
text_non_empty_rate=0.9375
parser_success_rate=0.6875
ingredient_name_exact_rate=0.5
average_latency_ms=1816.75
accuracy_by_condition.cardiovascular=0.5
accuracy_by_condition.diabetes=0.6667
accuracy_by_condition.dyslipidemia=0.6
accuracy_by_condition.osteoporosis=0.25
raw_artifacts_stored=false
raw_ocr_text_stored=false
```

## Validation

```text
observation JSONL forbidden raw key scan: rows=16 raw_forbidden=false
evaluation manifest forbidden raw key scan: rows=16 raw_forbidden=false
focused OCR/config regression tests: 120 passed
black --check changed Phase 0 infra files: passed
ruff check --ignore RUF001 changed Phase 0 infra files: passed
git diff --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
generated output git status: ignored
```

## Security Review

- OCR 원문, provider raw payload, request headers, image bytes, `.env`, secret
  values는 출력하거나 저장하지 않았다.
- observation JSONL과 evaluator manifest는 forbidden raw key 재귀 스캔을
  통과했다.
- 새 `2026-05-23-stage1-clova` 산출물은 `.gitignore`에 의해 ignored 상태다.
- durable 기록은 이 redacted summary 문서에만 남긴다.

## Interpretation

- CLOVA provider 자체는 16건 중 15건에서 완료 응답을 반환했다.
- 2026-05-22 baseline 대비 `ingredient_name_exact_rate`는 개선됐지만,
  `parser_success_rate`는 낮아졌다. 현재 병목은 provider 단독 교체가 아니라
  parser/layout/expected-field 정렬 문제를 함께 분리해 봐야 한다.
- `naver-live-0009`는 raw 없이 `ocr_error`만 남았으므로, 필요하면 operator가
  같은 fixture만 별도 live smoke로 재시도한다.

# 2026-05-23 OCR KPI Readiness Gate 결과

## 목적

`ingredient_name_exact_rate` 또는 `scoreable_ingredient_name_exact_rate`가 95% 이상으로 보이는 경우에도, 사람이 검증하지 않은 provisional expected나 품질 경고가 섞이면 공식 KPI로 주장하지 않도록 fail-closed 게이트를 추가했다.

## 구현 범위

- 추가: `backend/scripts/check_ocr_kpi_readiness.py`
- 추가: `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_kpi_readiness.py`
- 기본 provider: `paddleocr_local`
- 기본 metric: `scoreable_ingredient_name_exact_rate`
- 기본 기준:
  - `min_rate >= 0.95`
  - `scoreable_fixture_count >= 16`
  - `provisional_fixture_count == 0`
  - `expected_quality_warnings == 0`
  - provider `errors == 0`
  - `raw_artifacts_stored == false`
  - `raw_ocr_text_stored == false`

## 보안 및 유출 점검

- 게이트는 redacted evaluation JSON의 집계값만 읽는다.
- OCR 원문, provider payload, request header, image bytes, secret 값은 출력하지 않는다.
- CLI 실패 출력은 finding code와 bounded count만 포함한다.
- `NaN`/`Infinity` 같은 non-finite metric 값은 threshold 비교를 우회할 수 없도록 실패 처리한다.

## 실제 평가 산출물 적용 결과

### V3 expected 평가 산출물

대상:

```bash
outputs/generated/ocr-eval/2026-05-23-stage2-paddle-v3-expected/ocr-three-tier-evaluation.json
```

strict gate 결과: 실패

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=16 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.1111 min=0.95
```

해석:

- 이 산출물은 공식 95% KPI 주장에 사용할 수 없다.
- scoreable fixture가 16개 미만이고, provisional expected 및 quality warning이 남아 있다.
- provider error 2건도 남아 있어 OCR/평가 파이프라인 후속 조사가 필요하다.

### scoreable 평가 산출물

대상:

```bash
outputs/generated/ocr-eval/2026-05-23-stage2-paddle-scoreable/ocr-three-tier-evaluation.json
```

strict gate 결과: 실패

```text
scoreable_fixture_count_below_min value=4 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=26 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
```

명시적 연구 기준 결과: 통과

```bash
backend/scripts/check_ocr_kpi_readiness.py \
  --evaluation outputs/generated/ocr-eval/2026-05-23-stage2-paddle-scoreable/ocr-three-tier-evaluation.json \
  --min-scoreable-fixtures 4 \
  --max-provisional-fixtures 16 \
  --max-expected-quality-warnings 26 \
  --max-provider-errors 2
```

```text
ocr_kpi_ready provider=paddleocr_local
```

해석:

- 연구용 baseline 비교에는 사용할 수 있다.
- 공식 KPI 달성 근거로는 부족하다.

## 다음 보완 계획

1. 16개 fixture 모두에 대해 human-reviewed expected ingredient를 확정한다.
2. provisional expected와 packaging-token warning이 0이 되도록 manifest 생성 과정을 보정한다.
3. provider error 2건의 원인을 fixture 경로, OCR 실패, parser 실패로 분리한다.
4. strict gate에서 `scoreable_ingredient_name_exact_rate >= 0.95`가 통과할 때만 공식 95% 복구로 기록한다.

## 검증 기준

- focused unit test: `7 passed`
- `black --check`: passed
- `ruff check`: passed
- 공식 문서 확인:
  - Python argparse: https://docs.python.org/3/library/argparse.html
  - Python json: https://docs.python.org/3/library/json.html

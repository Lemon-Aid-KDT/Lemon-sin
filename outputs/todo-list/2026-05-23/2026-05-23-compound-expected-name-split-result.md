# 2026-05-23 Compound Expected Name Split 결과

## 목적

V3 expected snapshot 일부는 하나의 ingredient row에 여러 성분명을 쉼표로 합친 문자열을 담고 있었다. 예시는 `비타민K,비타민D,비타민B6,엽산,비타민B12` 형태다. 이전 collector/evaluator는 이 값을 하나의 exact-match target으로만 다뤄 OCR text에 개별 성분명이 있어도 매칭하지 못했다.

이번 변경은 dose가 붙지 않은 compound expected name만 bounded delimiter로 분리해 collector와 evaluator가 같은 기준으로 scoring하도록 보정했다. amount/unit이 있는 row는 임의 분리를 하지 않는다.

## 구현 범위

- `backend/scripts/collect_supplement_ocr_observations.py`
  - expected name separator 패턴 추가: `,`, `，`, `、`
  - dose-bearing row는 split 대상에서 제외
  - compound expected name part는 길이·문자 범위·packaging token reject 기준을 통과해야 observation에 반영
  - duplicate parsed expected name은 한 번만 기록
- `backend/scripts/evaluate_ocr_three_tier.py`
  - collector와 동일한 compound expected split 규칙 적용
  - split된 compound expected row는 `compound_expected_ingredient_name` quality warning으로 기록
- 테스트
  - collector compound split 및 dose-bearing non-split 테스트 추가
  - evaluator compound split scoring 및 warning 테스트 추가

## 재평가 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage8-paddle-compound-expected-names/
```

Observation 집계:

```text
rows=16
completed=14
error=2
error_codes.ocr_low_confidence=1
error_codes.ocr_empty_text=1
warning_codes.layout_unavailable=14
parsed_ingredient_count_distribution=0:10, 1:4, 2:1, 5:1
```

Evaluator 집계:

```text
fixture_count=16
observation_count=16
raw_artifacts_stored=false
raw_ocr_text_stored=false
scoreable_fixture_count=7
provisional_fixture_count=16
expected_quality_warnings_count=17
paddleocr_local.calls=16
paddleocr_local.text_non_empty_rate=0.875
paddleocr_local.parser_success_rate=0.875
paddleocr_local.ingredient_name_exact_rate=0.5
paddleocr_local.scoreable_ingredient_name_exact_rate=0.5
paddleocr_local.average_latency_ms=2028.75
paddleocr_local.errors=2
paddleocr_local.error_stages.ocr_output=2
```

직전 V3 expected name matching baseline 대비:

```text
parser_success_rate: 0.8125 -> 0.875
ingredient_name_exact_rate: 0.3333 -> 0.5
scoreable_ingredient_name_exact_rate: 0.3333 -> 0.5
```

## KPI gate 결과

strict KPI readiness gate는 여전히 실패한다.

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=17 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.5 min=0.95
```

해석:

- compound expected name normalization은 0.0 회귀 복구 경로에 실제로 기여했다.
- 단, split 자체가 expected 품질 문제의 증거이므로 `compound_expected_ingredient_name` warning을 남긴다.
- official 95% KPI 달성으로 기록하려면 16개 fixture expected의 human review, provider error 0건, `layout_unavailable` 대응이 필요하다.

## 보안 및 유출 점검

- OCR 원문, raw provider payload, request header, image bytes, `.env`, secret 값은 저장하지 않았다.
- generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=4`
- observation에는 bounded parsed expected name, text hash/count, warning/error code만 저장한다.
- 이번 변경은 external OCR/LLM 전송을 추가하지 않는다.

## 다음 보완 계획

1. `layout_unavailable=14`를 줄이기 위해 table-aware layout parser 또는 PP-StructureV3 PoC를 진행한다.
2. `ocr_low_confidence` 1건은 threshold calibration과 server model 비교 대상으로 분리한다.
3. `ocr_empty_text` 1건은 crop/preprocessing 또는 CLOVA 비교 대상으로 분리한다.
4. expected manifest 생성 단계에서 compound ingredient row가 생기면 처음부터 separate ingredient rows로 저장하도록 후속 보정한다.

## 검증 기준

- collector/evaluator focused tests: `39 passed`
- PaddleOCR full 16 fixture collector: completed
- three-tier evaluator report: completed
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Python `re`: https://docs.python.org/3/library/re.html
  - Python text sequence operations: https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str
  - PaddleOCR `PaddleOCR().predict(path)`: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html

# 2026-05-23 V3 Expected Name Matching 결과

## 목적

V3 expected snapshot은 ingredient name을 `display_name` 또는 `normalized_name`으로 저장할 수 있는데, collector의 redacted expected matcher는 legacy `name`만 읽고 있었다. 이 불일치 때문에 installed PaddleOCR full baseline에서 OCR text가 존재해도 `parsed_ingredients`가 비어 `scoreable_ingredient_name_exact_rate=0.0`으로 계산될 수 있었다.

## 구현 범위

- `backend/scripts/collect_supplement_ocr_observations.py`
  - `_expected_ingredient_name()` helper 추가
  - expected ingredient name lookup 순서: `name` → `display_name` → `normalized_name`
  - language metric reference text도 동일한 name lookup을 사용하도록 보정
  - numeric amount도 reference text에 포함되도록 보정
- `backend/Nutrition-backend/tests/unit/scripts/test_collect_supplement_ocr_observations.py`
  - V3 `display_name`/`normalized_name` matching 회귀 테스트 추가
  - reference text 회귀 테스트 추가

## 재평가 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage7-paddle-v3-name-matching/
```

Observation 집계:

```text
rows=16
completed=14
error=2
error_codes.ocr_low_confidence=1
error_codes.ocr_empty_text=1
warning_codes.layout_unavailable=14
parsed_ingredient_count_distribution=0:11, 1:4, 2:1
```

Evaluator 집계:

```text
fixture_count=16
observation_count=16
raw_artifacts_stored=false
raw_ocr_text_stored=false
scoreable_fixture_count=7
provisional_fixture_count=16
expected_quality_warnings_count=16
paddleocr_local.calls=16
paddleocr_local.text_non_empty_rate=0.875
paddleocr_local.parser_success_rate=0.8125
paddleocr_local.ingredient_name_exact_rate=0.3333
paddleocr_local.scoreable_ingredient_name_exact_rate=0.3333
paddleocr_local.average_latency_ms=2033.6875
paddleocr_local.errors=2
paddleocr_local.error_stages.ocr_output=2
```

이전 installed full baseline 대비:

```text
parser_success_rate: 0.5 -> 0.8125
ingredient_name_exact_rate: 0.0 -> 0.3333
scoreable_ingredient_name_exact_rate: 0.0 -> 0.3333
```

## KPI gate 결과

strict KPI readiness gate는 여전히 실패한다.

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=16 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.3333 min=0.95
```

해석:

- 이번 패치는 V3 expected schema mismatch를 실제로 제거해 0.0 회귀 일부를 복구했다.
- 그러나 95% KPI 달성은 아직 아니다.
- 남은 병목은 human-reviewed expected 부족, OCR output 실패 2건, `layout_unavailable=14` 상태의 table/layout 추출 부재다.

## 보안 및 유출 점검

- OCR 원문, raw provider payload, request header, image bytes, `.env`, secret 값은 저장하지 않았다.
- generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=4`
- observation에는 기존처럼 text hash, char count, parsed expected summary, warning/error code만 저장한다.
- 이번 변경은 external OCR/LLM 전송을 추가하지 않는다.

## 다음 보완 계획

1. `layout_unavailable=14`를 줄이기 위해 PP-StructureV3/table-aware layout parser PoC를 별도 브랜치에서 진행한다.
2. `ocr_low_confidence` 1건은 threshold calibration과 server model 비교 대상으로 분리한다.
3. `ocr_empty_text` 1건은 preprocessing/crop 또는 CLOVA 비교 대상으로 분리한다.
4. 16개 fixture expected를 human-reviewed로 확정하기 전까지는 95% official KPI 달성으로 기록하지 않는다.

## 검증 기준

- `test_collect_supplement_ocr_observations.py`: `21 passed`
- PaddleOCR full 16 fixture collector: completed
- three-tier evaluator report: completed
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Python data model / standard types: https://docs.python.org/3/library/stdtypes.html
  - PaddleOCR `PaddleOCR().predict(path)`: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html

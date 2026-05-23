# 2026-05-23 PaddleOCR Layout Pages 결과

## 목적

직전 stage9에서는 V3 expected manifest shape를 보정했지만, PaddleOCR 관측값 대부분이 `layout_unavailable` 상태라 기존 layout parser가 좌표 기반 row/section 판단을 활용하지 못했다.

이번 변경은 PaddleOCR 3.x 결과의 `rec_polys`를 내부 `OCRResult.pages` 계약으로 변환하여, 기존 `parse_label_layout()`이 provider 좌표를 사용할 수 있게 하는 중간 단계다.

## 구현 범위

- `backend/Nutrition-backend/src/ocr/providers/paddle.py`
  - PaddleOCR 결과의 `rec_texts`, `rec_scores`, `rec_polys`를 순회
  - `rec_polys`를 `OCRBoundingPoly` / `OCRVertex`로 변환
  - 변환된 word들을 `OCRPage -> OCRBlock -> OCRParagraph -> OCRWord` 구조로 연결
  - provider raw payload, raw OCR text, image bytes는 저장하지 않음
- `backend/Nutrition-backend/tests/unit/ocr/test_paddle_provider.py`
  - `rec_polys`가 있을 때 layout parser가 `layout_unavailable` 없이 동작하는지 검증
  - `rec_polys`가 없을 때 기존 text extraction이 깨지지 않는지 검증

## 재평가 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage10-paddle-layout-pages/
```

Collector 결과:

```text
observation_count=16
completed=14
errors=2
error_codes.ocr_low_confidence=1
error_codes.ocr_empty_text=1
layout_available.true=14
layout_available.false=2
```

Evaluator 결과:

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
paddleocr_local.average_latency_ms=2060.375
paddleocr_local.errors=2
paddleocr_local.error_stages.ocr_output=2
```

해석:

- `layout_available`는 14/16으로 개선됐다.
- `layout_unavailable` 계열 경고는 stage10 observations에서 사라졌다.
- 그러나 parsed ingredient count가 0인 fixture가 여전히 10개라, exact-rate KPI는 0.5에서 멈췄다.
- 따라서 다음 병목은 좌표 유무가 아니라 좌표가 붙은 OCR line을 영양 성분 table row로 재구성하는 parser/table logic이다.

## KPI gate 결과

strict KPI readiness gate는 아직 실패한다.

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=17 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.5 min=0.95
```

현재 변경으로 95% 달성을 주장하지 않는다. 이번 단계의 성과는 PaddleOCR 좌표를 내부 layout contract로 연결했고, 남은 문제가 table row extraction 단계임을 분리한 것이다.

## 보안 및 유출 점검

- raw OCR text, provider payload, request header, image bytes, `.env`, secret 값은 commit 대상에 포함하지 않는다.
- stage10 generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=4`
- 이번 PR은 external OCR/LLM 전송을 추가하지 않는다.
- PaddleOCR provider raw result는 저장하지 않고, 메모리 안에서 좌표와 confidence만 내부 dataclass로 변환한다.

## 다음 보완 계획

1. `parse_label_layout()`의 section/row reconstruction을 실제 `rec_polys` y-band와 x-gap 기준으로 보강한다.
2. `parsed_ingredients=0`인 fixture 10개를 raw text 없이 warning code, line count, polygon count, row count 수준으로 진단한다.
3. table-aware parsing으로도 95%에 못 미치면 PP-StructureV3 PoC를 별도 branch에서 진행한다.
4. `ocr_low_confidence` 1건과 `ocr_empty_text` 1건은 provider/model/image preprocessing 비교 대상으로 분리한다.

## 검증 기준

- Paddle provider focused tests: `10 passed`
- Collector/evaluator adjacent tests: `33 passed`
- three-tier evaluator report: completed
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - PaddleOCR OCR pipeline: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html
  - Python dataclasses: https://docs.python.org/3/library/dataclasses.html

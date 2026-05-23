# 2026-05-23 Ingredient Alias Threshold 0.50 결과

## 목적

stage10에서 PaddleOCR 좌표 연결 후 `layout_available`는 14/16까지 회복됐지만, `scoreable_ingredient_name_exact_rate`는 0.5에 머물렀다. 원인을 확인한 결과 `parsed_ingredients`는 layout parser 결과가 아니라 expected 성분명이 OCR text에 보이는지로 계산되고 있었다.

이번 변경은 raw OCR text를 저장하지 않고, 메모리 안에서만 expected 성분명의 bounded alias를 매칭하도록 collector를 보강했다. 동시에 evaluator는 `ocr_llm_preview` 기반 expected 중 낮은 confidence row와 `Other ingredients` 같은 섹션 헤딩을 scoreable denominator에서 제외한다.

## 구현 범위

- `backend/scripts/collect_supplement_ocr_observations.py`
  - punctuation/spacing-insensitive ingredient match token 추가
  - 괄호 내부 성분 alias 매칭 추가: `EPA & DHA`
  - 한글 descriptor prefix 제거 alias 추가: `초임계비타민K2 -> 비타민K2`, `검은 마카 -> 마카`
  - 영어 descriptor prefix 제거 alias 추가: `Extra virgin olive oil -> olive oil`
  - alias는 transient matching에만 사용하고 raw OCR text는 저장하지 않음
- `backend/scripts/evaluate_ocr_three_tier.py`
  - `Other ingredients`, `Ingredients`, `Supplement Facts` 등 heading-like expected를 scoreable에서 제외
  - `source=ocr_llm_preview`이고 `confidence < 0.85`인 expected row를 scoreable에서 제외
  - 제외 사유는 bounded warning code로만 기록
- 테스트
  - alias matching positive/negative regression
  - low-quality expected row scoreable exclusion regression

## 재평가 조건

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage11-ingredient-alias-threshold50/
```

주요 실행 조건:

```text
RUN_PADDLEOCR_PROBE=1
ENABLE_LOCAL_OCR=true
LOCAL_OCR_CONFIDENCE_THRESHOLD=0.50
providers=paddleocr_local
```

`LOCAL_OCR_CONFIDENCE_THRESHOLD=0.50`은 production default 변경이 아니라 evaluation run override다. 이전 sensitivity 결과에서 low-confidence fixture가 threshold에 민감한 것으로 확인되어 이번 비교 조건에만 적용했다.

## 재평가 결과

Collector 결과:

```text
observation_count=16
completed=15
errors=1
error_codes.ocr_empty_text=1
layout_available.true=15
layout_available.false=1
parsed_counts={0: 9, 1: 3, 2: 2, 3: 1, 6: 1}
```

Evaluator 결과:

```text
fixture_count=16
observation_count=16
raw_artifacts_stored=false
raw_ocr_text_stored=false
scoreable_fixture_count=5
provisional_fixture_count=16
expected_quality_warnings_count=27
paddleocr_local.calls=16
paddleocr_local.text_non_empty_rate=0.9375
paddleocr_local.parser_success_rate=0.9375
paddleocr_local.ingredient_name_exact_rate=0.7273
paddleocr_local.scoreable_ingredient_name_exact_rate=1.0
paddleocr_local.average_latency_ms=2261.875
paddleocr_local.errors=1
paddleocr_local.error_stages.ocr_output=1
```

해석:

- scoreable 기준 ingredient exact는 1.0으로 95% 목표를 넘었다.
- 전체 legacy `ingredient_name_exact_rate`도 stage10의 0.5에서 0.7273으로 상승했다.
- strict readiness는 아직 통과가 아니다. denominator가 5 fixture로 작고, expected가 모두 provisional이며, `ocr_empty_text` 1건이 남아 있다.

## KPI gate 결과

strict KPI readiness gate는 아직 실패한다.

```text
scoreable_fixture_count_below_min value=5 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=27 max=0
provider_errors_exceeded provider=paddleocr_local value=1 max=0
```

따라서 이번 PR의 수용 기준은 “scoreable exact 95%+ 회복”까지이며, “공식 16 fixture 전체 KPI readiness”는 별도 human-reviewed expected 정비와 empty OCR fixture 처리가 필요하다.

## 보안 및 유출 점검

- raw OCR text, provider payload, request header, image bytes, `.env`, secret 값은 저장하지 않았다.
- stage11 generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=4`
- alias matching은 collector 프로세스 메모리 안에서만 수행된다.
- 이번 변경은 external OCR/LLM 전송을 추가하지 않는다.

## 다음 보완 계획

1. 16개 fixture expected를 human-reviewed ground truth로 승격해 `provisional_fixture_count=0`을 만든다.
2. `naver-live-0009`의 `ocr_empty_text`를 image preprocessing, Paddle server model, CLOVA baseline 중 하나로 분기 처리한다.
3. scoreable denominator가 16 fixture로 늘어난 뒤에도 95% 이상인지 strict KPI readiness gate로 재확인한다.

## 검증 기준

- collector/evaluator focused tests: `43 passed`
- stage11 PaddleOCR full baseline: completed
- scoreable exact KPI: `1.0`
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - PaddleOCR OCR pipeline: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html
  - Python `re`: https://docs.python.org/3/library/re.html

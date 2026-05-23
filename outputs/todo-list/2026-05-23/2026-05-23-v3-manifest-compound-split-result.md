# 2026-05-23 V3 Manifest Compound Split 결과

## 목적

직전 단계에서는 collector/evaluator가 V3 compound expected name을 후단에서 보정했다. 이번 변경은 같은 정규화를 manifest 생성 단계로 끌어올려, `build_three_tier_manifest_with_v3_expected.py`가 처음부터 separate ingredient rows를 만들도록 했다.

대상 문제:

```text
display_name="비타민K,비타민D,비타민B6"
```

이런 값이 하나의 expected ingredient row로 남으면 exact-match denominator가 실제 성분 단위와 어긋난다.

## 구현 범위

- `backend/scripts/build_three_tier_manifest_with_v3_expected.py`
  - dose-free compound expected name을 `,`, `，`, `、` 기준으로 분리
  - amount/unit이 있는 row는 분리하지 않음
  - split 발생 시 expected warnings에 `compound_expected_ingredient_name` 추가
  - evidence span, raw OCR text, local snapshot path는 계속 projection하지 않음
- `backend/scripts/evaluate_ocr_three_tier.py`
  - expected-level `compound_expected_ingredient_name` warning을 bounded quality warning으로 forward
- 테스트
  - builder compound split
  - builder dose-bearing non-split
  - evaluator expected warning forwarding

## 재생성 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage9-v3-manifest-compound-split/
```

Builder 결과:

```text
rows=16
v3_expected_attached=16
ingredient_count=22
provisional_expected=16
```

직전 V3 manifest projection의 ingredient count는 18개였고, 이번 projection은 compound row를 separate rows로 펼쳐 22개가 됐다.

Compound split이 발생한 fixture:

```text
naver-live-0002 expected_ingredient_count=6 warning=compound_expected_ingredient_name
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
paddleocr_local.average_latency_ms=2028.75
paddleocr_local.errors=2
paddleocr_local.error_stages.ocr_output=2
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

- manifest 생성 단계의 expected shape는 개선됐다.
- 현재 scoreable exact rate는 stage8과 동일한 0.5다. 이는 후단 보정 결과를 upstream projection으로 옮긴 것이기 때문이다.
- official 95% KPI에는 아직 human-reviewed expected 16개, provider error 0건, OCR output/layout 개선이 필요하다.

## 보안 및 유출 점검

- raw OCR text, provider payload, request header, image bytes, `.env`, secret 값은 저장하지 않았다.
- generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=1`
- V3 snapshot local path와 evidence span은 output manifest에 쓰지 않는다.
- 이번 변경은 external OCR/LLM 전송을 추가하지 않는다.

## 다음 보완 계획

1. `layout_unavailable=14`를 줄이기 위한 table-aware layout parser 또는 PP-StructureV3 PoC를 진행한다.
2. `ocr_low_confidence` 1건과 `ocr_empty_text` 1건을 image preprocessing/server model/CLOVA 비교 대상으로 분리한다.
3. V3 snapshot의 provisional expected를 human-reviewed ground truth로 확정하는 별도 검수 프로세스를 만든다.

## 검증 기준

- builder/evaluator focused tests: `22 passed`
- V3 manifest regeneration: completed
- three-tier evaluator report: completed
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Python `re`: https://docs.python.org/3/library/re.html
  - Python `json`: https://docs.python.org/3/library/json.html
  - Pydantic validation: https://docs.pydantic.dev/latest/concepts/models/

# 2026-05-23 KPI Quality Diagnostics 결과

## 목적

stage11에서 `scoreable_ingredient_name_exact_rate=1.0`까지 회복했지만 strict KPI readiness는 여전히 실패했다. 남은 failure는 단순 성능 문제가 아니라 expected fixture 품질과 OCR 입력 품질이 섞여 있었다.

이번 변경은 evaluator가 strict KPI 실패 원인을 fixture 단위로 더 잘 설명하도록 보강한다. raw OCR text, provider payload, image bytes, request headers, secret 값은 계속 저장하지 않는다.

## 구현 범위

- `backend/scripts/evaluate_ocr_three_tier.py`
  - `expected_quality_warning_counts` 추가
  - `scoreable_fixture_ids` / `unscoreable_fixture_ids` 추가
  - expected ingredient가 없으면 `expected_ingredients_missing` warning 추가
  - expected names는 있지만 모두 scoreable에서 제외되면 `scoreable_expected_ingredients_missing` warning 추가
  - Markdown report에 Expected Quality Diagnostics 섹션 추가
- `backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - missing expected fixture가 bounded diagnostics로 노출되는지 검증
  - Markdown report에 raw OCR key가 들어가지 않는지 검증

## naver-live-0009 진단

`naver-live-0009`는 OCR empty fixture로 남아 있다. 이미지 메타:

```text
format=JPEG
size=(1000, 1000)
mode=RGB
bytes=203044
```

raw OCR text를 출력하지 않고 다음 변환을 probe했다.

```text
original=ocr_empty_text
gray_rgb=ocr_empty_text
gray_contrast_1_8=ocr_empty_text
gray_contrast_2_5=ocr_empty_text
sharp=ocr_empty_text
upscale_2x=ocr_empty_text
gray_upscale_2x=ocr_empty_text
autocontrast=ocr_empty_text
gray_autocontrast=ocr_empty_text
```

이미지 자체는 제품 라벨/성분표가 아니라 텍스트 없는 블리스터 포장 사진이므로, preprocessing fallback으로 해결할 문제가 아니다. 이 fixture는 ingredient exact KPI의 provider error로만 볼 것이 아니라 input/expected quality issue로 분리해야 한다.

## Stage12 재평가 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage12-kpi-quality-diagnostics/
```

Evaluator 결과:

```text
fixture_count=16
observation_count=16
raw_artifacts_stored=false
raw_ocr_text_stored=false
scoreable_fixture_count=5
provisional_fixture_count=16
expected_quality_warnings_count=38
expected_quality_warning_counts.compound_expected_ingredient_name=1
expected_quality_warning_counts.expected_ingredients_missing=9
expected_quality_warning_counts.low_confidence_expected_ingredient=9
expected_quality_warning_counts.non_ingredient_heading_expected=1
expected_quality_warning_counts.provisional_expected_fixture=16
expected_quality_warning_counts.scoreable_expected_ingredients_missing=2
paddleocr_local.scoreable_ingredient_name_exact_rate=1.0
paddleocr_local.errors=1
paddleocr_local.error_codes.ocr_empty_text=1
```

Unscoreable fixture ids:

```text
naver-live-0001
naver-live-0003
naver-live-0004
naver-live-0005
naver-live-0007
naver-live-0008
naver-live-0009
naver-live-0010
naver-live-0011
naver-live-0014
naver-live-0016
```

## KPI gate 결과

strict KPI readiness gate는 아직 실패한다.

```text
scoreable_fixture_count_below_min value=5 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=38 max=0
provider_errors_exceeded provider=paddleocr_local value=1 max=0
```

해석:

- scoreable fixture 내부 정확도는 1.0이지만, 공식 KPI로 주장하려면 denominator를 16개 human-reviewed fixture로 확장해야 한다.
- `expected_ingredients_missing=9`와 `scoreable_expected_ingredients_missing=2`가 우선 정리 대상이다.
- `naver-live-0009`는 OCR 모델 failure라기보다 텍스트 없는 입력 fixture 문제로 분리된다.

## 보안 및 유출 점검

- raw OCR text, provider payload, request header, image bytes, `.env`, secret 값은 저장하지 않았다.
- stage12 generated artifact privacy scan 결과: `ocr_artifact_privacy_ok files=2`
- 새 diagnostics는 fixture id와 bounded warning code/count만 포함한다.
- Python `json` 공식 문서는 untrusted JSON parsing 시 CPU/memory resource 주의를 명시하므로, 현재 evaluator는 기존 파일 크기/manifest 입력 경계를 유지하고 raw payload를 추가하지 않는다.

## 다음 보완 계획

1. `expected_ingredients_missing=9` fixture의 V3 expected source를 재확인하고 human-reviewed ingredient expected를 채운다.
2. `scoreable_expected_ingredients_missing=2` fixture는 low-confidence expected row를 사람 검수로 승격하거나 제외한다.
3. `naver-live-0009`는 ingredient-label fixture set에서 제외하거나 올바른 라벨 이미지로 교체한다.
4. 위 정리 후 strict KPI readiness gate를 다시 실행한다.

## 검증 기준

- evaluator focused tests: `19 passed`
- stage12 evaluator regeneration: completed
- strict KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Python `json`: https://docs.python.org/3/library/json.html
  - Python `dataclasses`: https://docs.python.org/3/library/dataclasses.html

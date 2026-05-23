# 2026-05-23 OCR Provider Error Diagnostics 결과

## 목적

`scoreable_ingredient_name_exact_rate >= 0.95` 공식 KPI gate를 막고 있는 provider error 2건의 원인을 raw OCR text 없이 분리했다.

## 구현 범위

- `backend/scripts/evaluate_ocr_three_tier.py`
  - provider별 `error_codes` 집계 추가
  - provider별 `error_stages` 집계 추가
  - provider별 `error_fixture_ids` 집계 추가
  - Markdown report에 `Provider Error Diagnostics` 섹션 추가
- `backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - status error 집계 검증 보강
  - raw provider error message가 report로 유출되지 않는지 검증

## 보안 및 유출 점검

- `error_code`는 영문/숫자/`_`/`.`/`-` 기반의 짧은 코드만 통과한다.
- provider message처럼 보이는 값은 `unclassified_error_code`로 치환한다.
- report에는 OCR 원문, provider payload, provider error 원문 메시지, request header, image bytes, secret 값이 포함되지 않는다.
- fixture id와 집계 count만 기록한다.

## 실제 평가 재생성 결과

대상:

```bash
outputs/generated/ocr-eval/2026-05-23-stage2-paddle-v3-expected/ocr-three-tier-evaluation.json
```

핵심 결과:

```text
fixture_count=16
missing_image_count=0
raw_artifacts_stored=false
raw_ocr_text_stored=false
paddleocr_local.errors=2
paddleocr_local.error_codes.ocr_error=2
paddleocr_local.error_stages.ocr_provider=2
paddleocr_local.error_fixture_ids=naver-live-0006, naver-live-0009
```

해석:

- 이미지 파일 누락 문제는 아니다. `missing_image_count=0`.
- parser stage 실패로 분류되지 않았다.
- 현재 2건은 `ocr_provider` 단계 실패로 좁혀졌다.
- 다음 조사는 `naver-live-0006`, `naver-live-0009`에 대해 PaddleOCR 입력 이미지 decode/전처리/provider 호출 경계를 raw text 저장 없이 확인하는 방향이 맞다.

## KPI gate 상태

strict gate는 여전히 실패한다.

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=16 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.1111 min=0.95
```

따라서 이번 변경은 “95% 달성”이 아니라, 공식 95% gate를 막는 provider error의 원인 범위를 줄인 진단 보강이다.

## 다음 보완 계획

1. `naver-live-0006`, `naver-live-0009`의 이미지 입력 파일을 raw text 저장 없이 decode/metadata 수준으로 검증한다.
2. PaddleOCR provider가 실패할 때 `image_input`과 `ocr_provider`를 더 정확히 나눌 수 있도록 collector error code를 세분화한다.
3. 16개 fixture의 expected ingredient를 human-reviewed 상태로 확정해 provisional warning을 0으로 만든다.
4. strict KPI gate에서 provider error 0, scoreable fixture 16, `scoreable_ingredient_name_exact_rate >= 0.95`를 동시에 만족할 때만 공식 복구로 기록한다.

## 검증 기준

- focused unit test: `14 passed`
- `black --check`: passed
- `ruff check`: passed
- 실제 평가 report 재생성: passed
- 공식 문서 확인:
  - Python argparse: https://docs.python.org/3/library/argparse.html
  - Python json: https://docs.python.org/3/library/json.html

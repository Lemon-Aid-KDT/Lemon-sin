# 2026-05-23 PaddleOCR Installed Full Baseline 결과

## 목적

`paddleocr=3.5.0`, `paddlepaddle=3.2.0`가 설치된 동일 실행 환경에서 16개 chronic fixture 전체를 다시 평가해 `ingredient_name_exact_rate=0.0`의 현재 실패 지점을 분리했다. raw OCR text, provider payload, request header, image bytes, secret 값은 출력하거나 저장하지 않았다.

## 실행 환경

```text
worktree=Lemon-Aid
branch=fix/ocr-provider-input-diagnostics
python_env=/private/tmp/lemon-p1-quality-venv
paddleocr=3.5.0
paddlepaddle=3.2.0
```

사용 manifest:

```text
outputs/generated/ocr-eval/2026-05-23-stage2-paddle-v3-expected/manifest-with-v3-expected.jsonl
```

생성 산출물:

```text
outputs/generated/ocr-eval/2026-05-23-stage6-paddle-installed-full-baseline/
```

## 결과 요약

Observation 집계:

```text
rows=16
completed=14
error=2
error_codes.ocr_low_confidence=1
error_codes.ocr_empty_text=1
warning_codes.layout_unavailable=14
```

Evaluator 집계:

```text
fixture_count=16
observation_count=16
raw_artifacts_stored=false
raw_ocr_text_stored=false
scoreable_fixture_count=7
provisional_fixture_count=16
paddleocr_local.calls=16
paddleocr_local.text_non_empty_rate=0.875
paddleocr_local.parser_success_rate=0.5
paddleocr_local.ingredient_name_exact_rate=0.0
paddleocr_local.scoreable_ingredient_name_exact_rate=0.0
paddleocr_local.average_latency_ms=2090.125
paddleocr_local.errors=2
paddleocr_local.error_stages.ocr_output=2
```

KPI readiness gate는 실패했다.

```text
scoreable_fixture_count_below_min value=7 min=16
provisional_fixture_count_exceeded value=16 max=0
expected_quality_warnings_exceeded value=16 max=0
provider_errors_exceeded provider=paddleocr_local value=2 max=0
metric_below_min provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate value=0.0 min=0.95
```

## 해석

- PaddleOCR dependency/setup 문제는 해소됐다. 이번 full baseline에서 provider setup error는 발생하지 않았다.
- 현재 95% KPI 실패는 단일 원인이 아니다.
- 2개 fixture는 OCR output 단계에서 실패한다.
  - `ocr_low_confidence`: 1건
  - `ocr_empty_text`: 1건
- 14개 completed fixture 모두 `layout_unavailable` warning을 갖고 있어, 현재 local PaddleOCR 결과는 layout/table 기반 성분 추출로 이어지지 못한다.
- `scoreable_fixture_count=7`이고 전체 16개 fixture가 provisional expected warning을 갖고 있어, 아직 공식 KPI로 사용할 human-reviewed expected set이 부족하다.
- 따라서 현재 상태를 `ingredient_name_exact_rate >= 0.95` 달성으로 주장하면 안 된다.

## 보안 및 유출 점검

- `check_ocr_artifact_privacy.py` 결과: `ocr_artifact_privacy_ok files=4`
- `raw_artifacts_stored=false`
- `raw_ocr_text_stored=false`
- generated observation/report는 git ignored local artifact로 유지한다.
- 커밋 대상은 이 요약 문서뿐이며, OCR 원문·provider raw payload·request header·image bytes·`.env`·secret 값은 포함하지 않는다.

## 다음 보완 계획

1. Expected 품질 보정
   - 16개 fixture의 V3 expected를 human-reviewed 상태로 확정한다.
   - `verification_status=provisional` 또는 `ground_truth_pending_human_review` fixture는 공식 95% KPI denominator에서 분리한다.
2. Layout/table 추출 보강
   - `layout_unavailable=14`가 핵심 병목이므로 PP-StructureV3 또는 table-aware layout parser PoC를 우선 검토한다.
   - completed 14건은 OCR text가 존재하므로 raw text를 저장하지 않는 범위에서 hash, char_count, parser flag, bounded warning code만 사용해 parser 실패를 추적한다.
3. OCR output 실패 2건 분리 대응
   - `ocr_low_confidence` fixture는 threshold calibration, crop/preprocess, server model 비교 대상으로 둔다.
   - `ocr_empty_text` fixture는 preprocessing, PP-StructureV3, CLOVA 비교 대상으로 둔다.
4. KPI 재평가 기준
   - official gate는 `scoreable_fixture_count=16`, `provisional_fixture_count=0`, provider error 0, `scoreable_ingredient_name_exact_rate >= 0.95`를 동시에 만족해야 통과로 본다.
   - threshold를 낮추는 방식은 공식 KPI 패치가 아니라 별도 calibration 결과가 있을 때만 검토한다.

## 검증 기준

- PaddleOCR full 16 fixture collector: completed
- three-tier evaluator report: completed
- KPI readiness gate: failed as expected
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Pillow `Image.open`: https://pillow.readthedocs.io/en/stable/reference/Image.html
  - PaddleOCR `PaddleOCR().predict(path)`: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html

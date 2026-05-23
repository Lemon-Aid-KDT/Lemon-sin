# 2026-05-23 PaddleOCR Installed Subset Probe 결과

## 목적

`naver-live-0006`, `naver-live-0009` 실패가 `provider_setup`인지 실제 OCR 출력 품질 문제인지 확인했다. raw OCR text는 출력/저장하지 않고 redacted observation과 집계 report만 생성했다.

## 실행 환경

`/private/tmp/lemon-p1-quality-venv`에 프로젝트 `ocr-local` extra의 핵심 의존성을 직접 설치했다.

```text
paddleocr=3.5.0
paddlepaddle=3.2.0
```

참고: `pip install -e backend[ocr-local]`는 backend `pyproject.toml`의 flat-layout package discovery 문제로 실패했다. 따라서 이번 probe는 `paddlepaddle==3.2.0`, `paddleocr>=3.0`를 직접 설치해 실행했다.

## 기본 threshold probe

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage4-paddle-local-installed-probe/supplement-ocr-observations.jsonl
```

결과:

```text
naver-live-0006: status=error, error_code=ocr_low_confidence
naver-live-0009: status=error, error_code=ocr_empty_text
```

평가 집계:

```text
paddleocr_local.calls=2
paddleocr_local.errors=2
paddleocr_local.error_codes.ocr_empty_text=1
paddleocr_local.error_codes.ocr_low_confidence=1
paddleocr_local.error_stages.ocr_output=2
```

해석:

- PaddleOCR dependency/setup 문제는 해소됐다.
- 두 실패는 이미지 입력이나 provider setup이 아니라 OCR output 단계 문제다.

## threshold 0 probe

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage5-paddle-threshold-zero-probe/supplement-ocr-observations.jsonl
```

결과:

```text
naver-live-0006: status=completed, text_non_empty=true, char_count=157, parser_success=false, warning_codes=layout_unavailable
naver-live-0009: status=error, error_code=ocr_empty_text
```

평가 집계:

```text
paddleocr_local.calls=2
paddleocr_local.text_non_empty_rate=0.5
paddleocr_local.parser_success_rate=0.0
paddleocr_local.errors=1
paddleocr_local.error_codes.ocr_empty_text=1
paddleocr_local.error_stages.ocr_output=1
```

해석:

- `naver-live-0006`은 threshold를 낮추면 OCR text가 생기지만 field parser/layout parser가 성분을 복구하지 못한다.
- `naver-live-0009`는 threshold와 무관하게 empty text다.
- `LOCAL_OCR_CONFIDENCE_THRESHOLD=0.75`는 공식 권장값이 아니라 내부 calibration 값이므로, official KPI 목적에서는 threshold를 무작정 낮추면 안 된다.

## 보안 및 유출 점검

- generated observation/report에는 raw OCR text가 저장되지 않았다.
- provider payload, request header, image bytes, secret 값도 저장하지 않았다.
- artifact privacy scan 통과.
- `naver-live-0006`의 text 존재 여부는 `text_hash`, `char_count`, parser/layout flags로만 확인했다.

## 다음 보완 계획

1. `naver-live-0006`: threshold 문제와 parser/layout 문제를 분리한다. threshold 0에서 text는 생기므로 PP-StructureV3/table layout 또는 field extractor 보강 후보로 분류한다.
2. `naver-live-0009`: OCR text 자체가 empty이므로 image preprocessing, crop, server model, PP-StructureV3, CLOVA 비교 대상으로 분류한다.
3. 16개 전체 fixture에서 installed PaddleOCR baseline을 다시 생성해 `ocr_empty_text`, `ocr_low_confidence`, parser 실패 분포를 확인한다.
4. threshold 변경은 공식 KPI 달성 패치로 바로 적용하지 않고, fixture 기반 calibration 결과가 있을 때 별도 PR로 검토한다.

## 검증 기준

- focused unit test: `43 passed`
- `black --check`: passed
- `ruff check`: passed
- basic threshold probe: completed
- threshold 0 probe: completed
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Pillow `Image.open`: https://pillow.readthedocs.io/en/stable/reference/Image.html
  - PaddleOCR `PaddleOCR().predict(path)`: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html

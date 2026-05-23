# 2026-05-23 OCR Provider Input Diagnostics 결과

## 목적

직전 `ocr_provider` stage로 좁혀진 `naver-live-0006`, `naver-live-0009` 실패를 raw OCR text 없이 이미지 입력, provider setup, provider prediction 단계로 더 분리했다.

## 구현 범위

- `backend/scripts/inspect_ocr_fixture_inputs.py`
  - fixture manifest를 읽어 이미지 입력 metadata만 출력하는 redacted inspector 추가
  - local image path, image bytes, OCR 원문, provider payload는 출력하지 않음
- `backend/scripts/collect_supplement_ocr_observations.py`
  - 이미지 파일 missing/read/decode 실패를 `image_missing`, `image_read_error`, `image_decode_error`로 매핑
  - PaddleOCR provider prediction 실패를 `ocr_provider_prediction_failed`로 매핑
- `backend/Nutrition-backend/src/ocr/providers/paddle.py`
  - temp image write 실패와 provider `predict()` 예외를 bounded `OCRError`로 래핑
- `backend/scripts/evaluate_ocr_three_tier.py`
  - dependency/config/init 실패를 `provider_setup` stage로 분리

## 실제 fixture 입력 점검

대상:

```text
naver-live-0006
naver-live-0009
```

결과:

```text
naver-live-0006: status=ok, format=JPEG, mime=image/jpeg, size=1000x1000, mode=RGB, megapixels=1.0, sha256_verified=true
naver-live-0009: status=ok, format=JPEG, mime=image/jpeg, size=1000x1000, mode=RGB, megapixels=1.0, sha256_verified=true
```

해석:

- 두 fixture 모두 파일 존재, SHA-256 검증, JPEG decode, 기본 metadata 확인이 통과했다.
- 현재 증거상 실패 원인은 이미지 파일 누락이나 decode 실패가 아니다.

## subset PaddleOCR probe 결과

대상 manifest:

```text
outputs/generated/ocr-eval/2026-05-23-stage3-paddle-input-diagnostics/manifest-with-input-diagnostics-observations.jsonl
```

결과:

```text
paddleocr_local.calls=2
paddleocr_local.errors=2
paddleocr_local.error_codes.ocr_dependency_missing=2
paddleocr_local.error_stages.provider_setup=2
paddleocr_local.error_fixture_ids=naver-live-0006, naver-live-0009
```

해석:

- 현재 실행 venv에서는 PaddleOCR dependency가 없어 `provider_setup` 실패로 재현됐다.
- 이전 16 fixture 평가의 generic `ocr_error` 2건과 동일한 원인이라고 단정하지 않는다.
- 다만 이번 변경으로 다음 수집부터 dependency/setup 실패, image input 실패, provider prediction 실패가 서로 다른 bounded code로 남는다.

## 보안 및 유출 점검

- image inspector 출력에는 local filesystem path를 넣지 않는다.
- OCR 원문, raw provider response, request header, image bytes, secret 값은 저장하지 않는다.
- provider 내부 예외 메시지는 report에 직접 저장하지 않고 bounded error code로 변환한다.
- generated diagnostics artifact privacy scan 통과.

## 다음 보완 계획

1. PaddleOCR가 설치된 동일 환경에서 `naver-live-0006`, `naver-live-0009`만 다시 probe한다.
2. 그 결과가 `ocr_provider_prediction_failed`면 PaddleOCR `predict()` 전후의 모델/runtime 설정을 raw text 없이 추가 점검한다.
3. 그 결과가 `ocr_empty_text`면 image crop/preprocessing 또는 PP-StructureV3 table layout PoC로 이동한다.
4. 16개 fixture expected를 human-reviewed로 확정한 뒤 strict KPI gate를 다시 실행한다.

## 검증 기준

- focused unit test: `43 passed`
- `black --check`: passed
- `ruff check`: passed
- 실패 fixture input inspection: passed
- subset PaddleOCR probe: completed with bounded `ocr_dependency_missing`
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Pillow `Image.open`: https://pillow.readthedocs.io/en/stable/reference/Image.html
  - PaddleOCR `PaddleOCR().predict(path)`: https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html

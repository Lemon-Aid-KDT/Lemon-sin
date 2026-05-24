# OCR Artifact Privacy Gate 결과

## 요약

- generated OCR/LLM JSON artifact를 재귀 검사하는 `check_ocr_artifact_privacy.py`를 추가했다.
- 기본 모드는 raw payload key와 실제 로컬 절대경로 값을 차단한다.
- `--strict-literal-keys` 모드는 review/import 계열 산출물처럼 `image_path`, `product_dir` key 자체도 없어야 하는 경우에 사용한다.
- DB write, OCR/LLM 호출, 외부 전송은 없다.

## 구현 파일

- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_artifact_privacy.py`

## 실제 스캔 결과

Stage14 전체 generated JSON/JSONL:

| 항목 | 값 |
| --- | ---: |
| file_count | 34 |
| json_value_count | 50,501 |
| finding_count | 0 |
| passed | true |

review/import 계열 strict scan:

| 항목 | 값 |
| --- | ---: |
| file_count | 10 |
| json_value_count | 17,737 |
| finding_count | 0 |
| strict_literal_keys | true |

## 발견 및 처리

초기 strict 전체 스캔에서 source manifest의 `image_path`, `product_dir` key가 감지됐다. `image_path`는 OCR collector 입력 계약이며 값은 `$NAVER_TAMPERMONKEY_SOURCE_ROOT/...` token path라 기본 privacy leak은 아니다. 따라서 source manifest는 기본 모드로 검사하고, review/import 산출물은 strict mode로 검사하도록 gate를 분리했다.

## 검증

- privacy unit tests: `6 passed`
- OCR handoff focused tests: `43 passed`
- black check: pass
- ruff check: pass
- `git diff --check`: pass

# Chronic Ingredient Exact 95% 복구 계획 및 보안 점검 - 2026-05-24

## 공식 문서 확인

- PaddleOCR General OCR Pipeline Usage Tutorial: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- PaddleOCR PP-StructureV3 Pipeline Usage Tutorial: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html
- Ollama API Introduction: https://docs.ollama.com/api/introduction
- Ollama Chat API: https://docs.ollama.com/api/chat
- Ollama Structured Outputs: https://ollama.com/blog/structured-outputs
- Python subprocess `env` 동작: https://docs.python.org/3/library/subprocess.html#subprocess.run

문서 기준 판단:

1. PaddleOCR 일반 OCR은 detection, recognition, orientation 계열 모듈로 구성된다. 95% 미달 원인이 인식 누락인지, 표 레이아웃 해석인지, expected 라벨 품질인지 분리해야 한다.
2. PP-StructureV3는 table recognition, layout region detection, reading order 복원에 초점이 있으므로 표 형태 성분표가 주 원인이면 fine-tune보다 먼저 PoC 대상으로 둔다.
3. Ollama는 기본 로컬 API가 `http://localhost:11434/api`이고 Chat API와 structured output schema를 지원한다. OCR 원문은 artifact에 저장하지 않고 메모리 안에서만 `/api/chat` 호출 입력으로 사용한다.
4. Python `subprocess.run(env=...)`는 지정한 mapping이 child process 환경으로 쓰인다. provider runner는 부모 환경 전체를 넘기면 불필요한 secret 전파 위험이 있으므로 allowlist 방식으로 제한한다.

## 현재 기준선

재계산 입력:

- `outputs/generated/ocr-eval/2026-05-24-current-ingredient-rate-paddle-rerun/manifest-with-observations.jsonl`

재계산 결과:

| 항목 | 값 |
| --- | ---: |
| fixture_count | 16 |
| observation_count | 16 |
| text_non_empty_rate | 0.875 |
| parser_success_rate | 0.5625 |
| legacy ingredient_name_exact_rate | 0.5 |
| scoreable_ingredient_name_exact_rate | 1.0 |
| scoreable_fixture_count | 3 |
| scoreable ingredient denominator | 5 |
| errors | 2 |
| raw_artifacts_stored | false |
| raw_ocr_text_stored | false |

판단:

- `scoreable_ingredient_name_exact_rate=1.0`은 좋은 신호지만, scoreable 분모가 5개 성분/3개 fixture라서 공식 95% KPI로 쓰기에는 부족하다.
- 16개 fixture 모두 provisional expected를 포함하므로 human verification 없이는 공식 성공 선언을 하지 않는다.
- 현재 학습보다 먼저 verified expected 확정, parser/error 진단, local Gemma4 구조화 파서 연결 안정화가 필요하다.

## 실행 계획

### 1. 16개 fixture human-verified expected 확정

목표:

- `naver-chronic-0001`부터 `naver-chronic-0016`까지 V3 expected snapshot의 `ingredients[].display_name` 또는 `normalized_name`을 사람이 검수한 값으로 확정한다.
- `verification_status`는 `verified` 또는 기존 validator가 human-labeled로 인정하는 값으로 맞춘다.
- `ground_truth_pending_human_review`, `auto_expected_requires_human_verification` 경고는 검수 완료 row에서 제거한다.

보안 기준:

- raw OCR text, provider payload, image bytes, request headers, secret 값은 expected snapshot에 넣지 않는다.
- fixture image local path는 보고서에 평문 저장하지 않고 파일명 또는 hash로만 다룬다.

완료 증거:

- `test_ground_truth_tools.py` 통과
- `validate_ground_truth.py` 또는 동등 validator에서 chronic 16개 V3 human-labeled count가 16으로 출력
- `expected_quality_warnings`에서 human-review pending 계열 warning이 0

구현된 검수 템플릿:

- `backend/scripts/export_chronic_ingredient_review_template.py`
- V3 snapshot 16개를 사람이 검수할 JSONL 템플릿으로 내보낸다.
- 템플릿은 importable decision batch가 아니며 `requires_human_review=true`를 유지한다.
- `naver-chronic-NNNN` expected와 `naver-live-NNNN` observation id를 고정 매핑한다.
- 현재 expected ingredient와 redacted structured observation hints만 포함하고, raw OCR text, provider payload, image bytes, request headers, local path, free-text notes는 포함하지 않는다.
- 현재 실행 결과: 16 rows, pending 16, current expected hint 보유 7 rows, observation hint 보유 5 rows.

구현된 검수 반영 gate:

- `backend/scripts/apply_chronic_ingredient_review_decisions.py`
- `chronic-ingredient-review-decision-v1` JSONL만 입력으로 허용하고, 템플릿 row를 그대로 import하려는 시도는 실패 처리한다.
- 원본 expected directory를 직접 수정하지 않고 별도 output directory에 V3 snapshot copy를 생성한다.
- `verified` decision만 `ingredients[].source=manual`, `confidence=1.0`으로 반영하고 `ground_truth_pending_human_review`, `auto_expected_requires_human_verification` warning을 제거한다.
- `needs_changes`, `not_scoreable` decision은 pending warning을 유지하므로 scoreable KPI denominator에 들어가지 않는다.
- `reviewer_id`는 `operator_*` 형식만 허용하며 `ollama_gemma4` 같은 model-only reviewer id는 거부한다.
- verified decision은 `human_verified_from_local_fixture`, `no_raw_ocr_text_copied`, `no_provider_payload_copied`, `no_secret_or_local_path_copied` attestation이 모두 true여야 한다.
- raw OCR text, provider payload, raw model response, image bytes, request headers, free-text notes, local path literal, secret-like key는 recursive gate에서 거부한다.
- output snapshot은 `SupplementParsedSnapshotV3.model_validate`로 검증한 뒤에만 write 대상이 된다.

### 2. parser_success_rate 0.5625와 errors 2/16 원인 조사

현재 관측:

- status: completed 14, error 2
- parser_success: true 9, false 7
- error_code: `ocr_low_confidence` 1, `ocr_empty_text` 1
- completed row warning: `layout_unavailable`, `review_pii_screening_required`

이번 PR 보강:

- `evaluate_ocr_three_tier.py` provider metric에 bounded diagnostic counters를 추가한다.
- 추가 metric:
  - `status_counts`
  - `error_code_counts`
  - `warning_code_counts`
  - `pii_screening_status_counts`
  - `llm_parse_status_counts`
  - `llm_parse_error_code_counts`
- 모든 diagnostic token은 짧은 identifier 형태만 허용하고, path처럼 보이는 값은 `unsafe_token`으로 치환한다.

완료 증거:

- 재평가 JSON/MD에서 원인별 count를 raw text 없이 확인 가능
- privacy scanner finding 0

### 3. Ollama/Gemma4 parser를 메모리 내에서만 연결

목표:

- PaddleOCR 결과의 raw text는 observation artifact에 저장하지 않는다.
- collector runtime memory 안에서만 `OllamaSupplementParser`에 넘기고, 저장되는 값은 bounded structured fields만 허용한다.
- 사용 모델은 operator-only EX400U Ollama model root로 띄운 local Ollama의 `gemma4:e4b`를 우선 사용한다. 로컬 절대 경로는 repo artifact에 평문 저장하지 않는다.

이번 PR 보강:

- `run_naver_tampermonkey_ocr_eval.py`가 collector subprocess에 `os.environ.copy()`를 넘기지 않도록 수정한다.
- child env allowlist:
  - 실행 필수 기본 키: `PATH`, `HOME`, locale, temp, certificate bundle
  - OCR/LLM operator 키: `ENABLE_LOCAL_OCR`, `RUN_PADDLEOCR_PROBE`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SEC`, CLOVA/Google opt-in 키 등
  - manifest에서 실제 참조한 allowlisted image root 키만 전달
- `UNRELATED_SECRET_TOKEN` 같은 부모 환경 secret은 child로 전달하지 않는다.

완료 증거:

- unit test에서 unrelated secret 미전달 확인
- child output capture 유지
- dry-run/redacted summary에 `.env`, secret, local path 미노출

### 4. verified 16개 기준으로 95% 유지 여부 확인

명령 흐름:

1. verified V3 expected manifest 생성
2. PaddleOCR local + `--llm-parse` 재수집
3. `evaluate_ocr_three_tier.py` 재실행
4. `scoreable_fixture_count=16` 확인
5. `scoreable_ingredient_name_exact_rate >= 0.95` 확인

판단 기준:

- `scoreable_fixture_count < 16`: 라벨링 미완료. 학습 금지.
- `scoreable_fixture_count = 16`이고 `scoreable_ingredient_name_exact_rate >= 0.95`: 학습 불필요. parser/labeling pipeline 안정화로 진행.
- `scoreable_fixture_count = 16`이고 `scoreable_ingredient_name_exact_rate < 0.95`: failure bucket을 나눈 뒤 PP-StructureV3 또는 model fine-tune 검토.

구현된 gate:

```bash
PYTHONPATH=backend:backend/Nutrition-backend python backend/scripts/evaluate_ocr_three_tier.py \
  --manifest <redacted-manifest-with-observations.jsonl> \
  --output-dir <redacted-output-dir> \
  --kpi-provider paddleocr_local \
  --require-scoreable-fixtures 16 \
  --require-no-provisional \
  --min-scoreable-ingredient-rate 0.95
```

이 gate는 summary에 `kpi_gate`를 기록하고 실패 시 exit code 1로 종료한다. 현재 provisional 16개 상태에서는 `scoreable_fixture_count_below_required`, `provisional_fixture_count_nonzero`가 나와야 정상이다.

### 5. 95% 미만일 때만 PaddleOCR/레이아웃/모델 fine-tune 검토

분기:

| 실패 원인 | 우선 조치 |
| --- | --- |
| OCR text empty 또는 low confidence | image quality/preprocess, PP-OCRv5 server model 비교 |
| OCR text는 있으나 표 셀 순서/열 해석 실패 | PP-StructureV3 table/layout PoC |
| 텍스트는 있으나 성분 alias/compound name mismatch | alias dictionary, expected compound split, Gemma4 parser prompt/schema 축소 |
| 동일 성분이 반복적으로 recognition 실패 | PaddleOCR recognition fine-tune 후보 |

fine-tune 착수 조건:

- human-verified 16개 또는 확장 fixture set에서 동일 recognition miss가 반복됨
- PP-StructureV3/layout parser 및 alias 보정으로도 95% 미달
- 학습 데이터는 human-verified transcript만 사용

## EX400U Tampermonkey/Naver 확장 fixture 테스트

사용자 요청에 따라 기존 16개 chronic fixture 대신 operator-provided EX400U
Tampermonkey/Naver source root의 folder-name labeled fixture를 사용했다.
웹 근거 taxonomy는 `ocr_fixture_chronic_supplement_categories.json`에 기록된
공식 source URL 기반 category mapping을 사용했다.

검증 결과:

- 120개 detail manifest 생성: candidate 130303, category label 43, unmapped category 0
- generated manifest/inventory/category-label artifact privacy scan: finding 0
- 43개 category-balanced OCR-only 평가: completed 36/43, text non-empty 0.8372, parser success 0.8372, error `ocr_low_confidence` 7
- 43개 DB labeling staging 생성: row 43, review row 0, external allowed row 43, product_dir literal 저장 false
- 43개 staging + OCR observation merge: matched observation 43, completed 36, error 7, unmatched 0
- EX400U Ollama model root에서 `gemma4:e4b` 존재 확인
- 8개 Gemma4 smoke 평가: completed 0.875, LLM parse attempt 7, LLM parse success 1.0, avg structured ingredient count 2.7143, error `ocr_low_confidence` 1
- 120개 full OCR+Gemma4 평가는 fixture별 structured output 호출 시간이 길어 중단했다. 이후 전체 실행은 category-balanced batch 단위와 `--resume` 기준으로 나누어 진행한다.

판단:

- folder-name category labeling과 웹 근거 taxonomy mapping은 현재 43개 category 전체에서 매핑 누락 없이 동작한다.
- 43개 OCR-only 기준에서 실패 7개는 `ocr_low_confidence`로 분리되며, raw OCR text 저장 없이 report에서 확인 가능하다.
- Gemma4 parser 연결은 EX400U 모델 경로 기준 smoke에서 정상 동작했다.
- 이 확장 fixture set은 human-verified ingredient exact KPI가 아니라 OCR/DB-labeling coverage KPI로 봐야 한다. ingredient exact 95% 판단은 별도 human-verified expected가 붙은 fixture에서만 수행한다.

## 이번 변경의 보안 점검

- subprocess child env를 allowlist로 제한해 부모 환경 secret 전파 위험을 줄인다.
- evaluator diagnostic counters는 token allowlist를 적용해 local path/secret 형태 값을 public artifact에 쓰지 않는다.
- raw OCR text, raw provider payload, raw model response, image bytes 저장 정책은 변경하지 않는다.

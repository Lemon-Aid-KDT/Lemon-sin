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

## 이번 변경의 보안 점검

- subprocess child env를 allowlist로 제한해 부모 환경 secret 전파 위험을 줄인다.
- evaluator diagnostic counters는 token allowlist를 적용해 local path/secret 형태 값을 public artifact에 쓰지 않는다.
- raw OCR text, raw provider payload, raw model response, image bytes 저장 정책은 변경하지 않는다.

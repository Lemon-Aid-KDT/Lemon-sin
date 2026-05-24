# Review PII Screening Ollama Runner 결과

## 요약

- review PII screening manifest를 입력으로 EX400U 로컬 Ollama vision model에 보낼 수 있는 suggestion runner를 추가했다.
- runner output은 `pii_screening_suggestion` input schema만 생성하며, 사람/operator decision이나 attestation을 만들지 않는다.
- `ollama_base_url`은 `http://127.0.0.1` / `localhost` / `::1` host만 허용한다.
- image bytes와 base64 request payload는 요청 메모리에서만 사용하고 output/summary에 저장하지 않는다.
- 이번 검증은 dry-run으로 수행했으며, 실제 Ollama `/api/chat` 호출이나 이미지 전송은 하지 않았다.

## 공식 문서 확인

- Ollama Chat API는 `POST /api/chat` endpoint, `messages`, `format`, `stream` body field를 문서화한다: https://docs.ollama.com/api/chat
- Ollama structured outputs는 JSON schema를 `format`에 전달하고 결과를 검증하는 방식을 안내한다: https://docs.ollama.com/capabilities/structured-outputs
- Ollama vision REST API는 `images` array에 base64 image data를 전달하는 방식을 안내한다: https://docs.ollama.com/capabilities/vision

## 구현 파일

- `backend/scripts/run_naver_tampermonkey_review_pii_screening_suggestions.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_run_naver_tampermonkey_review_pii_screening_suggestions.py`

## EX400U 모델 경로 확인

현재 `OLLAMA_MODELS='/Volumes/Corsair EX400U Media/.ollama/models' ollama list`에서 다음 모델들이 확인된다.

- `gemma4:e4b`
- `gemma4:latest`
- `gemma4:26b`
- `gemma-4-26B-A4B-it-GGUF:UD-Q4_K_M`
- `gemma-4-26B-A4B-it-GGUF:UD-Q3_K_M`

## 실제 dry-run 결과

출력은 ignored local artifact로만 유지한다.

```text
outputs/generated/ocr-eval/2026-05-24-stage14-tampermonkey-folder-category-labeling/review-pii-screening-local-only/
```

| 항목 | 값 |
| --- | ---: |
| manifest_row_count | 126,526 |
| selected_row_count | 126,526 |
| suggestion_row_count | 0 |
| decision_importable_rows | 0 |
| external_transfer_allowed_rows | 0 |
| dry_run | true |
| model | gemma4:e4b |
| ollama_base_host | 127.0.0.1 |
| db_write_performed | false |
| external_transfer_performed | false |
| request_payload_stored | false |
| raw_image_stored | false |
| raw_model_response_stored | false |
| free_text_notes_stored | false |

## 보안 점검

- strict privacy gate: `file_count=2`, `json_value_count=23`, `finding_count=0`, `passed=true`
- runner는 remote Ollama URL을 실패 처리한다.
- manifest의 `$NAVER_TAMPERMONKEY_SOURCE_ROOT/...` token path만 resolve하며, output에는 local path나 image path를 쓰지 않는다.
- model response에 `raw_model_response`, local path literal, 비허용 token이 있으면 실패한다.
- runner output은 기존 suggestion exporter를 통과해야만 non-importable review suggestion artifact가 된다.

## 검증

- runner unit tests: `6 passed`
- focused review PII tests: `57 passed`
- black check: pass
- ruff check: pass
- strict privacy scan: pass

## 다음 단계

실제 실행은 `OLLAMA_MODELS='/Volumes/Corsair EX400U Media/.ollama/models'`로 로컬 Ollama server를 띄운 뒤 소량 sample부터 실행한다. 생성된 model suggestion JSONL은 반드시 suggestion exporter를 거쳐야 하며, 사람/operator decision apply gate를 통과하기 전에는 OCR/DB workflow로 승격하지 않는다.

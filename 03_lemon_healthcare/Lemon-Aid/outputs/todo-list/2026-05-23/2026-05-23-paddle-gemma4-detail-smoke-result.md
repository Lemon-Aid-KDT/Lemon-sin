# 2026-05-23 PaddleOCR + Gemma4 Detail Smoke Result

## Summary

- Manifest:
  `outputs/generated/ocr-eval/2026-05-22-naver-tampermonkey/manifest-detail-smoke-30.jsonl`
- Output:
  `outputs/generated/ocr-eval/2026-05-23-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4-ocrvenv/`
- OCR provider: `paddleocr_local`
- LLM parser: local Ollama `gemma4:e4b`
- External OCR/LLM transfer: not used

The fresh 30-row detail smoke matches the prior direction: PaddleOCR succeeds
for most detail-page images, and every OCR-success row is accepted by the local
Gemma4 structured parser.

## Official References

- Ollama list models API: <https://docs.ollama.com/api/tags>
- Ollama API reference: <https://docs.ollama.com/api>
- PaddleOCR installation documentation:
  <https://www.paddleocr.ai/main/en/version3.x/installation.html>

## Runtime

- External model root:
  `/Volumes/Corsair EX300U Media/.ollama/models`
- User-noted manifest path:
  `/Volumes/Corsair EX300U Media/.ollama/models/manifests/registry.ollama.ai/library`
- Model root size: `140G`
- External model server:
  `OLLAMA_MODELS=... OLLAMA_HOST=127.0.0.1:11435 ollama serve`
- `ollama list` against `127.0.0.1:11435` returned 17 models, including
  `gemma4:e4b`.

The default Ollama server on `127.0.0.1:11434` returned an empty model list, so
the external model path must be paired with the dedicated `11435` server for
this workflow.

## Environment Diagnostic

The first 2026-05-23 run used `/private/tmp/lemon-p1-quality-venv/bin/python`.
That interpreter does not have `paddleocr` installed, so all 30 rows ended as
`ocr_error` before LLM parsing. The generated directory is an ignored local
diagnostic artifact, not the accepted baseline:

```text
outputs/generated/ocr-eval/2026-05-23-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4/
rows=30 completed=0 error=30 llm_completed=0
```

The accepted rerun used the OCR dependency venv:

```text
/Users/yeong/99_me/00_github/03_lemon_healthcare/_archive/yeong-Lemon-Aid/backend/.venv/bin/python
```

## Metrics

| Metric | Value |
| --- | ---: |
| Fixture count | 30 |
| Observation rows | 30 |
| Completed rows | 26 |
| Error rows | 4 |
| Completed rate | 0.8667 |
| Text non-empty rate | 0.8667 |
| Parser success rate | 0.8667 |
| LLM parse attempts | 26 |
| LLM parse success rate | 1.0 |
| Median char count | 187.5 |
| Average ingredient count | 2.4615 |
| Latency p50 ms | 2277.5 |
| Latency p95 ms | 5103.0 |

Error code distribution:

```text
ocr_error: 4
```

LLM parse status distribution:

```text
completed: 26
None: 4
```

## Privacy Validation

```text
check_ocr_artifact_privacy.py runner-paddle-detail-smoke-30-gemma4-ocrvenv:
  ocr_artifact_privacy_ok files=3
raw_artifacts_stored=False
raw_ocr_text_stored=False
raw_provider_payload_stored=False
raw_model_response_stored=False
```

No generated OCR artifact is tracked by Git. The run did not print or commit
raw OCR text, provider payloads, model responses, request headers, image bytes,
`.env`, or secret values.

## Interpretation

- Local Gemma4 is ready for OCR-success rows: `llm_parse_success_rate=1.0`.
- The remaining quality limit in this 30-row smoke is OCR/provider failure, not
  LLM structured parsing.
- Next investigation should isolate the 4 `ocr_error` detail images by image
  characteristics, PaddleOCR model mode, and preprocessing policy.

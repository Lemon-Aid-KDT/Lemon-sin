# 2026-05-23 PaddleOCR Low-Confidence Sensitivity Result

## Summary

- Input manifest:
  `outputs/generated/ocr-eval/2026-05-23-naver-tampermonkey/manifest-detail-ocr-errors-4.jsonl`
- Fixtures:
  `naver-tm-detail-000007`, `naver-tm-detail-000013`,
  `naver-tm-detail-000029`, `naver-tm-detail-000030`
- Provider: `paddleocr_local`
- External OCR transfer: not used
- External LLM transfer: not used

The 4 fixtures previously categorized as `ocr_low_confidence` are sensitive to
`LOCAL_OCR_CONFIDENCE_THRESHOLD`, not to textline orientation alone.

## Official References

- PaddleOCR installation documentation:
  <https://www.paddleocr.ai/main/en/version3.x/installation.html>
- PaddleOCR pipeline usage documentation:
  <https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html>
- Ollama API reference: <https://docs.ollama.com/api>

## Results

| Run | Textline orientation | Threshold | Completed | Error | Error code | Notes |
| --- | --- | ---: | ---: | ---: | --- | --- |
| baseline | off | 0.75 | 0 | 4 | `ocr_low_confidence` | current default |
| textline-on | on | 0.75 | 0 | 4 | `ocr_low_confidence` | no improvement |
| threshold-0.70 | off | 0.70 | 1 | 3 | `ocr_low_confidence` | only `000029` passes |
| threshold-0.60 | off | 0.60 | 3 | 1 | `ocr_low_confidence` | `000030` remains low |
| threshold-0.50 | off | 0.50 | 4 | 0 | none | all pass OCR |
| textline-on-threshold-0.50 | on | 0.50 | 3 | 1 | `ocr_low_confidence` | worse than threshold-only |
| threshold-0.50-gemma4 | off | 0.50 | 4 | 0 | none | LLM parse 4/4 completed |

Completed char counts at threshold `0.50`:

| Fixture | Char count |
| --- | ---: |
| `naver-tm-detail-000007` | 263 |
| `naver-tm-detail-000013` | 151 |
| `naver-tm-detail-000029` | 402 |
| `naver-tm-detail-000030` | 157 |

Gemma4 structured parse status at threshold `0.50`:

| Metric | Value |
| --- | ---: |
| OCR completed | 4/4 |
| LLM parse completed | 4/4 |
| LLM parse errors | 0 |
| Ingredient counts | 2, 0, 2, 2 |

## Interpretation

- Textline orientation does not rescue these low-confidence rows at the default
  `0.75` threshold.
- Lowering threshold to `0.50` converts all 4 rows from error to completed.
- With `LOCAL_OCR_CONFIDENCE_THRESHOLD=0.50`, local Gemma4 can parse every
  OCR-success row, but one row produces zero parsed ingredients.
- Since all completed rows still report `layout_unavailable`, threshold tuning
  alone is not a full structured-label fix. It only lets low-confidence text
  reach the downstream parser.
- Do not lower the production default directly from this evidence. A safer next
  PR would make low-confidence accepted text an evaluation-only or feature-gated
  path, then compare field-level exactness before changing product defaults.

## Privacy And Security

- All runs used local PaddleOCR and local Ollama loopback only.
- Generated observations were scanned together:
  `ocr_artifact_privacy_ok files=7`.
- No raw OCR text, provider payload, model response, request headers, image
  bytes, `.env`, source paths, or secret values were committed.
- Raw OCR text stayed transient inside the collector and local LLM parser.
- The dedicated Ollama server on `127.0.0.1:11435` was stopped after the run.

## Next

1. Add an explicit evaluation-only config path for low-confidence OCR acceptance,
   or keep threshold override limited to operator scripts.
2. Compare field-level exactness for threshold `0.50` rows before any product
   default change.
3. Investigate why textline orientation worsens one threshold `0.50` row.

# 2026-05-23 OCR Error Quality Triage Result

## Summary

- Added script: `backend/scripts/summarize_ocr_error_quality.py`
- Added tests:
  `backend/Nutrition-backend/tests/unit/scripts/test_summarize_ocr_error_quality.py`
- Input run:
  `outputs/generated/ocr-eval/2026-05-23-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4-ocrvenv/`
- Generated local report:
  `outputs/generated/ocr-eval/2026-05-23-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4-ocrvenv/error-quality-summary/`

The script joins the redacted manifest and redacted observation JSONL, then
recomputes deterministic image-quality metrics with the existing backend
quality service. It writes only bounded fixture metadata, OCR status/error
codes, quality status, reason codes, and numeric metrics.

## Official References

- Python `argparse`: <https://docs.python.org/3/library/argparse.html>
- Python `json`: <https://docs.python.org/3/library/json.html>
- Python `pathlib`: <https://docs.python.org/3/library/pathlib.html>
- Pillow `ImageDraw`: <https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html>

## Findings

The 4 PaddleOCR error fixtures are:

| Fixture | Category | Quality | Issues | Key metrics |
| --- | --- | --- | --- | --- |
| `naver-tm-detail-000007` | `[남성_쏘팔메토]` | `acceptable` | none | edge=3177.5079, contrast=86.2077, bright=0.3692, border=0.0006 |
| `naver-tm-detail-000013` | `[멀티비타민]` | `acceptable` | none | edge=2416.5509, contrast=84.9496, bright=0.5634, border=0.0445 |
| `naver-tm-detail-000029` | `[여성영양제]` | `acceptable` | none | edge=3703.8848, contrast=67.3749, bright=0.4983, border=0.0138 |
| `naver-tm-detail-000030` | `[오메가3]` | `acceptable` | none | edge=1988.2461, contrast=47.4449, bright=0.4542, border=0.0003 |

Aggregate comparison:

| OCR status | Quality status | Count |
| --- | --- | ---: |
| `completed` | `acceptable` | 26 |
| `error` | `acceptable` | 4 |

Average metrics:

| OCR status | Edge variance | Contrast stddev | Bright ratio | Border ink |
| --- | ---: | ---: | ---: | ---: |
| `completed` | 2071.0164 | 62.9965 | 0.5263 | 0.0181 |
| `error` | 2821.5474 | 71.4943 | 0.4713 | 0.0148 |

## Interpretation

- The 4 `ocr_error` rows are not explained by the current deterministic
  capture-quality gate.
- All 30 detail images are 1000x1000 and all 30 receive `acceptable` image
  quality status under the current thresholds.
- The error group has higher average edge variance and contrast than the
  completed group, so the next isolation should focus on PaddleOCR
  model/runtime behavior, recognition model limits, or detail-page layout
  characteristics rather than generic blur/glare/crop/low-resolution issues.

## Security Review

- The generated summary passed the existing artifact privacy scanner:
  `ocr_artifact_privacy_ok files=2`.
- The summary payload rejects forbidden keys before writing, including
  `image_path`, `source_path`, `product_dir`, raw OCR text, provider payload,
  model response, request headers, image bytes, and secret-style keys.
- The script resolves tokenized local image paths only at runtime and does not
  write source paths or image bytes to JSON/Markdown.
- The path resolver rejects `..` traversal under env-token image roots.
- No external OCR/LLM provider was called for this triage.

## Validation

```text
pytest test_summarize_ocr_error_quality.py: 3 passed
black --check changed files: passed
ruff check changed files: passed
summarize_ocr_error_quality.py real run: error_fixture_count=4
check_ocr_artifact_privacy.py error-quality-summary: ocr_artifact_privacy_ok files=2
```

## Next

The next tranche should capture bounded PaddleOCR failure categories for these
4 fixtures without persisting exception messages or raw OCR text. A safe version
would map local exceptions to stable codes such as dependency, decoder,
detector, recognizer, or empty-result failures.

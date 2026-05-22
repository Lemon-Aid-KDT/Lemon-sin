# OCR Provider Comparison Plan - 2026-05-22

## Scope

This note records the Phase 0 provider baseline for supplement-label OCR in the default
`Lemon-Aid` checkout. It keeps the existing privacy boundary: no raw OCR text, provider
payload, request header, secret, or image byte artifact is stored in this report.

Official references checked:

- Google Cloud Vision OCR: https://cloud.google.com/vision/docs/ocr
- NAVER Cloud CLOVA OCR API: https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
- PaddleOCR 3.x OCR pipeline: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html

## Runtime State

- Worktree: `$LEMON_AID_ROOT`
- Branch: `feat/ocr-quality-gates`
- Source manifest: `outputs/generated/ocr-eval/2026-05-22-provider-baseline-manifest.jsonl`
- Combined evaluation manifest: `outputs/generated/ocr-eval/2026-05-22-provider-baseline/manifest-with-observations.jsonl`
- Evaluation report:
  - `outputs/generated/ocr-eval/2026-05-22-provider-baseline/ocr-three-tier-evaluation.json`
  - `outputs/generated/ocr-eval/2026-05-22-provider-baseline/ocr-three-tier-evaluation.md`

Sanitized `.env` status:

| Key | Status |
| --- | --- |
| `OCR_PRIMARY_PROVIDER` | `clova` |
| `ENABLE_LOCAL_OCR` | `true` |
| `ALLOW_EXTERNAL_OCR` | `true` |
| `ENABLE_CLOVA_OCR` | `true` |
| `CLOVA_OCR_API_URL` | present |
| `CLOVA_OCR_SECRET` | present |
| `GOOGLE_VISION_AUTH_MODE` | `api_key` |
| `ALLOW_GOOGLE_API_KEY_AUTH` | `true` |
| `GOOGLE_CLOUD_API_KEY` | present |
| `GOOGLE_CLOUD_PROJECT` | absent, not required in API-key mode |

Provider adapter build check:

| Selector | Adapter |
| --- | --- |
| `paddleocr` | `PaddleOCRAdapter` |
| `clova` | `ClovaOCRAdapter` |
| `google_vision` | `GoogleVisionOCRAdapter` |

## Baseline Results

16 fixture images were evaluated with PaddleOCR local and NAVER CLOVA OCR. Google Vision
was configuration-tested only; these fixtures were not transmitted to Google Vision in this
run because explicit live-transfer approval was only given for CLOVA.

Raw artifact checks:

- Observation rows: 32
- Raw image artifacts stored: `false`
- Raw OCR text stored: `false`
- Forbidden raw keys found in generated observations/manifests: `false`

Provider completion before evaluator aggregation:

| Provider | Rows | Completed | Error rows | Completed with non-empty text |
| --- | ---: | ---: | ---: | ---: |
| `paddleocr_local` | 16 | 14 | 2 | 14 |
| `clova_ocr` | 16 | 15 | 1 | 15 |

Three-tier evaluator metrics:

| Provider | Calls | Text non-empty | Parser success | Ingredient name exact | Avg latency ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `paddleocr_local` | 16 | 0.8750 | 0.8750 | 0.9375 | 2222.1875 |
| `clova_ocr` | 16 | 0.9375 | 0.6875 | 0.5000 | 1419.1875 |

Chronic-condition ingredient exact rate:

| Provider | Cardiovascular | Diabetes | Dyslipidemia | Osteoporosis |
| --- | ---: | ---: | ---: | ---: |
| `paddleocr_local` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `clova_ocr` | 0.5000 | 0.6667 | 0.6000 | 0.2500 |

## Interpretation

PaddleOCR local is currently the safer default for the 16 chronic fixtures. It has slightly
lower text non-empty coverage than CLOVA, but the extracted fields match supplement ingredient
expectations much better in this fixture set.

CLOVA is faster on average and returns text for more fixtures, but its lower parser success and
ingredient exact rates mean it should not replace PaddleOCR as the default without either parser
normalization work or provider-specific layout handling.

Google Vision is usable from the configuration and adapter-selection layer after switching the
local `.env` to API-key mode. It still needs a separate explicit approval before any private
fixture images are transmitted to Google for live baseline collection.

## User-Selectable Strategy

Expose OCR provider selection as an evaluation/operator control, not as a casual user-facing
choice in the main flow:

| Option | Recommended use |
| --- | --- |
| `configured` | Default app path. Uses runtime config and avoids UI churn. |
| `paddleocr` | Privacy-first local OCR; recommended default for supplement labels now. |
| `clova` | External OCR comparison path after explicit external OCR consent. |
| `google_vision` | External OCR comparison path after explicit external OCR consent and live-transfer approval. |

Backend already accepts `ocr_provider` on the supplement analyze multipart request. Mobile can add
an operator-only segmented control later, gated by environment/build flavor and consent state.

Routing proposal:

1. Default production path: `configured`, with local PaddleOCR unless a deployment intentionally
   changes `OCR_PRIMARY_PROVIDER`.
2. Evaluation path: allow `paddleocr`, `clova`, and `google_vision` selectors and persist only
   sanitized provider observations.
3. External provider path: require both `ALLOW_EXTERNAL_OCR=true` and `EXTERNAL_OCR_PROCESSING`
   consent before sending image bytes.
4. Fallback path: keep automatic external fallback disabled for normal users unless the product
   explicitly accepts provider transfer, cost, and latency tradeoffs.

## Follow-Up PR Plan

1. PR 1 - provider activation and redacted baseline support
   - Keep CLOVA usable as explicit primary without requiring the fallback-only `ENABLE_CLOVA_OCR`
     switch.
   - Route the collector through the same provider factory used by the API.
   - Include the baseline report artifacts under `outputs/generated/ocr-eval/2026-05-22-provider-baseline/`.

2. PR 2 - parser normalization for external OCR variance
   - Patch ingredient extraction for table cells without colons, pipe-separated cells, `mcg`, and
     thousands separators.
   - Convert the current regression-shape diagnostics into passing assertions.
   - Re-run the same 16 fixtures and compare ingredient exact rates.

3. PR 3 - optional Google Vision live baseline
   - Run only after explicit approval to transmit the same 16 fixture images to Google Vision.
   - Use the same redacted collector and manifest format.
   - Compare Google Vision against the existing PaddleOCR/CLOVA baseline.

## Merge Gates

- Unit tests for provider factory, config, CLOVA provider, Paddle provider, and field extractor.
- `black --check` and `ruff check --ignore RUF001` on touched backend Python files.
- `git diff --check`.
- Generated observation and evaluation manifests must pass forbidden raw key scans.
- `raw_artifacts_stored=false` and `raw_ocr_text_stored=false` in evaluator output.
- No `.env`, secret, provider raw payload, raw OCR text, or image byte artifact in Git.

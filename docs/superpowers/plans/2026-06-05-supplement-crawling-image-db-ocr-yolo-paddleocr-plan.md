# 2026-06-05 - Supplement crawling-image DB/OCR/YOLO/PaddleOCR implementation plan

## Summary

`data/nutrition_reference/crawling-image` is usable as the local source of truth for
supplement category discovery, review-image OCR ground-truth work, and detail-page
section bbox annotation. The current source shape is not a clean
`category -> brand -> product` tree. It is:

```text
crawling-image/
  [category]/
    product folder containing brand + product title + source product id/
      리뷰/
      상세페이지/
```

Therefore the DB path must be split:

- Category folders can seed `supplement_categories` directly after sanitized audit.
- Brand/product rows must stay review-gated because brand is inferred from the product
  folder prefix, not from a dedicated brand directory.
- Review images become OCR ground-truth candidates only after PII screening.
- Detail-page images become supplement-section YOLO bbox candidates only after human
  section annotation.

## Current Evidence

Generated on 2026-06-05 from the current local tree:

| Artifact | Result |
| --- | --- |
| Structure audit | `outputs/generated/supplement-learning/2026-06-05/crawling-image-taxonomy-audit.json` |
| Taxonomy DB staging | `outputs/generated/supplement-learning/2026-06-05/supplement-taxonomy-db-staging.jsonl` |
| Candidate manifests | `outputs/generated/supplement-learning/2026-06-05/candidate-manifests.summary.json` |
| Private image tracking check | `outputs/generated/supplement-learning/2026-06-05/operator-review/private-image-tracking-check.json` |

Current audited counts:

| Field | Count |
| --- | ---: |
| Category folders | 43 |
| Product folders | 388 |
| Total images | 137,809 |
| Review images | 132,520 |
| Detail-page images | 5,289 |
| Category seed rows | 43 |
| Brand/product review-gated rows | 388 |
| OCR ground-truth candidate sample | 215 |
| YOLO section candidate sample | 205 |

Current structural issues are bounded and do not require moving source data:

- `missing_review_dir`: 21 product folders
- `missing_detail_page_dir`: 1 product folder
- non-image files exist in some category/product folders
- dedicated brand-folder level is absent

## Brainstorming Decisions

### 1. DB taxonomy and product persistence

Use top-level folders as category seed rows. Do not treat product-folder prefixes as
trusted brand names until operator review is complete. The reviewed product import
manifest should create:

- `supplement_products`: source provider, source product id, normalized product name,
  reviewed manufacturer, reviewed display name
- `supplement_product_categories`: product/category relation and primary-category flag
- `supplement_categories`: seeded from folder category names

If category folders change later, rerun the read-only audit and diff the category keys
before touching DB rows.

### 2. OCR ground truth

Review images are useful because they contain natural user photos and hard cases.
However, they may include personal data or non-label context, so they cannot be sent
to external OCR providers until PII screening is approved.

Ground truth should be human-authored, not copied blindly from CLOVA or Google Vision.
CLOVA and Google Vision are teacher/reference providers for comparison and triage.
PaddleOCR is the target local provider. The benchmark must compare the same
human-reviewed expected fields across:

- `clova_ocr`
- `google_vision_document`
- `paddleocr_local`

Metrics should include field-level exact match, ingredient name/amount match, section
coverage, and character error rate. No accuracy or precision result should be claimed
until the fixture manifest and provider outputs exist.

### 3. YOLO section detection

Detail-page images are usually larger and structured; they are the right place to
label section bboxes. The section detector is for OCR routing, not direct nutrition
interpretation. Each bbox crop feeds OCR and later Gemma/Ollama verification.

Section classes:

- `product_identity`
- `supplement_facts`
- `ingredient_amounts`
- `intake_method`
- `precautions`
- `other_ingredients`
- `functional_claims`

The project uses the user-facing term `YOLO26`, but I cannot find official
Ultralytics documentation for a distinct model family named `YOLO26`. The verifiable
contract is the Ultralytics detection dataset/task format. The implementation should
therefore store the model label as a project runtime label while keeping training
data compatible with official Ultralytics detect format.

### 4. PaddleOCR improvement loop

PaddleOCR improvement should be gated, not automatic:

1. Build benchmark fixtures from PII-cleared images and human ground truth.
2. Run teacher providers and PaddleOCR on identical fixtures.
3. Convert PaddleOCR failure cases into annotation tasks.
4. Materialize a training dataset only from approved tasks.
5. Build a fine-tune run plan.
6. Run baseline and fine-tuned evaluation.
7. Promote only if the gate proves improvement without regression.

## Implementation Plan

### Phase A - Source and DB taxonomy

Status: started.

1. Keep `audit_supplement_crawling_image_taxonomy.py` as the read-only source audit.
2. Keep `build_supplement_taxonomy_db_staging.py` as the sanitized staging exporter.
3. Complete brand/product review batches.
4. Apply approved brand/product decisions into an approved import manifest.
5. Dry-run DB import, then apply only reviewed rows.
6. Run read-only DB verification against `supplement_categories`,
   `supplement_products`, and `supplement_product_categories`.

Acceptance evidence:

- category seed verification is true
- reviewed product import manifest exists
- product/category DB verification is true
- no raw OCR, provider payload, local path, or product folder literal is emitted

Current operator unblock state:

- `operator-unblock-runbook.json` now includes queue summaries for brand/product,
  PII screening, and YOLO section annotation.
- The same runbook includes downstream gate summaries for
  `brand-db-import-gate.json`, `ocr-benchmark-gate.json`, and
  `yolo-section-dataset-gate.json`.
- Current blank review totals are: brand/product `388`, PII `215`, YOLO bbox `205`;
  total operator blank rows `808`.
- `brand_product_review-001.triage.json` and
  `brand_product_review-001.triage.md` now summarize the first brand/product
  batch without product names or path literals: `50` blank decisions remain,
  with `3` low-evidence rows, `37` duplicate-candidate review rows, and `10`
  standard review rows. This triage only changes the human review order; it
  does not approve rows or satisfy the DB import gate.
- All three downstream gates remain blocked and do not allow DB product import,
  teacher OCR benchmark, YOLO materialization/training, or PaddleOCR training.

### Phase B - Review-image OCR ground truth

Status: candidate manifests and local PII review bundle created, PII review pending.

1. Export review-image PII screening batches.
2. Reject rows with faces, personal info, order info, addresses, phone numbers, or
   unrelated photos.
3. Export OCR ground-truth template only for cleared rows.
4. Human-fill exact values for product name, ingredients, amounts, intake method,
   precautions, and optional functional claims.
5. Build benchmark fixture manifest.

Acceptance evidence:

- PII screening apply summary exists
- OCR ground-truth rows are human-reviewed
- benchmark manifest includes only PII-cleared and human-reviewed rows

Current implementation state:

- `review-pii-screening-bundle/README.md` and
  `review-pii-screening-bundle/review-index.html` now include the operator decision
  guide, reason-code guide, and cleared-row attestation requirements.
- `review-pii-screening-bundle/decisions.todo.jsonl` includes editable PII decision
  stubs plus `decision_guide`, `reason_code_guide`, and
  `cleared_required_attestations`.
- `review-pii-screening-preflight.json` currently reports `215` candidate rows,
  `215` blank decisions, and `0` cleared rows.
- `ocr-benchmark-gate.json` remains `blocked_by_pii_screening`; teacher OCR,
  external OCR evaluation, and PaddleOCR training are not allowed.

### Phase C - OCR provider comparison

Status: blocked until Phase B.

1. Run CLOVA OCR and Google Vision only on cleared benchmark fixtures.
2. Run PaddleOCR on the same fixture set.
3. Store provider outputs in private generated artifacts, not DB.
4. Store redacted metrics and failure summaries.
5. Gate PaddleOCR improvement candidates from confirmed misses only.

Acceptance evidence:

- comparison artifact exists
- provider calls are opt-in and recorded
- raw provider payload is not exposed in operator reports or API responses

### Phase D - Detail-page YOLO section annotation

Status: candidate manifests and local annotation bundle created, bbox review pending.

1. Export local annotation bundle from detail-page candidates.
2. Label section bboxes using the class list above.
3. Validate each bbox is normalized, clamped, and class-whitelisted.
4. Promote approved annotations.
5. Materialize the YOLO dataset in Ultralytics detect format.

Current implementation state:

- `yolo-section-annotation-bundle/annotation-index.html` displays the materialized
  detail-page images for local review.
- `yolo-section-annotation-bundle/annotation.todo.jsonl` includes the editable
  `label_snapshot.boxes` stubs plus a normalized `xywh` example and section
  class guide.
- `yolo-section-annotation-preflight.json` currently reports all rows as pending
  human bbox review, with no invalid rows.
- `yolo-section-dataset-gate.json` remains blocked by annotation review and does
  not allow training.

Acceptance evidence:

- approved bbox decisions exist
- YOLO dataset summary exists
- label rows follow official detect format
- low-confidence or overlapping boxes are flagged for review

### Phase E - PaddleOCR dataset and training gate

Status: blocked until Phases B and C.

1. Build PaddleOCR improvement candidates from benchmark misses.
2. Create OCR annotation tasks.
3. Materialize PaddleOCR train/val datasets from approved tasks.
4. Build a fine-tune run plan.
5. Evaluate baseline and candidate model.
6. Promote only if the metric gate passes.

Acceptance evidence:

- baseline eval artifact exists
- fine-tune eval artifact exists
- comparison gate artifact exists
- promotion runbook exists

## Security and Privacy Review

Controls to preserve:

- Do not store local absolute paths in DB, API responses, or public reports.
- Do not store raw OCR text, provider payloads, image bytes, request headers, or secrets.
- Do not send review images to CLOVA or Google Vision until PII screening is approved.
- Do not use teacher OCR as ground truth without human review.
- Do not commit source image datasets or materialized private image fixtures.
- Enforce the image-commit rule with
  `backend/scripts/check_private_image_artifacts_not_tracked.py`; the current
  report checks `crawling-image` and local operator-review artifacts and reports
  `tracked_private_image_count=0`.
- Keep DB writes separate from read-only audits and dry runs.
- Keep user/profile data out of training manifests unless an explicit learning policy
  and owner-level consent path exists.

Main gaps after this review:

- Brand/product import is still pending operator review.
- Manual OCR ground truth does not yet exist.
- CLOVA/Google/PaddleOCR comparison has not run.
- YOLO bbox review has not been completed.
- YOLO dataset materialization has not happened.
- PaddleOCR fine-tune/eval/promotion gates are missing.

## Immediate Next Implementation Steps

1. Use `brand_product_review-001.triage.md` with the contact sheet to review the
   first brand/product batch in this order: low-evidence rows first, duplicate
   candidates together, then standard blank rows.
2. Fill `brand_product_review-001.review.csv`; never copy OCR raw text, provider
   payloads, image paths, or product folder literals into reviewed fields.
3. Run `build_supplement_brand_review_batch_triage.py` again after edits to catch
   partial rows before applying CSV decisions.
4. After operator decisions are filled, reconcile and apply only approved rows.
5. Continue PII screening and YOLO annotation batches in parallel.
6. Do not run external OCR or PaddleOCR training until the review gates above pass.
7. Use `operator-unblock-runbook.md` as the single redacted queue/gate status
   handoff for the next operator session.

## Official References

- Ultralytics detection dataset format: https://docs.ultralytics.com/datasets/detect/
- Ultralytics detect task: https://docs.ultralytics.com/tasks/detect/
- PaddleOCR OCR pipeline usage: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- Google Cloud Vision OCR: https://cloud.google.com/vision/docs/ocr
- NAVER Cloud CLOVA OCR API: https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
- PostgreSQL constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security

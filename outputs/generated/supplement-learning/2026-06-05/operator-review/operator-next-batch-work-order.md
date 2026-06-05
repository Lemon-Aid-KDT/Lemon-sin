# Supplement Operator Review Next Batch Work Order

Schema: `supplement-operator-review-next-work-order-v1`

이 문서는 다음 수동 검수 batch의 redacted 작업 지시서입니다. row id, 제품명, OCR 원문, provider payload, 이미지 경로, source ref, 로컬 경로를 포함하지 않습니다.

## Next Batch

- Batch: `brand_product_review:001`
- Queue: `brand_product_review`
- Stage: `brand_product_review`
- Stage status: `pending_operator_review`
- Batch status: `pending`
- Workpack guide: `brand_product_review-001.md`
- Batch JSONL: `brand_product_review-001.jsonl`
- Batch review CSV: `brand_product_review-001.review.csv`
- Source editable file: `decisions.todo.jsonl`
- Row range: `1-50`

## Progress

- Expected rows: `50`
- Valid rows: `0`
- Blank rows: `50`
- Pending rows: `0`
- Invalid rows: `0`
- Missing rows: `0`
- Total blank rows across queues: `808`

## Reason Counts

- `blank_decision`: `50`

## Batch Triage

- Triage file: `brand_product_review-001.triage.json`
- Rows: `50`
- Blank rows: `50`
- Reviewed/valid rows: `0`
- Priorities:
- `p1_evidence_check`: `3`
- `p2_duplicate_candidate_review`: `37`
- `p3_standard_review`: `10`
- Reasons:
- `blank_decision`: `50`
- `duplicate_candidate_in_batch`: `38`
- `no_review_images`: `3`
- Row hints:
- row `21`: `p1_evidence_check`
- row `26`: `p1_evidence_check`
- row `32`: `p1_evidence_check`
- row `4`: `p2_duplicate_candidate_review`
- row `5`: `p2_duplicate_candidate_review`
- Operator next steps:
- `verify_low_evidence_rows_in_contact_sheet`
- `review_duplicate_candidate_rows_together`
- `complete_blank_decisions_in_review_csv`
- `run_apply_brand_batch_review_csv_decisions`
- `run_batch_file_preflight_before_reconcile`

## Source Bundle Files

- `decisions.todo.jsonl`
- `review-index.html`
- `README.md`
- `review.csv`

## Visual Review Contact Sheet

- Directory: `brand-detail-contact-sheet-001`
- Files:
- `brand-detail-contact-sheet.html`
- `README.md`
- `brand-detail-contact-sheet.summary.json`
- Reviewable rows: `50`
- Rows with thumbnails: `50`
- Rows without thumbnails: `0`
- Thumbnail count: `127`
- Contact sheet는 브랜드/제품명 검수용 시각 근거입니다. 보이는 텍스트를 notes에 복사하지 않습니다.

## Checklist

- `fill_reviewed_manufacturer`
- `fill_reviewed_product_name`
- `set_approve_or_reject_decision`
- `keep_db_import_attestation_explicit`

## Post Completion Gates

- `reconcile_operator_batch_files`
- `rerun_operator_batch_progress_preflight`
- `extract_reviewed_brand_decisions_for_partial_manifest_preview`
- `rerun_brand_decision_preflight`
- `create_approved_product_import_only_after_blank_invalid_counts_are_zero`

## Rule

preflight 통과 전에는 DB apply, teacher OCR transfer, YOLO dataset promotion, PaddleOCR 학습을 진행하지 않습니다.

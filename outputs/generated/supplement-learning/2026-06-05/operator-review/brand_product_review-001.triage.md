# Supplement Brand Review Batch Triage

Schema: `supplement-brand-review-batch-triage-markdown-v1`

이 문서는 brand/product review CSV의 검토 우선순위만 표시합니다.
제품명, 브랜드명, OCR 원문, provider payload, 이미지 경로, source ref, 로컬 경로는 포함하지 않습니다.

## Batch

- CSV: `brand_product_review-001.review.csv`
- Rows: `50`
- Blank decision rows: `50`
- Partial review rows without decision: `0`
- Reviewed rows: `0`

## Priority Counts

- `p1_evidence_check`: `3`
- `p2_duplicate_candidate_review`: `37`
- `p3_standard_review`: `10`

## Reason Counts

- `blank_decision`: `50`
- `duplicate_candidate_in_batch`: `38`
- `no_review_images`: `3`

## Row Hints

- row `21`: `p1_evidence_check` (blank_decision, no_review_images)
- row `26`: `p1_evidence_check` (blank_decision, duplicate_candidate_in_batch, no_review_images)
- row `32`: `p1_evidence_check` (blank_decision, no_review_images)
- row `4`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `5`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `6`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `7`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `8`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `9`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `10`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `11`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `12`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `13`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `14`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `15`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `16`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `17`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `18`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `20`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `22`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `27`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `28`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `30`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `31`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)
- row `33`: `p2_duplicate_candidate_review` (blank_decision, duplicate_candidate_in_batch)

## Next Steps

- `verify_low_evidence_rows_in_contact_sheet`
- `review_duplicate_candidate_rows_together`
- `complete_blank_decisions_in_review_csv`
- `run_apply_brand_batch_review_csv_decisions`
- `run_batch_file_preflight_before_reconcile`

## Rule

이 triage는 수동 검토 순서만 제안합니다. approve/reject 결정, DB import, OCR ground-truth 전환은 별도 gate를 통과해야 합니다.

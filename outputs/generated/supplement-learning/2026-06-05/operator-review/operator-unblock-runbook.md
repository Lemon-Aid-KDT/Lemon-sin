# Supplement Operator Unblock Runbook

- Schema: `supplement-operator-unblock-runbook-v1`
- Status: `blocked_by_operator_review`
- Completion allowed: `false`
- Next batch: `brand_product_review:001`
- Next batch file: `brand_product_review-001.jsonl`
- Source editable file: `decisions.todo.jsonl`
- Total blank rows: `808`
- Requirements: `6` verified / `3` pending / `5` blocked

## Queue Summary

| Queue | Status | Batches | Blank | Valid | Next batch | Reason counts |
| --- | --- | ---: | ---: | ---: | --- | --- |
| brand_product_review | `pending_operator_review` | 8 | 388 | 0 | brand_product_review:001 | blank_decision=388 |
| review_pii_screening | `pending_operator_review` | 5 | 215 | 0 | review_pii_screening:001 | blank_decision=215 |
| yolo_section_annotation | `pending_operator_review` | 5 | 205 | 0 | yolo_section_annotation:001 | blank_boxes=205 |

## Gate Summary

| Gate | Status | Key counts | Allowed flags | Next steps |
| --- | --- | --- | --- | --- |
| brand_db_import_gate | `blocked_by_operator_review` | approved_decision_count=0, blank_decision_count=388, pending_operator_action_count=388 | db_import_apply_allowed_now=false, product_import_manifest_allowed=false | complete_operator_brand_review, rerun_brand_decision_preflight_require_all_reviewed, rerun_brand_db_import_gate |
| ocr_benchmark_gate | `blocked_by_pii_screening` | benchmark_fixture_count=0, cleared_no_personal_data_count=0, pii_blank_decision_count=215, pii_pending_operator_action_count=215 | external_teacher_ocr_eval_allowed=false, paddleocr_training_allowed_now=false, teacher_ocr_benchmark_allowed=false | complete_review_image_pii_screening, rerun_pii_screening_decision_preflight_require_all_reviewed, rerun_ocr_benchmark_gate |
| yolo_section_dataset_gate | `blocked_by_annotation_review` | blank_box_row_count=205, pending_operator_action_count=205, promoted_item_count=0 | dataset_materialization_ready=false, model_promotion_allowed_now=false, section_yolo_training_allowed_now=false | complete_supplement_section_bbox_review, rerun_yolo_annotation_preflight_require_all_reviewed, rerun_yolo_section_dataset_gate |

## Batch Triage Summary

| Queue | File | Rows | Blank | Reviewed/Valid | Priorities | Reasons | Hints |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| brand_product_review | brand_product_review-001.triage.json | 50 | 50 | 0 | p1_evidence_check=3, p2_duplicate_candidate_review=37, p3_standard_review=10 | blank_decision=50, duplicate_candidate_in_batch=38, no_review_images=3 | row 21:p1_evidence_check, row 26:p1_evidence_check, row 32:p1_evidence_check, row 4:p2_duplicate_candidate_review, row 5:p2_duplicate_candidate_review |
| review_pii_screening | review_pii_screening-001.triage.json | 50 | 50 | 0 | p2_privacy_screening_required=50 | blank_decision=50 | row 1:p2_privacy_screening_required, row 2:p2_privacy_screening_required, row 3:p2_privacy_screening_required, row 4:p2_privacy_screening_required, row 5:p2_privacy_screening_required |
| yolo_section_annotation | yolo_section_annotation-001.triage.json | 50 | 50 | 0 | p2_bbox_annotation_required=50 | blank_boxes=50 | row 1:p2_bbox_annotation_required, row 2:p2_bbox_annotation_required, row 3:p2_bbox_annotation_required, row 4:p2_bbox_annotation_required, row 5:p2_bbox_annotation_required |

## Unblock Sequence

| Order | Queue | Action | Unblocks |
| ---: | --- | --- | --- |
| 1 | brand_product_review | complete_brand_product_human_review | taxonomy product/category DB import |
| 2 | review_pii_screening | complete_review_image_pii_screening | manual OCR ground truth and teacher OCR comparison |
| 3 | yolo_section_annotation | complete_supplement_section_bbox_review | YOLO section dataset and PaddleOCR improvement loop |
| 4 | post_operator_gates | run_post_completion_gates_in_order | remaining requirement gates: brand_product_db_import, taxonomy_db_import_verified, review_image_ground_truth_privacy_gate, manual_ocr_ground_truth, teacher_ocr_paddleocr_comparison, detail_page_yolo_bbox_annotation, section_yolo_dataset_ready, paddleocr_training_loop_ready |

## Current Post-Completion Gates

- `1` `preflight_supplement_brand_review_contact_sheet` (`must_pass_before_csv_apply`): confirm csv and contact sheet row alignment
- `2` `build_supplement_brand_review_batch_triage` (`operator_review_helper_no_decision`): summarize csv review priority without decisions
- `3` `apply_supplement_brand_batch_review_csv_decisions` (`require_all_reviewed_no_source_overwrite`): copy fully reviewed csv fields into a batch jsonl copy
- `4` `preflight_supplement_operator_review_batch_file` (`must_pass_before_reconcile`): confirm operator local batch is complete
- `5` `reconcile_supplement_operator_review_batch_files` (`no_source_overwrite`): merge completed batch into reconciled queue copies
- `6` `preflight_supplement_operator_review_batch_progress` (`must_pass_before_queue_preflight`): confirm queue level batch progress after reconcile
- `7` `extract_supplement_brand_reviewed_decisions` (`partial_preview_only`): separate reviewed brand decisions from blank queue stubs
- `8` `preflight_supplement_brand_review_decisions` (`strict_zero_blank_pending_invalid_required`): check strict brand decision readiness
- `9` `gate_supplement_brand_db_import` (`must_pass_before_product_manifest`): gate product import manifest preparation
- `10` `apply_supplement_brand_review_decisions` (`dry_run_or_manifest_only_before_db_gate`): create approved product import manifest
- `11` `import_supplement_taxonomy_approved_manifest` (`dry_run_before_product_db_apply`): dry run category product and mapping import
- `12` `gate_supplement_product_db_apply` (`must_pass_before_db_apply`): gate reviewed product db apply
- `13` `verify_supplement_taxonomy_db_import` (`read_only_after_apply`): verify imported categories products and mappings

## Safety

- Source images read: `false`
- DB write performed: `false`
- OCR provider call performed: `false`
- LLM call performed: `false`
- Training execution performed: `false`
- Raw OCR/provider payload stored: `false`

## Source Docs

- https://docs.python.org/3/library/csv.html
- https://docs.ultralytics.com/datasets/detect/
- https://docs.ultralytics.com/tasks/detect/
- https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- https://cloud.google.com/vision/docs/ocr
- https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
- https://docs.sqlalchemy.org/en/21/orm/queryguide/select.html
- https://www.postgresql.org/docs/current/ddl-constraints.html
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://docs.python.org/3/library/argparse.html
- https://docs.python.org/3/library/json.html

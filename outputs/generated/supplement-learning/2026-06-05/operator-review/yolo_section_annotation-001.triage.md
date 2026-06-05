# Supplement Operator Review Batch Triage

Schema: `supplement-operator-review-batch-triage-markdown-v1`

이 문서는 operator JSONL batch의 검토 우선순위만 표시합니다.
fixture id, 이미지 경로, source ref, bbox 좌표, OCR 원문, provider payload는 포함하지 않습니다.

## Batch

- Queue: `yolo_section_annotation`
- File: `yolo_section_annotation-001.jsonl`
- Rows: `50`
- Valid rows: `0`
- Blank rows: `50`
- Pending rows: `0`
- Invalid rows: `0`

## Priority Counts

- `p2_bbox_annotation_required`: `50`

## Reason Counts

- `blank_boxes`: `50`

## Row Hints

- row `1`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `2`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `3`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `4`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `5`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `6`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `7`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `8`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `9`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `10`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `11`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `12`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `13`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `14`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `15`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `16`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `17`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `18`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `19`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `20`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `21`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `22`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `23`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `24`: `p2_bbox_annotation_required` (`blank_boxes`)
- row `25`: `p2_bbox_annotation_required` (`blank_boxes`)

## Next Steps

- `draw_section_bboxes_or_mark_rejected`
- `run_batch_file_preflight_before_reconcile`
- `run_strict_yolo_preflight_before_dataset_materialization`

## Rule

이 triage는 수동 검토 순서만 제안합니다. PII clearance, teacher OCR, YOLO dataset promotion, training은 별도 gate를 통과해야 합니다.

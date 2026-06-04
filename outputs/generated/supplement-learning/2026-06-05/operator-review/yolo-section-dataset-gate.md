# Supplement YOLO Section Dataset Gate

Schema: `supplement-yolo-section-dataset-gate-v1`

이 문서는 supplement label bbox annotation이 YOLO26 학습 데이터셋으로 넘어갈 수 있는지 aggregate summary만으로 판단합니다. 이미지 경로, source ref, 라벨 row, OCR 원문은 포함하지 않습니다.

- Status: `blocked_by_annotation_review`
- Training allowed now: `false`
- Model promotion allowed now: `false`

## Counts

- Template rows: `205`
- Valid accepted rows: `0`
- Pending annotation actions: `205`
- Promoted items: `0`
- Materialized items: `0`
- Images: `0`
- Labels: `0`
- Train split: `0`
- Val split: `0`
- Test split: `0`

## Gate Checks

- Strict annotation ready: `false`
- Template promotion ready: `false`
- Dataset materialization ready: `false`
- Dataset validation ready: `true`

## Next Steps

- `complete_supplement_section_bbox_review`
- `rerun_yolo_annotation_preflight_require_all_reviewed`
- `rerun_yolo_section_dataset_gate`

## Rule

YOLO26 학습은 strict bbox review, reviewed template promotion, train/val이 모두 있는 materialized dataset, require-files validation이 통과한 뒤에만 허용합니다. 모델 promotion은 별도 metric gate 전까지 계속 차단합니다.

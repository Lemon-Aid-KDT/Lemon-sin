# Supplement Learning Dependency Audit

Schema: `supplement-learning-dependency-audit-v1`

이 문서는 목표별 blocker와 다음 operator batch를 aggregate 수준에서 연결합니다. row id, 제품명, OCR 원문, provider payload, 이미지 경로, 로컬 경로를 포함하지 않습니다.

- Status: `blocked_by_operator_review`
- Batch count: `18`
- Pending batch count: `18`
- Total blank rows: `808`

| Outcome | Gate status | Allowed now | Blocking queue | Next batch |
| --- | --- | --- | --- | --- |
| product_catalog_db_import | blocked_by_operator_review | false | brand_product_review | `brand_product_review:001` (brand_product_review-001.md) |
| ocr_teacher_benchmark | blocked_by_pii_screening | false | review_pii_screening | `review_pii_screening:001` (review_pii_screening-001.md) |
| yolo_section_dataset | blocked_by_annotation_review | false | yolo_section_annotation | `yolo_section_annotation:001` (yolo_section_annotation-001.md) |

## Recommended Operator Sequence

- `brand_product_review:001`
- `review_pii_screening:001`
- `yolo_section_annotation:001`

## Rule

1. 각 outcome의 다음 batch를 채운 뒤 reconcile과 queue-level preflight를 다시 실행합니다.
2. DB import, teacher OCR benchmark, YOLO promotion, PaddleOCR training은 해당 gate가 explicit allow를 반환하기 전까지 실행하지 않습니다.
